.PHONY: install fix check test build


install:
	uv tool install --reinstall .

fix:
	uv run black .
	uv run isort .

check:
	uv run black --check .
	uv run isort --check-only .

test:
	uv run python -m unittest discover -s tests -v

build:
	uv sync --group build
	uv run pyinstaller --onefile --name tomuroboxmidi main.py
