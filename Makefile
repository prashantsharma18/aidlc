PY ?= python3
export PYTHONPATH := $(CURDIR)/cli

.PHONY: test
test:
	$(PY) -m unittest discover -s tests -t .
