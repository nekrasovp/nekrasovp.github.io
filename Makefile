help:
	@echo 'make markdown  Markdown-only smoke build (warnings are errors)'
	@echo 'make build     Full production build (blocked by legacy notebook reader)'
	@echo 'make serve     Local Markdown-only server (PORT=8000 by default)'
	@echo 'make test      SITE-001 acceptance tests'

markdown:
	./scripts/site markdown

serve:
	./scripts/site serve --port $(or $(PORT),8000)

build:
	./scripts/site build

test:
	./scripts/site test

.PHONY: help markdown build serve test
