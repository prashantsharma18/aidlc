PY ?= python3
export PYTHONPATH := $(CURDIR)/cli

.PHONY: test
test:
	$(PY) -m unittest discover -s tests -t .

.PHONY: harness-live
harness-live:
	$(PY) tests/harness_live/run_attacks.py --out docs/verification/$$(date +%F)-harness-attacks.md
