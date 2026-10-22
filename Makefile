.PHONY: help setup install lint test clean data notebooks app figures train

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

help:
	@echo "INSIGHT Kalimantan — common commands"
	@echo ""
	@echo "  make setup       Create venv and install dependencies"
	@echo "  make install     Install dependencies into existing venv"
	@echo "  make data        Download/prepare raw data for the demo bounding box"
	@echo "  make train       Train the Random Forest risk model from a FIRMS CSV"
	@echo "  make notebooks   Open the exploration notebooks (note: opens in browser)"
	@echo "  make app         Run the demo web app"
	@echo "  make figures     Regenerate demo figures if scripts exist"
	@echo "  make test        Run the test suite"
	@echo "  make lint        Run lightweight lint checks"
	@echo "  make clean       Remove venv and generated artifacts"

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

install:
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

requirements-dev.txt:
	@echo "Use 'make setup' or install extras manually:"
	@echo "  .venv/bin/pip install streamlit folium jupyter pytest flake8 ruff"

data:
	@echo "Downloading raw data for the configured bounding box..."
	$(PYTHON) -m src.fire_data download || true
	$(PYTHON) -m src.osm fetch || true

notebooks:
	@echo "Open Jupyter in the project root:"
	$(PYTHON) -m jupyter notebook notebooks/

app:
	$(PYTHON) -m app.main

train:
	$(PYTHON) -m src.train --firms data/raw/MODIS_C6_1_Global_7d.csv

figures:
	@echo "No figure generation scripts configured yet."

test:
	$(PYTHON) -m pytest tests/ -q

lint:
	flake8 src/ app/ tests/ || true
	ruff check src/ app/ tests/ || true

clean:
	rm -rf .venv
	rm -rf data/raw data/processed demos figures
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name '*.pyc' -delete || true
