.PHONY: install test lint demo bench ts-demo ts-check

install:
	pip install -r requirements.txt pytest

test:
	PYTHONPATH=. pytest tests/ -q

lint:
	python -m py_compile external_compute/*.py harness.py tools.py demo.py benchmark.py cli.py agent_loop.py platform_server.py

demo:
	python demo.py

bench:
	python benchmark.py --only orgo --runs 12 --json

ts-demo:
	cd typescript && npm install && npm run demo

ts-check:
	cd typescript && npm install && npm run typecheck
