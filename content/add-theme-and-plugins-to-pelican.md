Title: Add theme and plugins to Pelican installation
Author: Nekrasov Pavel
Date: 2019-02-02 16:00
Category: Blog
Tags: python, markdown, pelican
Slug: add-theme-and-plugins-to-pelican
Summary: The standard theme that comes with Pelican has one huge disadvantage: it does not display properly on mobile devices.
To accomplish this we will change our website to use the excellent pelican-bootstrap3 theme.


The standard theme that comes with Pelican has one huge disadvantage: it does not display properly on mobile devices.
To accomplish this we will change our website to use the excellent [pelican-bootstrap3](https://github.com/getpelican/pelican-themes/tree/master/pelican-bootstrap3) theme.
To view the full listing of Pelican themes click [here](https://github.com/getpelican/pelican-themes).

####Goals:
- [x] Setup the pelican-bootstrap3 theme
- [x] Setup necessary plugins. 
- [x] Make a config file.

Start by creating a new folder called theme in the source folder.
```bash
blog
  └── source
       ├── content
       └── theme (new)
```
Now we need to tell Pelican where it can find the custom theme we will be using. 
Open pelicanconf.py and add the following line:
```python
THEME = 'theme'
```
Next, go to GitHub and download the [pelican-bootstrap3](https://github.com/getpelican/pelican-themes/tree/master/pelican-bootstrap3) theme.
Place all pelican-bootstrap3 files into the blog/source/theme folder so it looks like this:
```bash 
blog
  └── source
       ├── content
       └── theme
           ├── static
           ├── templates
           ├── translations
           | ...(more files)
```

To avoid errors we have to install missing plugin i18n_subsites which is used by pelican-bootstrap3 to provide support for 
internationalization (i.e. i18n). 
We must download the [i18n_subsistes plugin](https://github.com/getpelican/pelican-plugins/tree/master/i18n_subsites) from Github and in include it in our project. 
To view the full listing of available Pelican plugins click [here](https://github.com/getpelican/pelican-plugins/tree/master/i18n_subsites).

Add another folder inside the source called plugins. Place the i18n_subsites folder and files you downloaded from Github into the plugins folder:
```bash
blog
  └── source
       ├── content
       ├── plugins (new)
       |   └── i18n_subsites (new)
       └── theme
```
We must tell Pelican where the plugins folder is located just as we did for the theme folder. 
Open pelicanconf.py and add the following line.
```python
PLUGIN_PATHS = ['plugins/', ]
```
A typical Pelican website will utilize many different plugins to extend its capabilities. 
Each plugin must be setup individually within pelicanconf.py. 
The PLUGINS variable contains all plugins being used by the website. 
Open pelicanconf.py and add the following line.
```python
PLUGINS = ['i18n_subsites', ]
```
The i18n_subsites plugin relies on a language called Jinja2. To properly configure the i18n_subsites plugin we must also add the JINJA_ENVIRONMENT variable to pelicanconf.py as shown below.
```python
JINJA_ENVIRONMENT = {
    'extensions': ['jinja2.ext.i18n'],
}
```
View the latest version of our website at [http://127.0.0.1:8000](http://127.0.0.1:8000). 
Notice when you expand and shrink the width of the web browser window the website layout changes to fit? 
By selecting a theme that incorporates responsive web design principles our website will be viewable on screens of all shapes and sizes.
Now that we have properly configured the bootstrap3 theme and its dependencies we can try to generate our site.
```bash
pelican content
pelican --listen
```
The pelican-bootstrap3 theme comes with several options to change the style of our website. 
To view the full list of available themes go the folder blog/source/theme/css. 
You will see several files with the filename bootstrap.(some name).min.css. 
We will be using the the bootstrap.flatly.min.css file to style our website. 
Open pelicanconf.py* and add the following line. 
Take a moment to try out some other options if you'd like to see what's available.
```python
BOOTSTRAP_THEME = 'flatly'
```
At this time we can also change the style for code blocks we may write in our blog posts. 
Pelican displays code blocks using the Pygments code highlighter. 
To view a full list of the available Pygments styles go to the folder blog/source/theme/css/pygments. 
Our website will use monokai.css to style code blocks. Add the following line to pelicanconf.py.
```python
PYGMENTS_STYLE = 'monokai'
```
Let's update the sidebar too with our own preferred links and social pages. 
You can use the websites shown below or choose your own. 
Update the following line in pelicanconf.py

```python
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         ('Wikipedia', 'https://wikipedia.org'),)

SOCIAL = (('Facebook', 'https://www.facebook.com/nekrasovp'),
         ('BitBucket', 'https://bitbucket.org/Nekrasovp/'),)
```
Regenerate the website to see the impact of changing the style. 
Not all of the changes we made to the style are apparent at this time because our website does not yet have any content.
In the next postsl we will learn how to create articles and pages for our blog.