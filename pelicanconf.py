#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Nekrasov Pavel'
SITENAME = 'Data driven'
SITESUBTITLE = 'Nekrasov Pavel personal page'
SITEURL = ''
TIMEZONE = 'Europe/Moscow'

FAVICON = 'images/logo2.png'

PATH = 'content'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Banner Image
BANNER = 'images/wireframe2.png'
BANNER_SUBTITLE = 'Nekrasov Pavel personal page'
BANNER_ALL_PAGES = False

HIDE_SITENAME = False

DISPLAY_CATEGORY_IN_BREADCRUMBS = True

SITELOGO = 'images/logo2.png'

DISPLAY_ARTICLE_INFO_ON_INDEX = True

DISPLAY_TAGS_ON_SIDEBAR = True

DISPLAY_TAGS_INLINE = True

DISQUS_SITENAME = "nekrasovp"

# ABOUT_ME = 'Some info about me'
# AVATAR = 'images/noava-160x160.png'

# Blogroll
# LINKS = (('Markdown', 'https://github.com/adam-p/markdown-here/wiki/Markdown-Here-Cheatsheet'),
#          ('Pelican', 'http://getpelican.com/'),
#          ('Python.org', 'http://python.org/'),)

# Social widget
SOCIAL = (
          ('LinkedIn', 'https://linked.in/in/nekrasovp'),
          ('GitHub', 'https://github.com/nekrasovp/'),
          ('BitBucket', 'https://bitbucket.org/Nekrasovp/'),
          ('GitLab','https://gitlab.com/Nekrasovp'),
          ('Message','https://t.me/def12', 'message'),
          ('E-mail', 'mailto:nekrasovp@gmail.com', 'envelope'),
          )

DEFAULT_PAGINATION = 7
DEFAULT_DATE = (2021, 3, 2, 14, 1, 1)

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True

# Use other output directory
OUTPUT_PATH = '/output'

# static paths will be copied without parsing their contents
STATIC_PATHS = [
    'images',
]

# Theme path
THEME = 'theme'

BOOTSTRAP_THEME = 'flatly'

PYGMENTS_STYLE = 'friendly'

MARKUP = ('md', 'ipynb')

# if you create jupyter files in the content dir, snapshots are saved with the same
# metadata. These need to be ignored.
IGNORE_FILES = [".ipynb_checkpoints"]

IPYNB_GENERATE_SUMMARY = True

# Plugin paths
PLUGIN_PATHS = ['plugins/']

# Plugin list
PLUGINS = ['i18n_subsites', 'related_posts', 'tag_cloud', 'ipynb.markup']

# IPYNB_FIX_CSS = False
IPYNB_SKIP_CSS = True

JINJA_ENVIRONMENT = {
    'extensions': ['jinja2.ext.i18n'],
}
