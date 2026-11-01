.PHONY: setup starter full validate test repro independent-check docs-check all clean

setup:
	uv sync --locked

starter:
	uv run wdf generate --scale starter --seed 20261022 --out output/starter

full:
	uv run wdf generate --scale full --seed 20261022 --out output/full

validate:
	uv run wdf validate --input output/starter

test:
	uv run pytest --cov=wdf --cov-report=term-missing

repro:
	uv run wdf repro --scale starter --seed 20261022 --out output

independent-check: full
	uv run python tools/independent_check.py output/full

docs-check:
	uv run python tools/check_docs.py output/full

all: test starter validate forecast detect evaluate

forecast:
	uv run wdf forecast --input output/starter

detect:
	uv run wdf detect --input output/starter

evaluate:
	uv run wdf evaluate --input output/starter

clean:
	python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['output/starter', 'output/full', 'output/repro-a', 'output/repro-b']]"
