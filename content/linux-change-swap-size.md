Title: Change swap size in Ubuntu
Author: Nekrasov Pavel
Date: 2022-08-06 15:00
Category: Blog
Tags: linux
Slug: linux-change-swap-size
Summary: If you want to change the size of your swap file just follow the following steps.

## Change swap size in Ubuntu

In a nutshell swap is a piece of storage (used from your harddisk) which can be used as additional RAM. If you want to change the size of your swap file  just follow the following steps:
1. Turn off all running swap processes
   ```bash 
   swapoff -a
   ```
2. Resize swap (change **XG** to the gigabyte size you want it to be)
   ```bash 
   fallocate -l XG /swapfile
   ``` 
3. CHMOD swap
   ```bash 
   chmod 600 /swapfile
   ``` 
4. Make file usable as swap 
   ```bash 
   mkswap /swapfile
   ````
5. Active the swap file 
   ```bash 
   swapon /swapfile
   ```

Some commands may take some time to be executed, just wait patiently for the commands to finish.

To verify your swap size run the following command and you will see the swap size
```bash 
free -m
```
