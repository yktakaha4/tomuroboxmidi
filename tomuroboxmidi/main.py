import argparse
import sys
from pathlib import Path

from tomuroboxmidi.converter import convert, note_name
from tomuroboxmidi.models import MODEL_MAP

_MIDI_SUFFIXES = {".mid", ".midi"}


def _collect_input_files(input_args: list[str]) -> list[Path]:
    """Resolve input arguments, expanding directories to their MIDI files."""
    result: list[Path] = []
    for arg in input_args:
        path = Path(arg)
        if path.is_dir():
            found = sorted(
                p
                for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in _MIDI_SUFFIXES
            )
            if not found:
                print(f"[skip] No MIDI files found in: {path}")
            result.extend(found)
        else:
            result.append(path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tomuroboxmidi",
        description="Convert MIDI files to Muro Box compatible format",
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        metavar="input_file",
        help="MIDI file(s) or directory to convert",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="overwrite existing output files without confirmation",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="dir",
        default=None,
        help="output directory (default: ./muroboxmidi/)",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=list(MODEL_MAP.keys()),
        default="n40",
        help="target Muro Box model (default: n40)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print details of each removed note",
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
            f"Error: could not create output directory: {output_dir}: {e}",
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
            print(f"[skip] File not found: {input_path}")
            skipped += 1
            continue

        output_path = output_dir / input_path.name

        if output_path.exists() and not args.force:
            try:
                answer = input(
                    f"Output file already exists: {output_path}\nOverwrite? [y/N]: "
                )
            except EOFError:
                answer = ""
            if answer.strip().lower() != "y":
                print(f"[skip] {input_path.name}")
                skipped += 1
                continue

        try:
            result = convert(input_path, output_path, valid_notes)
        except Exception as e:
            print(f"[error] {input_path}: {e}")
            skipped += 1
            continue

        print(f"[done] {input_path} -> {output_path}")
        print(f"  - out of range: {result.removed_out_of_range} note(s)")
        if args.verbose:
            for n in result.removed_note_details:
                if n.reason == "out_of_range":
                    print(f"      tick={n.abs_tick}  {note_name(n.note)} ({n.note})")
        print(f"  - duplicates:   {result.removed_duplicates} note(s)")
        if args.verbose:
            for n in result.removed_note_details:
                if n.reason == "duplicate":
                    print(f"      tick={n.abs_tick}  {note_name(n.note)} ({n.note})")
        print(f"  - remaining:    {result.remaining_notes} note(s)")

        if result.remaining_notes == 0:
            print("  [warning] No notes remaining after conversion")

        converted += 1

    print(f"\nDone: {converted}/{total} file(s) converted (skipped: {skipped})")


if __name__ == "__main__":
    main()
