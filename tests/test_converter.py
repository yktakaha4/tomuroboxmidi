"""converter のスナップショットテスト。

スナップショットの初回生成・更新:
    UPDATE_SNAPSHOTS=1 python -m unittest tests/test_converter.py

通常のテスト実行:
    python -m unittest discover -s tests
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

import mido

from tomuroboxmidi.converter import ConvertResult, convert, note_name
from tomuroboxmidi.models import MODEL_MAP

TESTS_DIR = Path(__file__).parent
SNAPSHOTS_DIR = TESTS_DIR / "snapshots"
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS") == "1"


def _format_msg(msg) -> str:
    """mido メッセージを tick なしのテキストに変換する。"""
    s = str(msg)
    if s.startswith("MetaMessage("):
        s = re.sub(r", time=\d+\)$", ")", s)
    else:
        s = re.sub(r" time=\d+$", "", s)
    if hasattr(msg, "note") and not isinstance(msg, mido.MetaMessage):
        s += f"  # {note_name(msg.note)}"
    return s


def midi_to_snapshot_text(result: ConvertResult, output_path: Path) -> str:
    """変換結果と出力MIDIファイルをスナップショット用テキストに変換する。"""
    mid = mido.MidiFile(str(output_path))

    lines = [
        "## result",
        f"removed_out_of_range={result.removed_out_of_range}",
        f"removed_duplicates={result.removed_duplicates}",
        f"remaining_notes={result.remaining_notes}",
        "## midi",
        f"ticks_per_beat={mid.ticks_per_beat}",
        f"type={mid.type}",
        "---",
    ]

    current_tick = 0
    for msg in mid.tracks[0]:
        current_tick += msg.time
        lines.append(f"tick={current_tick:8d}  {_format_msg(msg)}")

    return "\n".join(lines) + "\n"


class TestConverterSnapshot(unittest.TestCase):

    def _run(self, midi_filename: str, model: str) -> None:
        input_path = TESTS_DIR / midi_filename
        stem = Path(midi_filename).stem
        snapshot_path = SNAPSHOTS_DIR / f"{stem}_{model}.txt"

        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = convert(input_path, output_path, MODEL_MAP[model])
            actual = midi_to_snapshot_text(result, output_path)
        finally:
            output_path.unlink(missing_ok=True)

        if UPDATE_SNAPSHOTS:
            SNAPSHOTS_DIR.mkdir(exist_ok=True)
            snapshot_path.write_text(actual, encoding="utf-8")
            return

        if not snapshot_path.exists():
            self.fail(
                f"スナップショットが存在しません: {snapshot_path}\n"
                "UPDATE_SNAPSHOTS=1 python -m unittest tests/test_converter.py で生成してください。"
            )

        expected = snapshot_path.read_text(encoding="utf-8")
        self.assertEqual(actual, expected, f"スナップショットと一致しません: {snapshot_path}")

    def test_daisy_bell_n20(self):
        self._run("daisy_bell.mid", "n20")

    def test_daisy_bell_n40(self):
        self._run("daisy_bell.mid", "n40")

    def test_annie_laurie_n20(self):
        self._run("annie_laurie.mid", "n20")

    def test_annie_laurie_n40(self):
        self._run("annie_laurie.mid", "n40")


if __name__ == "__main__":
    unittest.main()
