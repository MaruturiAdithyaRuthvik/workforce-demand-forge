.PHONY: setup starter full validate test repro all clean

setup:
	python -m pip install -e ".[dev]"

starter:
	wdf generate --scale starter --seed 20261022 --out output/starter

full:
	wdf generate --scale full --seed 20261022 --out output/full

validate:
	wdf validate --input output/starter

test:
	pytest

repro:
	wdf repro --scale starter --seed 20261022 --out output

all: test starter validate forecast detect evaluate

forecast:
	wdf forecast --input output/starter

detect:
	wdf detect --input output/starter

evaluate:
	wdf evaluate --input output/starter

clean:
	python -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['output/starter', 'output/full', 'output/repro-a', 'output/repro-b']]"
