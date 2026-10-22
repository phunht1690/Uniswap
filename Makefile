PYTHON ?= python

.PHONY: data run test research
data:
	$(PYTHON) -m src.data.ingest
run:
	$(PYTHON) -m uvicorn api.main:app --host 127.0.0.1 --port 8000
test:
	$(PYTHON) -m pytest
research:
	$(PYTHON) -m src.evaluation.research
