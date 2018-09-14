.PHONY: test all

all: test

test:
	PYTHONPATH="$(shell pwd)/scripts" pytest
