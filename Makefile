PYTHON ?= python3

.PHONY: smoke test docker-build docker-up demo-docs

smoke:
	LLM_MODE=mock $(PYTHON) -m pytest -q

test:
	$(PYTHON) -m pytest -q

docker-build:
	docker compose build

docker-up:
	docker compose up

demo-docs:
	$(PYTHON) scripts/generate_demo_docs.py --count 50 --out documents/generated
