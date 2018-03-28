MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

PHONY: release
release:
	python setup.py sdist bdist_wheel
	twine upload ./dist/*
	git tag -s v$(shell python setup.py --version) -m "v$(shell python setup.py --version)" $(shell git rev-parse HEAD)
	git push --tags

PHONY: clean
clean:
	rm -rf build dist goodconf.egg-info

PHONY: test
test:
	pytest --cov=goodconf --cov-report=term
