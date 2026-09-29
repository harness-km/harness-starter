# Agent Harness Engineering — starter repository
# Run `make help` to see the commands.

PY ?= python
WEEK ?=

.PHONY: help setup test data catch-up logs audit replay

help:
	@echo "make setup            install the course libraries (Codespaces does this for you)"
	@echo "make test             run the tests"
	@echo "make data             (re)generate the course dataset in ./data"
	@echo "make catch-up WEEK=07 save your work to a backup branch, then copy in that week's checkpoint"
	@echo "make logs RUN=<id>    (from Week 8) log lines for one run"
	@echo "make audit RUN=<id>   (from Week 8) audit chain for one run, verified"
	@echo "make replay RUN=<id>  (from Week 9) replay a checkpointed run"

setup:
	$(PY) -m pip install -q -r requirements.lock
	$(PY) -m pip install -q -e course-tools

test:
	$(PY) -m pytest -q

data:
	$(PY) -m course_tools.data.generate data

catch-up:
	@test -n "$(WEEK)" || (echo "Usage: make catch-up WEEK=07" && exit 1)
	$(PY) scripts/catch_up.py $(WEEK)

logs audit replay:
	@echo "'make $@' arrives with the kernel in Weeks 8 and 9."
