PY ?= python3
export PYTHONPATH := $(CURDIR)/cli

.PHONY: test
test:
	$(PY) -m unittest discover -s tests -t .

.PHONY: harness-live
harness-live:
	$(PY) tests/harness_live/run_attacks.py --out docs/verification/$$(date +%F)-harness-attacks.md

# The live policy tests need the pinned conftest (aidlc tools install conftest). A skipped test
# here is a failure: this target is where the live tests must run.
AIDLC_TOOLS_DIR ?= $(HOME)/.aidlc/bin
export AIDLC_TOOLS_DIR

.PHONY: policy-test
policy-test:
	bin/aidlc policy rego-test
	@log=$$(mktemp); $(PY) -m unittest -v tests.unit.test_conftest_check tests.unit.test_ci_templates > $$log 2>&1; status=$$?; cat $$log; \
	skipped=$$(grep -cE "skipped=|\.\.\. skipped " $$log); rm -f $$log; \
	if [ $$status -ne 0 ]; then exit $$status; fi; \
	if [ $$skipped -ne 0 ]; then echo "policy-test: skipped test(s): install conftest (aidlc tools install conftest) or set AIDLC_TOOLS_DIR"; exit 1; fi
