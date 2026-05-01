.PHONY: fix test build install

fix:
	uv run black .
	uv run isort .

test:
	uv run python -m unittest discover -s tests -v

build:
	uv sync --group build
	uv run pyinstaller --onefile --name tomuroboxmidi main.py

install:
	uv tool install --reinstall .
