from dataclasses import dataclass, field
from pathlib import Path

import mido

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(note: int) -> str:
    """Convert a MIDI note number to a note name (C3 = 60)."""
    return f"{_NOTE_NAMES[note % 12]}{(note // 12) - 2}"


@dataclass
class RemovedNote:
    note: int
    abs_tick: int
    reason: str  # "out_of_range" | "duplicate"


@dataclass
class ConvertResult:
    removed_out_of_range: int
    removed_duplicates: int
    remaining_notes: int
    removed_note_details: list[RemovedNote] = field(default_factory=list)


def convert(
    input_path: Path,
    output_path: Path,
    valid_notes: frozenset[int],
) -> ConvertResult:
    mid = mido.MidiFile(str(input_path))
    merged = list(mido.merge_tracks(mid.tracks))

    deduped_meta = _remove_duplicate_meta(merged)
    filtered, range_details = _remove_out_of_range(deduped_meta, valid_notes)
    deduped, dup_details = _remove_duplicates(filtered)
    with_eot = _set_end_of_track(deduped, mid.ticks_per_beat)

    remaining = sum(1 for m in deduped if m.type == "note_on" and m.velocity > 0)

    out_mid = mido.MidiFile(type=0, ticks_per_beat=mid.ticks_per_beat)
    out_track = mido.MidiTrack()
    out_mid.tracks.append(out_track)
    out_track.extend(with_eot)
    out_mid.save(str(output_path))

    return ConvertResult(
        removed_out_of_range=len(range_details),
        removed_duplicates=len(dup_details),
        remaining_notes=remaining,
        removed_note_details=range_details + dup_details,
    )


def _remove_duplicate_meta(messages: list) -> list:
    """Remove meta messages at non-zero ticks whose type already appeared at tick=0."""
    types_at_zero: set[str] = set()
    current_tick = 0
    for msg in messages:
        current_tick += msg.time
        if current_tick == 0 and isinstance(msg, mido.MetaMessage):
            types_at_zero.add(msg.type)

    result = []
    current_tick = 0
    pending_time = 0
    for msg in messages:
        current_tick += msg.time
        if (
            current_tick > 0
            and isinstance(msg, mido.MetaMessage)
            and msg.type not in ("end_of_track", "set_tempo", "key_signature")
            and msg.type in types_at_zero
        ):
            pending_time += msg.time
        else:
            result.append(msg.copy(time=msg.time + pending_time))
            pending_time = 0

    return result


def _remove_out_of_range(
    messages: list,
    valid_notes: frozenset[int],
) -> tuple[list, list[RemovedNote]]:
    """Remove notes outside the valid range.

    When a note_on is removed, its corresponding note_off is also removed.
    The delta time of removed messages is carried forward to the next message
    to preserve overall timing.
    """
    result = []
    # pitch -> number of filtered note_ons not yet closed
    filtered_active: dict[int, int] = {}
    removed_details: list[RemovedNote] = []
    pending_time = 0
    current_tick = 0

    for msg in messages:
        current_tick += msg.time

        if not hasattr(msg, "note"):
            result.append(msg.copy(time=msg.time + pending_time))
            pending_time = 0
            continue

        is_note_on = msg.type == "note_on" and msg.velocity > 0
        is_note_off = msg.type == "note_off" or (
            msg.type == "note_on" and msg.velocity == 0
        )

        if msg.note not in valid_notes:
            if is_note_on:
                filtered_active[msg.note] = filtered_active.get(msg.note, 0) + 1
                removed_details.append(
                    RemovedNote(msg.note, current_tick, "out_of_range")
                )
                pending_time += msg.time
            elif is_note_off:
                if filtered_active.get(msg.note, 0) > 0:
                    filtered_active[msg.note] -= 1
                    pending_time += msg.time
                else:
                    # Orphaned note_off with no matching note_on — pass through
                    result.append(msg.copy(time=msg.time + pending_time))
                    pending_time = 0
        else:
            result.append(msg.copy(time=msg.time + pending_time))
            pending_time = 0

    return result, removed_details


def _remove_duplicates(messages: list) -> tuple[list, list[RemovedNote]]:
    """Remove note_on messages that share the exact same absolute tick and pitch.

    When a duplicate note_on is removed, its corresponding note_off is also
    removed. kept_active tracks open note_ons that were kept, so their
    note_offs are correctly preserved.
    """
    # Convert delta times to absolute ticks
    abs_messages: list[tuple[int, object]] = []
    current_tick = 0
    for msg in messages:
        current_tick += msg.time
        abs_messages.append((current_tick, msg))

    seen_note_ons: set[tuple[int, int]] = set()  # (abs_tick, pitch)
    kept_active: dict[int, int] = {}  # pitch -> count of kept open note_ons
    skipped_active: dict[int, int] = {}  # pitch -> count of skipped open note_ons

    result: list[tuple[int, object]] = []
    removed_details: list[RemovedNote] = []

    for abs_tick, msg in abs_messages:
        if not hasattr(msg, "note"):
            result.append((abs_tick, msg))
            continue

        is_note_on = msg.type == "note_on" and msg.velocity > 0
        is_note_off = msg.type == "note_off" or (
            msg.type == "note_on" and msg.velocity == 0
        )

        if is_note_on:
            key = (abs_tick, msg.note)
            if key in seen_note_ons:
                removed_details.append(RemovedNote(msg.note, abs_tick, "duplicate"))
                skipped_active[msg.note] = skipped_active.get(msg.note, 0) + 1
            else:
                seen_note_ons.add(key)
                kept_active[msg.note] = kept_active.get(msg.note, 0) + 1
                result.append((abs_tick, msg))
        elif is_note_off:
            if kept_active.get(msg.note, 0) > 0:
                kept_active[msg.note] -= 1
                result.append((abs_tick, msg))
            elif skipped_active.get(msg.note, 0) > 0:
                skipped_active[msg.note] -= 1
                # note_off for a skipped note_on — discard
            else:
                # Orphaned note_off — pass through
                result.append((abs_tick, msg))
        else:
            result.append((abs_tick, msg))

    # Convert absolute ticks back to delta times
    delta_messages = []
    prev_tick = 0
    for abs_tick, msg in result:
        delta_messages.append(msg.copy(time=abs_tick - prev_tick))
        prev_tick = abs_tick

    return delta_messages, removed_details


def _set_end_of_track(messages: list, ticks_per_beat: int) -> list:
    """Remove existing end_of_track messages and append one 3 seconds after the last note event."""
    filtered = [m for m in messages if m.type != "end_of_track"]

    current_tick = 0
    last_note_tick = 0
    current_tempo = 500000  # default: 120 BPM
    last_note_tempo = 500000

    for msg in filtered:
        current_tick += msg.time
        if msg.type == "set_tempo":
            current_tempo = msg.tempo
        if hasattr(msg, "note"):
            last_note_tick = current_tick
            last_note_tempo = current_tempo

    three_sec_ticks = int(mido.second2tick(3.0, ticks_per_beat, last_note_tempo))
    eot_tick = last_note_tick + three_sec_ticks
    eot_delta = max(0, eot_tick - current_tick)

    filtered.append(mido.MetaMessage("end_of_track", time=eot_delta))
    return filtered
