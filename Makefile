.PHONY: build bump-major bump-minor bump-patch clean coverage format install install-pipx lint release-check test

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
VERSION := $(shell sed -nE 's/^VERSION = "([0-9]+\.[0-9]+\.[0-9]+)"$$/\1/p' euercli/__init__.py)

# Install globally via pipx (recommended for end users)
install-pipx:
	pipx install .
	@echo ""
	@echo "✓ euer ist jetzt global verfügbar."

# Create venv and install in editable mode (for development)
install:
	python3 -m venv $(VENV)
	$(PIP) install -e ".[dev,xlsx]"
	@echo ""
	@echo "✓ Dev-Installation abgeschlossen."
	@echo "  Aktiviere die Umgebung mit: source $(VENV)/bin/activate"

# Run tests
test:
	$(PYTHON) -m unittest discover -s tests

# Check linting and formatting without changing files
lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

# Format Python files
format:
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

# Run tests and report coverage
coverage:
	$(VENV)/bin/coverage run -m unittest discover -s tests
	$(VENV)/bin/coverage combine
	$(VENV)/bin/coverage report

# Build wheel and source distribution
build:
	rm -rf dist
	$(PYTHON) -m build

# Validate the tag, canonical version, main ancestry and release notes.
release-check:
	$(PYTHON) -m scripts.release_check --tag v$(VERSION) --main-ref main

# Versioning
bump-patch:
	./scripts/bump-version.sh patch

bump-minor:
	./scripts/bump-version.sh minor

bump-major:
	./scripts/bump-version.sh major

# Remove venv and build artifacts
clean:
	rm -rf $(VENV) build dist *.egg-info euercli.egg-info .coverage* .ruff_cache
	rm -rf __pycache__ euercli/__pycache__ euercli/commands/__pycache__
	rm -rf euercli/services/__pycache__ tests/__pycache__
