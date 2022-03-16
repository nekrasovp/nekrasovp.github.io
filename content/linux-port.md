Title: Ways to find out which process is listening on a specific port
Author: Nekrasov Pavel
Date: 2022-03-16 15:00
Category: Blog
Tags: linux
Slug: linux-port
Summary: In this article, we will show three different ways to find the process listening on a specific port in Linux.

## Abstract

There are at least three ways to find out which *process* is listening on a particular *port*. 

A *port* is a logical object that represents a communication endpoint and is associated with a process or service in the operating system.

In this article, we will show three different ways to find the *process* listening on a specific *port* in Linux.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Using the netstat command](#using-the-netstat-command)
- [Using the lsof command](#using-the-lsof-command)
- [Using the fuser command](#using-the-fuser-command)

## Using the netstat command

The **netstat** (network statistics) command is used to display information about network connections, routing tables, interface statistics, and beyond. It is available on all Unix-like operating systems, including Linux, as well as on Windows.

If **netstat** is not installed by default, use the following command to install it:

```bash
sudo yum install net-tools #RHEL/CentOS
sudo apt install net-tools #Debian/Ubuntu
sudo dnf install net-tools #Fedora 22+
```

Once installed, you can use **netstat** along with **grep** to find the *process* listening on a specific *port* on Linux like so:

```bash
sudo netstat -ltnp | grep -w ':80'
```

The above command uses the following options:

- **l** instructs **netstat** to show only listening sockets.
- **t** - indicates the display of tcp connections.
- **n** - indicates that it is necessary to show ip-addresses.
- **p** - allows you to show the process ID and process name.
- **grep -w** - matches exact string (':80').

## Using the lsof command

The **lsof** (LiSt Open Files) command is used to list all open files on a Linux system. To install it on your system, enter the command below.

```bash
sudo yum install lsof #RHEL/CentOS
sudo apt install lsof #Debian/Ubuntu
sudo dnf install lsof #Fedora 22+
```

To find the process listening on a specific port, type:

```bash
sudo lsof -i :80
```

The above command uses the following options:

- **i** lists IP sockets.

## Using the fuser command

**fuser** shows the PID of processes using specified files or filesystems on Linux.

You can install it like this:

```bash
sudo yum install psmisc #RHEL/CentOS
sudo apt install psmisc #Debian/Ubuntu
sudo dnf install psmisc #Fedora 22+
```

You can find the process listening on a specific port by running the command below:

```bash
sudo fuser 22/tcp
```

Then find the process name using the **PID** number, with the **ps** command:

```bash
sudo ps -p 177
```

The above command uses the following options:

- **p** specific process PID
