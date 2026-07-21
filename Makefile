PY?=python3
UV?=uv
PELICAN?=$(UV) run --locked pelican
PELICANOPTS=

BASEDIR=$(CURDIR)
INPUTDIR=$(BASEDIR)/content
OUTPUTDIR?=$(BASEDIR)/.tmp/site
SMOKE_OUTPUTDIR?=$(BASEDIR)/.tmp/markdown-smoke
CONFFILE=$(BASEDIR)/pelicanconf.py
PUBLISHCONF=$(BASEDIR)/publishconf.py
BUILD_WRAPPER=$(BASEDIR)/migration/site_build/scripts/build.py


DEBUG ?= 0
ifeq ($(DEBUG), 1)
	PELICANOPTS += -D
endif

RELATIVE ?= 0
ifeq ($(RELATIVE), 1)
	PELICANOPTS += --relative-urls
endif

help:
	@echo 'Makefile for a pelican Web site                                           '
	@echo '                                                                          '
	@echo 'Usage:                                                                    '
	@echo '   make html                           run the full local build (red until notebook successor)'
	@echo '   make smoke                          run the SITE-001 Markdown-only smoke build'
	@echo '   make clean                          remove the generated files         '
	@echo '   make regenerate                     regenerate files upon modification '
	@echo '   make publish                        run the full production build (no publish side effect)'
	@echo '   make serve [PORT=8000]              serve Markdown smoke at http://localhost:8000'
	@echo '   make serve-global [SERVER=0.0.0.0]  serve Markdown smoke on $(SERVER)  '
	@echo '   make devserver [PORT=8000]          alias for Markdown smoke serve     '
	@echo '                                                                          '
	@echo 'Set the DEBUG variable to 1 to enable debugging, e.g. make DEBUG=1 html   '
	@echo 'Set the RELATIVE variable to 1 to enable relative urls                    '
	@echo '                                                                          '

html:
	$(UV) run --locked $(PY) $(BUILD_WRAPPER) build local --output $(OUTPUTDIR)

smoke:
	$(UV) run --locked $(PY) $(BUILD_WRAPPER) build markdown-smoke --output $(SMOKE_OUTPUTDIR)

clean:
	[ ! -d $(OUTPUTDIR) ] || rm -rf $(OUTPUTDIR)

regenerate:
	$(PELICAN) -r $(INPUTDIR) -o $(OUTPUTDIR) -s $(CONFFILE) --fatal errors $(PELICANOPTS)

serve:
ifdef PORT
	$(UV) run --locked $(PY) $(BUILD_WRAPPER) serve markdown-smoke --output $(SMOKE_OUTPUTDIR) --port $(PORT)
else
	$(UV) run --locked $(PY) $(BUILD_WRAPPER) serve markdown-smoke --output $(SMOKE_OUTPUTDIR)
endif

serve-global:
ifdef SERVER
	$(UV) run --locked $(PY) $(BUILD_WRAPPER) serve markdown-smoke --output $(SMOKE_OUTPUTDIR) --bind $(SERVER) --port $(or $(PORT),8000)
else
	$(UV) run --locked $(PY) $(BUILD_WRAPPER) serve markdown-smoke --output $(SMOKE_OUTPUTDIR) --bind 0.0.0.0 --port $(or $(PORT),8000)
endif


devserver:
ifdef PORT
	$(MAKE) serve PORT=$(PORT)
else
	$(MAKE) serve
endif

publish:
	$(UV) run --locked $(PY) $(BUILD_WRAPPER) build production --output $(OUTPUTDIR)


.PHONY: html smoke help clean regenerate serve serve-global devserver publish
