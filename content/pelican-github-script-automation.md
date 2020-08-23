Title: Move blog to github and automate deploying with git hooks
Author: Nekrasov Pavel
Date: 2020-08-22 20:00
Category: Blog
Tags: pelican, git, github
Slug: pelican-github-script-automation
Summary: In this post we will describe how to move your blog to github and automate git hooks tho
 update gh
-pages branch on commits

This blog is powered by [Pelican](http://docs.getpelican.com/en/stable) and hosted through 
GitHub using [GitHub Pages](https://pages.github.com/). 

In this post we will describe how to move blog to github and automate git hooks to update gh
-pages branch on commits.

For those of you not familiar with these technologies, 
Pelican is a static site generator - meaning you can write your content in a format such as 
Markdown or Jupyter notebook(ipynb) and Pelican will automatically generate the HTML files for you; 
and GitHub Pages is a service provided by GitHub for hosting a 
website under the <your-username>.github.io URL.

Previously when blog was hosted on bitbucket we solve it using two separate repositories: one for
 the
 website "source" files, and one for the output which was be served using bitbucket.io.

But i decide to move to one repository with different branches. This is how to achieve this:

The first step is to create two *branches*:

- **master** will contain the blog's "source" files, namely - all the files such as the content
 folder
 which contains the actual posts, and pelicanconf.py file.
- **gh-pages** will contain only the contents of output.

Github will use **gh-pages** branch for serving [Blog pages](https://nekrasovp.github.io/)

Then update your .gitignore file with output\ folder.

To automate lets create *pre-push* git hook in `.git/hooks/pre-push`:

```bash
#!/bin/sh

while read local_ref local_sha remote_ref remote_sha
do
        if [ "$remote_ref" = "refs/heads/master" ]
        then
                pelican content -o output -s publishconf.py
                ghp-import -m "Update with latest content" output
                git push --no-verify origin gh-pages
        fi
done

exit 0
```

1. The first thing the script does is iterating over the commits that are about to be pushed. 
Specifically, only commits that are pushed to the **master** branch are of interest to us.
2. If commits are pushed to **master**, it executes pelican command using publishconf.py. 
This will generate the production version of the blog into output.
3. The [GitHub Pages Import](https://pypi.org/project/ghp-import/) tool is used for copying the contents of output to a branch named 
**gh-pages** with provided commit message.
4. **gh-pages** is pushed to the remote **gh-pages** branch. --no-verify skips the pre-push hook
 so this script won't run again.

Now, whenever I push to source to **master** branch i get fresh version of my static site on github
 pages at the same time.
 
We can use different ways to achieve the same goal, 
check this post [Using git worktree for deploying to GitHub Pages](https://musteresel.github.io/posts/2018/01/git-worktree-for-deploying.html) about git worktree automation.

We can even build pages on remote servers, 
check this [GitHub Pages Pelican Build Action](https://github.com/nelsonjchen/gh-pages-pelican-action) 
and [GitHub Pages Pelican Build Action Demo](https://github.com/nelsonjchen/pelican-action-demo) for example.