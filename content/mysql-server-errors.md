Title: MySQL server has gone away errors
Author: Nekrasov Pavel
Date: 2023-07-11 13:00
Category: Blog
Tags: mysql, linux
Slug: mysql-server-errors
Summary: This post is about errors after "The MySQL server has gone away", which means that the MySQL server (mysqld) timed out and closed the connection.

## Abstract

MySQL server has gone away, can be a frustrating error to solve. This is partly because, to solve this error, sometimes the solution involves multiple layers, application, or service config changes. This article includes solutions I’ve seen for this MySQL server general error.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [MySQL server has gone away error log examples](#mysql-server-has-gone-away-error-log-examples)
- [MySQL wait\_timeout](#mysql-wait_timeout)
- [MySQL max\_allowed\_packet](#mysql-max_allowed_packet)
- [MySQL innodb\_log\_file\_size](#mysql-innodb_log_file_size)
- [Other causes of MySQL server has gone away](#other-causes-of-mysql-server-has-gone-away)
  - [MySQL database charset and collation](#mysql-database-charset-and-collation)
  - [Exceeding MySQL max\_connections setting](#exceeding-mysql-max_connections-setting)
- [Still unresolved? See MySQL’s help page](#still-unresolved-see-mysqls-help-page)

## MySQL server has gone away error log examples

Keep in mind that this error can be logged in a few ways, as listed below. In addition, at times, the error is only an indication of a deeper underlying issue. This means the error could be due to a problem or bug in your connecting application or remote service. In this case, you need to check ALL related error logs with the same timestamp to determine whether another issue may be to blame. Here are error log examples of the MySQL server has gone away error:

```General error: 2006 MySQL server has gone away```

```Error Code: 2013. Lost connection to MySQL server during query```

```Warning: Error while sending QUERY packet```

```PDOException: SQLSTATE[HY000]: General error: 2006 MySQL server has gone away```

## MySQL wait_timeout

The reason for MySQL server has gone away error is often because MySQL’s *wait_timeout* was exceeded. MySQL *wait_timeout* is the number of seconds the server waits for activity on a non-interactive connection before closing it. You should make sure the *wait_timeout* is not set too low. The default for MySQL *wait_timeout* is 28800 seconds. Often, it gets lowered arbitrarily. That said, the lower you can set *wait_timeout* without affecting database connections can be a good sign of MySQL database efficiency. 

Also, check the variables: *net_read_timeout*, *net_write_timeout* and *interactive_timeout*. Adjust or add the following lines in my.cnf to meet your requirements:

```wait_timeout=90
net_read_timeout=90
net_write_timeout=90
interactive_timeout=300
connect_timeout=90
```

## MySQL max_allowed_packet

*max_allowed_packet* is the maximum size of one packet. The default size of 4MB helps the MySQL server catch large (possibly incorrect) packets. As of MySQL 8, the default has been increased to 16MB. If mysqld receives a packet that is too large, it assumes that something is wrong and closes the connection. To fix this, you should increase the *max_allowed_packet* in my.cnf, then restart MySQL. The max for this setting is 1GB. For example:

```
max_allowed_packet = 512M
```

## MySQL innodb_log_file_size

You may need to increase the *innodb_log_file_size* MySQL variable in your my.cnf configuration. MySQL’s *innodb_log_file_size* should be 25% of *innodb_buffer_pool_size* (if possible, no less than 20%). Remember that the larger this value, the longer it will take to recover from a database crash.

This means, for example, if your buffer pool size is set to *innodb_buffer_pool_size*=16G and your *innodb_log_files_in_group* setting is still set to the recommended default of 2 files (*innodb_log_files_in_group*=2), then your *innodb_log_file_size* should be set to 2G. This will create two (2) log files at 2GB each, which equals 25% of *innodb_buffer_pool_size*=16G.

**WARNING**: You must stop MySQL server in order to change *innodb_log_file_size* or *innodb_log_files_in_group*. If you don’t, you risk catastrophe! (Read: [MySQL Log Redo instructions](https://dev.mysql.com/doc/refman/8.0/en/innodb-redo-log.html).)

## Other causes of MySQL server has gone away

### MySQL database charset and collation

Changing the default database charset to latin1 and default collation to latin1_general_ci seemed to have solved MySQL server has gone away for sometimes.

### Exceeding MySQL max_connections setting

*Max_connections* set the maximum permitted number of simultaneous client connections. Be careful with this setting!! Exhaustion of memory and other resources can occur [when set too large](https://linuxblog.io/my-cnf-tuning-avoid-this-common-pitfall/) and scheduling overhead also increases. As a guide, set *max_connections* to approximately double the previous number of maximum simultaneous client connections. E.g., if after a month of uptime, the maximum simultaneous client connections were 114, then set to *max_connections*=250. Before you go crazy with this setting, please read: [How MySQL Handles Client Connections](https://dev.mysql.com/doc/refman/8.0/en/client-connections.html).

## Still unresolved? See MySQL’s help page

Oracle has put together a [nice self-help page for MySQL server has gone away](https://dev.mysql.com/doc/refman/8.0/en/gone-away.html) errors. On that page, they also suggest that you make sure MySQL didn’t stop/restart during the query. Excerpt:

“You can check whether the MySQL server died and restarted by executing [mysqladmin version](https://dev.mysql.com/doc/refman/8.0/en/mysqladmin.html) and examining the server’s uptime. If the client connection was broken because [mysqld](https://dev.mysql.com/doc/refman/8.0/en/mysqld.html) crashed and restarted, you should concentrate on finding the reason for the crash.”
