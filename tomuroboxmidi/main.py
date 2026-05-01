import argparse
import sys
from pathlib import Path

from tomuroboxmidi.converter import convert, note_name
from tomuroboxmidi.models import MODEL_MAP


_MIDI_SUFFIXES = {".mid", ".midi"}


def _collect_input_files(input_args: list[str]) -> list[Path]:
    """引数リストを解析し、ディレクトリはその直下の MIDI ファイルに展開して返す。"""
    result: list[Path] = []
    for arg in input_args:
        path = Path(arg)
        if path.is_dir():
            found = sorted(
                p for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in _MIDI_SUFFIXES
            )
            if not found:
                print(f"[スキップ] MIDIファイルが見つかりません: {path}")
            result.extend(found)
        else:
            result.append(path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tomuroboxmidi",
        description="MIDIファイルをMuro Box向け形式に変換します",
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        metavar="input_file",
        help="変換対象のMIDIファイル",
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="出力先に同名ファイルが存在しても確認なしに上書きする",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="dir",
        default=None,
        help="出力先ディレクトリ（省略時: ./muroboxmidi/）",
    )
    parser.add_argument(
        "-m", "--model",
        choices=list(MODEL_MAP.keys()),
        default="n40",
        help="対象のMuro Boxモデル（省略時: n40）",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="削除されたノートの詳細を表示する",
    )

    args = parser.parse_args()

    if args.output is not None:
        output_dir = Path(args.output).resolve()
    else:
        output_dir = Path.cwd() / "muroboxmidi"

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(
            f"エラー: 出力ディレクトリを作成できませんでした: {output_dir}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    valid_notes = MODEL_MAP[args.model]

    input_paths = _collect_input_files(args.input_files)
    total = len(input_paths)
    converted = 0
    skipped = 0

    for input_path in input_paths:
        if not input_path.exists():
            print(f"[スキップ] ファイルが存在しません: {input_path}")
            skipped += 1
            continue

        output_path = output_dir / input_path.name

        if output_path.exists() and not args.force:
            try:
                answer = input(
                    f"出力先ファイルが既に存在します: {output_path}\n上書きしますか？ [y/N]: "
                )
            except EOFError:
                answer = ""
            if answer.strip().lower() != "y":
                print(f"[スキップ] {input_path.name}")
                skipped += 1
                continue

        try:
            result = convert(input_path, output_path, valid_notes)
        except Exception as e:
            print(f"[エラー] {input_path}: {e}")
            skipped += 1
            continue

        print(f"[変換完了] {input_path} -> {output_path}")
        print(f"  - 音域外削除: {result.removed_out_of_range} ノート")
        if args.verbose:
            for n in result.removed_note_details:
                if n.reason == "out_of_range":
                    print(f"      tick={n.abs_tick}  {note_name(n.note)} ({n.note})")
        print(f"  - 重複削除: {result.removed_duplicates} ノート")
        if args.verbose:
            for n in result.removed_note_details:
                if n.reason == "duplicate":
                    print(f"      tick={n.abs_tick}  {note_name(n.note)} ({n.note})")
        print(f"  - 残存ノート: {result.remaining_notes} ノート")

        if result.remaining_notes == 0:
            print("  [警告] 変換後のノートが0件です")

        converted += 1

    print(f"\n処理完了: {total} ファイル中 {converted} ファイル変換 (スキップ: {skipped})")


if __name__ == "__main__":
    main()
