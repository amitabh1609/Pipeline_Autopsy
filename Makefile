PYTHON ?= python3

.PHONY: smoke test

smoke:
	LLM_MODE=mock $(PYTHON) -m pytest -q

test:
	$(PYTHON) -m pytest -q
