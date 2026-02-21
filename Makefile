.PHONY: install install-pipx test lint clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Install globally via pipx (recommended for end users)
install-pipx:
	pipx install .
	@echo ""
	@echo "✓ euer ist jetzt global verfügbar."

# Create venv and install in editable mode (for development)
install:
	python3 -m venv $(VENV)
	$(PIP) install -e .
	@echo ""
	@echo "✓ Dev-Installation abgeschlossen."
	@echo "  Aktiviere die Umgebung mit: source $(VENV)/bin/activate"

# Run tests
test:
	$(PYTHON) -m unittest discover -s tests

# Run linter (requires ruff)
lint:
	$(VENV)/bin/ruff check euercli
	$(VENV)/bin/ruff format euercli

# Versioning
bump-patch:
	./scripts/bump-version.sh patch

bump-minor:
	./scripts/bump-version.sh minor

bump-major:
	./scripts/bump-version.sh major

# Remove venv and build artifacts
clean:
	rm -rf $(VENV) *.egg-info euercli.egg-info __pycache__ euercli/__pycache__
