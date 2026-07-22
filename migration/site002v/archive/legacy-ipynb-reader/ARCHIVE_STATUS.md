# Inactive comparison archive

This directory is the site's former vendored `ipynb.markup` reader. SITE-002V
moved it out of the active `plugins/` root so Pelican cannot discover or import
it through `PLUGIN_PATHS`.

It is retained temporarily only for validation comparison and license/history
review. Production-intent configuration imports the immutable external
`pelican.plugins.ipynb_reader` dependency. Do not add this directory to
`PLUGIN_PATHS` or restore `ipynb.markup`; SITE-002 owns removal after the final
released package replaces the validation pin.
