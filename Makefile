help:
	@echo 'make markdown  Markdown-only smoke build (warnings are errors)'
	@echo 'make build     Full production-intent build (46 historical articles)'
	@echo 'make validate  Full SITE-002V deterministic and negative gates'
	@echo 'make serve     Local Markdown-only server (PORT=8000 by default)'
	@echo 'make test      SITE-001 acceptance tests'

markdown:
	./scripts/site markdown

serve:
	./scripts/site serve --port $(or $(PORT),8000)

build:
	./scripts/site build

validate:
	./scripts/site validate

test:
	./scripts/site test

.PHONY: help markdown build validate serve test
