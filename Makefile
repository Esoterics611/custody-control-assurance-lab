.PHONY: install test lint assure serve e2e clean

install:
	uv sync
	npx --prefix tests/e2e playwright install chromium || npx playwright install chromium

test:
	uv run pytest -n auto

lint:
	uv run ruff check src tests scripts
	uv run black --check src tests scripts

assure:
	uv run python scripts/run_assurance.py

serve:
	uv run python -m cal.api.serve

e2e:
	cd tests/e2e && npx playwright test

clean:
	rm -rf reports/*.json reports/*.html allure-results .pytest_cache
