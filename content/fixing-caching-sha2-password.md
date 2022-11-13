Title: Authentication plugin 'caching_sha2_password' cannot be loaded
Author: Nekrasov Pavel
Date: 2022-06-15 12:00
Category: Blog
Tags: mysql
Slug: fixing-caching-sha2-password
Summary: Fixing "Authentication plugin 'caching_sha2_password' cannot be loaded. The specific module can not be found" errors

## Contents

- [Contents](#contents)
- [Summary](#summary)
- [Reason](#reason)
- [Resolution](#resolution)
- [References](#references)

## Summary

You have installed MySQL 8 and are unable to connect your database using your MySQL client. Every attempt to connect using your MySQL client results in the following error:

```
Authentication plugin 'caching_sha2_password' cannot be loaded: dlopen(/usr/local/mysql/lib/plugin/caching_sha2_password.so, 2): image not found
```

or

```
Authentication plugin 'caching_sha2_password' cannot be loaded. The specific module can not be found
```

## Reason

As of MySQL 8.0, **caching_sha2_password** is now the default authentication plugin rather than **mysql_native_password** which was the default in previous versions. This means that clients that rely on the **mysql_native_password** won't be able to connect because of this change.

## Resolution

At a server level, revert to the mysql_native_password mechanism by adding the following to your MySQL configuration files:

```cfg
[mysqld]
default_authentication_plugin=mysql_native_password
```

At a user level, revert to the mysql_native_password mechanism via the following process.

Open a terminal window and connect to your MySQL instance via the command line:

```sh
mysql -u [USERNAME] -p
```

Enter your MySQL password and press enter and you should be logged into your MySQL instance.

Now run the following SQL command, replacing `[USERNAME]`, `[PASSWORD]` and `[HOST]` as appropriate.

Note: `[HOST]` can be the IP address of your computer which would allow access from your computer only or, in the case of a local development environment, you can use % to allow from any host.

```sql
ALTER USER '[USERNAME]'@'[HOST]' \
  IDENTIFIED WITH mysql_native_password \
  BY '[PASSWORD]';
```

or

```sql
ALTER USER '[USERNAME]'@'%' \
  IDENTIFIED WITH mysql_native_password \
  BY '[PASSWORD]';
```

Now you should be able to go back to your MySQL client and connect as normal.

## References

2.11.4 Changes in MySQL 8.0 - https://dev.mysql.com/doc/refman/8.0/en/upgrading-from-previous-series.html

6.4.1.2 Caching SHA-2 Pluggable Authentication - https://dev.mysql.com/doc/refman/8.0/en/caching-sha2-pluggable-authentication.html