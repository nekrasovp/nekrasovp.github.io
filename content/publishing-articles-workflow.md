Title: Publishing articles workflow
Author: Nekrasov Pavel
Date: 2020-09-09 15:00
Category: Blog
Tags: markdown 
Slug: publishing-articles-workflow
Summary: In this article, I would like to document my blogging experience. After writing and distributing articles for a long time, I kind of set up a framework when it comes to distributing articles.

## Abstract

In this article, I would like to document my blogging experience. 
After writing and distributing articles for a long time, 
I kind of set up a framework when it comes to distributing articles. 
From idea to pushing the spread button. Of course, this structure is constantly evolving, 
and over time I have tried to change it to suit my needs.

## Contents

* [Abstract](#abstract)
* [Idea](#idea)
* [Article writing](#article-writing)
* [Article checking](#article-checking)
* [Article publishing](#article-publishing)

## Idea

It's simple, the idea comes from a self-learning process. Whenever I find myself in a situation 
where I don't understand certain concepts, I first try to fully understand the topic. 
And when I reach a certain level of understanding, I try to describe the concept in my own words. 
So that I can understand when I look at this next time.

_This means that I primarily write articles for myself only. 
And if my articles are useful to someone, it will be an additional bonus!_

## Article writing

I use [VS Code][vs-code] to write articles because articles are written in 
Markdown, in my opinion, VS Code offers a few very useful plugins. 
To get started on a new article, all I have to do is create a blank Markdown file and start writing.

To make it even better, I use a VS Code extension called [Markdown All in One][markdown-all-in-one],
which adds some important things like keyboard shortcuts, table of contents, auto preview, linter, 
and more when it comes to Markdown.

## Article checking

When the article is written, I go to [grammarly.com][grammarly] and paste the entire article to 
check spelling and grammar errors.
On top of that, it also offers alternative words and unnecessary word removal, which can make 
reading enjoyable.

_In the past, I didn't care much about my articles being grammatically correct. 
But over time, I realized that this is important for the reader. So, this important step has entered my workflow._

## Article publishing

At the moment, everything is in place and the article is ready for publication. 
A simple git push is enough to post the article in my case, 
since I have hosted my [blog][blog] on GitHub pages and it starts a new build every time I push to
 Git.

I described this automation in next [article][git-hooks-article].

After the code is published, it will take around 10 seconds for the article to appear on the 
blog and for the atom feed to update.

For a full-fledged repost on social networks in the future, 
I plan to add automatic banner creation to the workflow.

[vs-code]: https://code.visualstudio.com
[markdown-all-in-one]: https://marketplace.visualstudio.com/items?itemName=yzhang.markdown-all-in-one
[grammarly]: https://app.grammarly.com
[blog]: https://nekrasovp.github.io
[git-hooks-article]: https://nekrasovp.github.io/pelican-github-script-automation.html