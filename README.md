# tomuroboxmidi

A CLI tool that converts MIDI files into a format compatible with [Muro Box](https://murobox.com/) music boxes.

## What it does

- Merges all tracks into a single track (Muro Box only accepts Type 0 MIDI files)
- Removes notes outside the playable range of the target model
- Removes duplicate notes that occur at the exact same tick position

## Installation

### Using uv tool (recommended)

```sh
uv tool install git+https://github.com/yktakaha4/tomuroboxmidi
```

### Using pipx

```sh
pipx install git+https://github.com/yktakaha4/tomuroboxmidi
```

### Standalone binary

Download the pre-built binary for your platform from the [Releases](https://github.com/yktakaha4/tomuroboxmidi/releases) page. No Python installation required.

## Usage

```
tomuroboxmidi [OPTIONS] <input_file> [<input_file> ...]
```

Converted files are written to `./muroboxmidi/` by default, preserving the original filenames.
A directory can also be passed as input — all `.mid` and `.midi` files directly inside it will be processed.

### Options

| Option | Description |
|---|---|
| `-m, --model {n20,n40}` | Target Muro Box model. Default: `n40` |
| `-o, --output <dir>` | Output directory (absolute or relative path). Default: `./muroboxmidi/` |
| `-f, --force` | Overwrite existing output files without confirmation |
| `-v, --verbose` | Print details of each removed note |

### Examples

```sh
# Convert a single file (n40 model, output to ./muroboxmidi/)
tomuroboxmidi song.mid

# Convert all MIDI files in a directory
tomuroboxmidi ./my_songs/

# Convert for the n20 model
tomuroboxmidi -m n20 song.mid

# Specify output directory and force overwrite
tomuroboxmidi -f -o ./out song.mid

# Show details of removed notes
tomuroboxmidi -v song.mid
```

## Muro Box note range

Notes outside the valid range are removed rather than silently transposed.

### N40 (default)

Range: F2 – A6 (chromatic, with four exceptions)

Excluded notes: F#2, G#2, A#2, C#3

### N20

Range: C3 – A5 (white keys only, 20 notes)

> **Note:** C3 = Middle C = MIDI note 60 (261.6 Hz)

---

## Development

### Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

### Setup

```sh
git clone https://github.com/yktakaha4/tomuroboxmidi
cd tomuroboxmidi
uv sync
```

### Running the tool locally

```sh
uv run tomuroboxmidi --help
```

### Code style

This project uses [black](https://github.com/psf/black) for formatting and [isort](https://pycf.github.io/isort/) for import sorting.

```sh
uv run black .
uv run isort .
```

### Running tests

Snapshot tests using `unittest`:

```sh
uv run python -m unittest discover -s tests -v
```

To regenerate snapshots after intentional behavior changes:

```sh
UPDATE_SNAPSHOTS=1 uv run python -m unittest tests/test_converter.py
```

### CI

GitHub Actions runs black, isort, and unittest on every push and pull request to `main`.

---

## Building a standalone binary

Produces a single self-contained executable via [PyInstaller](https://pyinstaller.org/).

```sh
uv sync --group build
uv run pyinstaller --onefile --name tomuroboxmidi main.py
# Output: dist/tomuroboxmidi
```

---

## Project structure

```
tomuroboxmidi/
├── tomuroboxmidi/
│   ├── main.py        # CLI entry point (argparse, I/O flow)
│   ├── converter.py   # MIDI conversion logic
│   └── models.py      # Valid note sets per model
├── tests/
│   ├── test_converter.py
│   ├── snapshots/
│   ├── daisy_bell.mid
│   └── annie_laurie.mid
├── main.py            # Shim for `python main.py`
└── pyproject.toml
```
