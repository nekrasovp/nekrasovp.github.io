Title: How to rebase git branch
Author: Nekrasov Pavel
Date: 2022-04-21 12:00
Category: Blog
Tags: git
Slug: git-rebase
Summary: Choosing between git rebase and git merge remains one of the most discussed topics in the community.

## Abstract

Choosing between **git rebase** and **git merge** remains one of the most discussed topics in the community. Some may say that you should always use merging, some may say that rebasing is a more correct way to do things. There is no right or wrong way of using these two commands. It mainly depends on the user and the workflow. In the scope of this topic we will discuss how to rebase your branch.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Steps to rebasing branch](#steps-to-rebasing-branch)
  - [Fetching changes](#fetching-changes)
  - [Integrating changes](#integrating-changes)
  - [Pushing changes](#pushing-changes)
- [Rebasing vs Merging](#rebasing-vs-merging)
- [Fetching](#fetching)

## Steps to rebasing branch

Here are the steps to follow while rebasing a branch:

### Fetching changes

You should receive the latest changes from a remote git repository. Thus the first step is running git fetch:

```sh
git fetch
```

### Integrating changes

The second step is running **git rebase**. Rebase is a Git command which is used to integrate changes from one branch into another. The following command rebase the current branch from master (or choose any other branch like *develop*, suppose, the name of remote is origin, which is by default):

```sh
git rebase origin/master
```

After **git rebase**, conflicts may occur. You should resolve them and add your changes by running git add command:

```sh
git add .
```

After resolving the conflicts and adding the changes to the staging area, you must run git rebase with the --continue option:

```sh
git rebase --continue
```

If you want to cancel the rebasing rather than resolving the conflicts, you can run the following:

```sh
git rebase --abort
```

### Pushing changes

The final step is **git push** (forced). This command uploads local repository content to a remote repository. To do that, run the command below:

```sh
git push origin HEAD -f
```

**--force** that is the same as **-f** overwrites the remote branch on the basis of your local branch. It destroys all the pushed changes made by other developers. It refers to the changes that you don't have in your local branch.

Here is an alternative and safer way to push your changes:

```sh
git push --force-with-lease origin HEAD
```

**--force-with-lease** is considered a safer option that will not overwrite the work done on the remote branch in case more commits were attached to it (for instance, by another developer). Moreover, it helps you to avoid overwriting another developer's work by force pushing.

## Rebasing vs Merging

Rebasing and merging are both used to integrate changes from one branch into another differently. They are both used in different scenarios. If you need to update a feature branch, always choose to **git rebase** for maintaining the branch history clean. It keeps the commit history out of the branch, contrary to the **git merge** command, which is its alternative. While, for individuals, rebasing is not recommended in the case of feature branch because when you share it with other developers, the process may create conflicting repositories. Once you need to put the branch changes into master, use merging. If you use merging too liberally, it will mess up **git log** and make difficult to understand the history. Merging preserves history whereas rebasing rewrites it. If you need to see the history absolutely the same as it happened, then use merge.

## Fetching

The git fetch command downloads commits, files, and refs from a remote repository into the local repository. It updates your remote-tracking branches. The git fetch command allows you to see the progress of the central history, not forcing you to merge the changes into your repository. It does not affect your local work process.
