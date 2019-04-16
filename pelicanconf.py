#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Nekrasov Pavel'
SITENAME = 'Data driven blog'
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Europe/Moscow'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         ('Wikipedia', 'https://wikipedia.org'),)

# Social widget
SOCIAL = (('Facebook', 'https://www.facebook.com/nekrasovp'),
         ('BitBucket', 'https://bitbucket.org/Nekrasovp/'),)

DEFAULT_PAGINATION = False

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

# Use other output directory
OUTPUT_PATH = '../output'

# Theme path
THEME = 'theme'

BOOTSTRAP_THEME = 'flatly'

PYGMENTS_STYLE = 'monokai'

# Plugin paths
PLUGIN_PATHS = ['plugins/', ]

# Plugin list
PLUGINS = ['i18n_subsites', ]

JINJA_ENVIRONMENT = {
    'extensions': ['jinja2.ext.i18n'],
}