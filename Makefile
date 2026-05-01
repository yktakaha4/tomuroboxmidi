.PHONY: install fix check test build


install:
	uv sync --group dev
	uv tool install --reinstall .

fix:
	uv run --group dev black .
	uv run --group dev isort .

check:
	uv run --group dev black --check .
	uv run --group dev isort --check-only .

test:
	uv run python -m unittest discover -s tests -v

build:
	rm -rf build/ dist/ tomuroboxmidi.spec
	uv sync --group dev
	uv run pyinstaller --onefile --name tomuroboxmidi main.py
