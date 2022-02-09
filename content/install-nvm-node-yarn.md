Title: Install nvm, node and yarn for your Node.js application
Author: Nekrasov Pavel
Date: 2022-01-11 15:00
Category: Blog
Tags: nvm, node, yarn
Slug: install-nvm-node-yarn
Summary: The official package manager for node is npm which comes pre-installed with node. We use npm to install yarn

## Abstract

The official package manager for node is npm which comes pre-installed with node. You use npm to install yarn — so you do things in this order nvm -> node/npm -> yarn.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Install nvm](#install-nvm)
- [Use nvm to install node/npm](#use-nvm-to-install-nodenpm)
- [Use npm to Install yarn](#use-npm-to-install-yarn)
- [Summary](#summary)

## Install nvm

Open a terminal on your system or connect a remote system using SSH. Use the following commands to install curl on your system, then run the nvm installer script.

```sh
sudo apt install curl
curl https://raw.githubusercontent.com/creationix/nvm/master/install.sh | bash 
```

The nvm installer script creates environment entry to login script of the current user. You can either logout and login again to load the environment or execute the below command to do the same.

```sh
source ~/.profile  
```

Now check nvm installation with next command

```sh
nvm --version
```

## Use nvm to install node/npm

Run next command to find the available node.js version for the installation.

```sh
nvm ls-remote 
```

We will use v12.22.10 at this time, simply run

```sh
nvm install v12.22.10
```

Check locally installed node versions run

```sh
nvm list
```

You can also select a different version for the current session. The selected version will be the currently active version for the current shell only.

```sh
nvm use v12.22.10
```

To confirm it worked, run *node --version* — if you see a version number, you’re in business!
Note that *npm --version* should also now succeed.

## Use npm to Install yarn

To install yarn, simply run

```sh
npm install --global yarn
```

To confirm it worked, run *yarn --version* — if that works, you’re good to go!

## Summary

Congratulations, you just installed nvm, node+npm, and yarn, and you’re now ready to tun your node.js application.
