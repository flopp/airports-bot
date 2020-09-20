.PHONY: setup
setup:
	python3 -m venv .env
	.env/bin/pip install --upgrade pip
	.env/bin/pip install --upgrade --requirement requirements.txt

.PHONY: setup-dev
setup-dev: setup
	.env/bin/pip install --upgrade --requirement requirements-dev.txt

.PHONY: install
install: setup
	.env/bin/pip install .

.PHONY: lint
lint: mypy
	.env/bin/pylint \
	    airports_bot
	.env/bin/black \
	    --line-length 120 \
	    --check \
	    --diff \
	    airports_bot

.PHONY: mypy
mypy:
	.env/bin/mypy \
	    airports_bot

.PHONY: format
format:
	.env/bin/black \
	    --line-length 120 \
	    airports_bot

.PHONY: run
run: setup
	PYTHONPATH=. .env/bin/python airports_bot/cli.py \
		--config config.ini \
		--verbose \
		--number 3

.PHONY: run-reset
run-reset: setup
	PYTHONPATH=. .env/bin/python airports_bot/cli.py \
		--config config.ini \
		--reset \
		--verbose
