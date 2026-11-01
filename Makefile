.PHONY: test lint links
BATS ?= bats

test:            ## shellcheck + bats + markdown link check
	BATS=$(BATS) ./scripts/test.sh

lint:            ## shellcheck only
	shellcheck scripts/*.sh tests/check-links.sh

links:           ## markdown relative-link check only
	bash tests/check-links.sh
