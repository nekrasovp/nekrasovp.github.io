Title: How to List Users in Linux
Author: Nekrasov Pavel
Date: 2022-08-07 15:00
Category: Blog
Tags: linux
Slug: linux-list-users
Summary: This article will show you how to list users in Linux systems.

## Abstract

Have you ever wanted to list all users in your Linux system or to count the number of users in the system? There are commands to create a user, delete a user, list logged in users, but what is the command to list all users in Linux?

This article will show you how to list users in Linux systems.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Get a List of All Users using the /etc/passwd File](#get-a-list-of-all-users-using-the-etcpasswd-file)
- [Get a List of all Users using the getent Command](#get-a-list-of-all-users-using-the-getent-command)
  - [Check whether a user exists in the Linux system](#check-whether-a-user-exists-in-the-linux-system)
  - [System and Normal Users](#system-and-normal-users)
- [Conclusion](#conclusion)

## Get a List of All Users using the /etc/passwd File

Local user information is stored in the */etc/passwd* file. 
Each line in this file represents login information for one user. 
To open the file you can either use **cat** or **less** :+

```bash
less /etc/passwd
```

Each line in the file has seven fields delimited by colons that contain the following information:

- User name.
- Encrypted password (x means that the password is stored in the /etc/shadow file).
- User ID number (UID).
- User’s group ID number (GID).
- Full name of the user (GECOS).
- User home directory.
- Login shell (defaults to **/bin/bash**).

If you want to display only the username you can use either **awk** or **cut** commands to print only the first field containing the username:

```bash
awk -F: '{ print $1}' /etc/passwd
```

```bash
cut -d: -f1 /etc/passwd
```

## Get a List of all Users using the getent Command

The **getent** command displays entries from databases configured in **/etc/nsswitch.conf** file, including the passwd database, which can be used to query a list of all users.

To get a list of all Linux userr, enter the following command:

```bash
getent passwd
```

As you can see, the output is the same as when displaying the content of the **/etc/passwd** file. If you are using LDAP for user authentication, the **getent** will display all Linux users from both **/etc/passwd** file and LDAP database.

You can also use **awk** or **cut** to print only the first field containing the username:

```bash
getent passwd | awk -F: '{ print $1}'
```

```bash
getent passwd | cut -d: -f1
```

### Check whether a user exists in the Linux system

Now that we know how to list all users, to check whether a user exists in our Linux box we, can simply filter the users’ list by piping the list to the grep command.

For example, to find out if a user with name jack exists in our Linux system we can use the following command:

```bash
getent passwd | grep jack
```

If the user exists, the command above will print the user’s login information. No output that means the user doesn’t exist.

We can also check whether a user exists without using the **grep** command as shown below:

```bash
getent passwd jack
```

Same as before, if the user exists, the command will display the user’s login information.

If you want to find out how many users accounts you have on your system, pipe the getent passwd output to the wc command:

```bash
getent passwd | wc -l
```

### System and Normal Users

There is no real technical difference between the system and regular (normal) users. Typically system users are created when installing the OS and new packages. In some cases, you can create a system user that will be used by some applications.

Normal users are the users created by the root or another user with sudo privileges. Usually, a normal user has a real login shell and a home directory.

Each user has a numeric user ID called UID. If not specified when creating a new user with the **useradd** command, the UID will be automatically selected from the /etc/login.defs file depending on the **UID_MIN** and **UID_MAX** values.

To check the **UID_MIN** and **UID_MAX** values on your system, you can use the following command:

```bash
grep -E '^UID_MIN|^UID_MAX' /etc/login.defs
```

From the output above, we can see that all normal users should have a UID between 1000 and 60000. Knowing the minimal and maximal value allow us to query a list of all normal users in our system.

The command below will list all normal users in our Linux system:

```bash
getent passwd {1000..60000}
```

Your system UID_MIN and UID_MIN values may be different so the more generic version of the command above would be:

```bash
eval getent passwd {$(awk '/^UID_MIN/ {print $2}' /etc/login.defs)..$(awk '/^UID_MAX/ {print $2}' /etc/login.defs)}
```

If you want to print only the usernames just pipe the output to the cut command:

```bash
eval getent passwd {$(awk '/^UID_MIN/ {print $2}' /etc/login.defs)..$(awk '/^UID_MAX/ {print $2}' /etc/login.defs)} | cut -d: -f1
```

## Conclusion
In this tutorial, you learned how to list and filter users in your Linux system and what are the main differences between system and normal Linux users.

The same commands apply for any Linux distribution, including Ubuntu, CentOS, RHEL, Debian, and Linux Mint.

Feel free to leave a comment if you have any questions.
