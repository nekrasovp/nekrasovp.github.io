Title: Upgrading OpenSSL on Ubuntu 18.04
Author: Nekrasov Pavel
Date: 2019-02-05 15:00
Category: blogging
Tags: linux, ubuntu, openssl
Slug: upgrading-openssl-ubuntu

To avoid openssl and TLS version issue we will update openSSL on server and desktop version of Ubuntu 18.04

We will download it manually, insall and make necessary file permission changes.

Let's begin with fetching the tarball from official site.
```bash
➜  wget https://www.openssl.org/source/openssl-1.1.1b.tar.gz
```
Next we unpack the tarball with tar and navigate to newly created folder
```bash
➜  tar -zxf openssl-1.1.1b.tar.gz
➜  cd openssl-1.1.1b/
```
Issue the command
```bash
➜  ./config
```
Issue the command make while you have gcc installed properly 
```bash
➜  make
```
Run make test to check for possible errors
```bash
➜  make test
```
Backup current openssl binary
```bash
➜  sudo mv /usr/bin/openssl ~/tmp
```
Issue the command
```bash
➜  sudo make install
```
Create symbolic link from newly install binary to the default location:
```bash
➜  sudo ln -s /usr/local/bin/openssl /usr/bin/openssl
```
Run the command sudo ldconfig to update symlinks and rebuild the library cache
```bash
➜  sudo ldconfig
```
Assuming that there were no errors in executing steps 4 through 10, you should have successfully installed the new version of OpenSSL.

Again, from the terminal issue the command:
```bash
➜  OpenSSL openssl version
OpenSSL 1.1.1b  26 Feb 2019

```
Finally we have to check files and folders permission in /etc/ssl/certs/ and /usr/share/ca-certificates
and change newly created file permission:
```bash
➜  sudo chmod o+rx ca-certificates.crt 
```


We can check openssl functionality with 
```bash
➜  openssl s_client -connect <remote_server_addresss>
```

