Title: Deploying a static website to bitbucket
Author: Nekrasov Pavel
Date: 2019-02-02 16:00
Category: Blog
Tags: python, markdown, pelican, bitbucket
Slug: deploying-a-static-website-to-bitbucket
Summary: We will use BitBucket for the task of hosting a small static website. The service is free and I already use BitBucket repositories to store the source code for my software projects so the workflow comes naturally.

We will use BitBucket for the task of hosting a small static website.
The service is free and I already use BitBucket repositories to store the source code for my software projects
so the workflow comes naturally.

#### Goals:
- [x] Create BitBucket repositories for your static website and its source code.
- [x] Go-live with your website on BitBucket.

#### Deployment To BitBucket
When building a static website it is a good idea to keep your website and its source code in two separate folders. 
To make things simple let's call the folders output and source just like the website in previous posts.
```bash
blog
└── output
└── source
```
We are going to create two BitBucket repositories: one to hold the static website and another to hold its source code.
The repository for the output folder must follow the pattern username.bitbucket.io. 
This is how BitBucket knows how to display the repo's contents as a website. 
The repository for the source folder can have any name we would like. 
We will use the repo name blog_source.
```bash
blog
└── output (repo: username.bitbucket.io)
└── source (repo: blog_source)
```
Login to BitBucket and create a new repository called username.bitbucket.io. 
Replace the word username with your actual BitBucket user name. 
Make the website public and do not initialize it with a readme file.

Immediately create a second repository called blog_source as well using the same settings as the first. 
Now we have two empty BitBucket repositories.

Open up the command line. If you are following along from a previous posts we should generate the website prior to deployment. 
Generate the website using the command below. We append -s publishconf.py to use settings that should only be applied when the website is being published.

```bash
pelican content -s publishconf.py
```

Now its time to use Git. 
While in the blog/output folder run the following git commands in order to push our files to the nekrasovp.bitbucket.io repository.

```bash
git init
git remote add origin git@bitbucket.org:Nekrasovp/nekrasovp.bitbucket.io.git
git add -A
git commit -m "initial commit"
git push --set-upstream origin master
```

Next, navigate to the blog/source folder run the following git commands in order to push our files to the blog_source repository:

```bash
git init
git remote add origin git@bitbucket.org:Nekrasovp/blog_source.git
git add -A
git commit -m "initial commit"
git push --set-upstream origin master
```

After running both sequences of Git commands we should be able to see our files loaded inti their respective repositories on BitBucket.
To view our website type https://username.bitbucket.io into your web browser.



