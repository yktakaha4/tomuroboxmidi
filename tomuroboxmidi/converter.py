from dataclasses import dataclass, field
from pathlib import Path

import mido

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(note: int) -> str:
    """MIDIノート番号をノート名に変換する（C3=60 基準）。"""
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

    filtered, range_details = _remove_out_of_range(merged, valid_notes)
    deduped, dup_details = _remove_duplicates(filtered)

    remaining = sum(1 for m in deduped if m.type == "note_on" and m.velocity > 0)

    out_mid = mido.MidiFile(type=0, ticks_per_beat=mid.ticks_per_beat)
    out_track = mido.MidiTrack()
    out_mid.tracks.append(out_track)
    out_track.extend(deduped)
    out_mid.save(str(output_path))

    return ConvertResult(
        removed_out_of_range=len(range_details),
        removed_duplicates=len(dup_details),
        remaining_notes=remaining,
        removed_note_details=range_details + dup_details,
    )


def _remove_out_of_range(
    messages: list,
    valid_notes: frozenset[int],
) -> tuple[list, list[RemovedNote]]:
    """音域外のノートを削除する。

    note_on を削除した場合は対応する note_off も削除し、
    削除したメッセージの time を次のメッセージに加算してタイミングを保持する。
    """
    result = []
    # pitch -> 削除済み note_on のうちまだ閉じていない数
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
                    # 対応する note_on がない孤立 note_off はそのまま通す
                    result.append(msg.copy(time=msg.time + pending_time))
                    pending_time = 0
        else:
            result.append(msg.copy(time=msg.time + pending_time))
            pending_time = 0

    return result, removed_details


def _remove_duplicates(messages: list) -> tuple[list, list[RemovedNote]]:
    """絶対 tick と pitch が完全一致する重複 note_on を削除する。

    重複した note_on に対応する note_off も削除し、
    先に出力した note_on が正しく閉じられるよう kept_active で追跡する。
    """
    # デルタ時間 -> 絶対 tick に変換
    abs_messages: list[tuple[int, object]] = []
    current_tick = 0
    for msg in messages:
        current_tick += msg.time
        abs_messages.append((current_tick, msg))

    # (abs_tick, pitch) の組み合わせで重複を検出
    seen_note_ons: set[tuple[int, int]] = set()
    # pitch -> 出力済みで未閉の note_on 数
    kept_active: dict[int, int] = {}
    # pitch -> スキップ済みで未閉の note_on 数
    skipped_active: dict[int, int] = {}

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
                # スキップした note_on に対応する note_off なので削除
            else:
                # 孤立 note_off はそのまま通す
                result.append((abs_tick, msg))
        else:
            result.append((abs_tick, msg))

    # 絶対 tick -> デルタ時間に戻す
    delta_messages = []
    prev_tick = 0
    for abs_tick, msg in result:
        delta_messages.append(msg.copy(time=abs_tick - prev_tick))
        prev_tick = abs_tick

    return delta_messages, removed_details
