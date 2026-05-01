.PHONY: fix test build

fix:
	uv run black .
	uv run isort .

test:
	uv run python -m unittest discover -s tests -v

build:
	uv sync --group build
	uv run pyinstaller --onefile --name tomuroboxmidi main.py
