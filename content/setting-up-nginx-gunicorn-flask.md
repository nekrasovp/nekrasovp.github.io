Title: Setting Up Nginx, Gunicorn for Flask app 
Author: Nekrasov Pavel
Date: 2021-11-03 15:00
Category: Blog
Tags: nginx, gunicorn, flask, python
Slug: setting-up-nginx-gunicorn-flask
Summary: This article describes how to configure a Nginx and gunicorn to run Flask app.

## Abstract

In this article we will to go through the process of deploying a flask app on a Linux server. We will use gunicorn as a WSGI server to communicate with our flask app, and Nginx as a proxy server between the gunicorn server and the client.

We need gunicorn between flask and nginx because the flask development server although good for debugging is weak and will not stand in production, so we need gunicorn as a wsgi server to communicate with flask.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Install pre-requisite packages](#install-pre-requisite-packages)
- [Create Python Virtual Environment](#create-python-virtual-environment)
- [Install flask and gunicorn packages](#install-flask-and-gunicorn-packages)
- [Setup Flask Web Application](#setup-flask-web-application)
- [Configure Gunicorn](#configure-gunicorn)
  - [Create WSGi Entry Point](#create-wsgi-entry-point)
  - [Access Flask web app using Gunicorn](#access-flask-web-app-using-gunicorn)
- [Configuring Nginx](#configuring-nginx)
- [Summary](#summary)

## Install pre-requisite packages

Firstly, we need to make sure that python3 is installed on the Linux, run the following command to test if python exists:

```sh
$ python3.9 --version
Python 3.9.9
```

However, if python is not installed, you can install it using the following commands:

Update the repository

```sh
$ sudo apt update
```

Install python

```ah
$ sudo apt install python3.9
```

Now we need to make sure that pip (python's package manager) is installed. Run the following command:

```sh
$ python3.9 -m pip --version
pip 20.0.2 from /usr/lib/python3/dist-packages/pip (python 3.9)
```

If pip is not installed then you can install the same using this command:

```sh
$ sudo apt install python3.9-pip
```

## Create Python Virtual Environment

Before installing any of the packages that we are going to use, we need to create a python virtual environment to keep different versions of packages separated.

We will create a separate directory to store our project files:

```sh
$ mkdir flask-gunicorn
```

Move to the directory that contains your project and create a virtual environment named *venv*  (or any name):

```sh
$ cd flask-gunicorn
$ python3.9 -m venv venv
```

The above command will create a directory named *venv/* that contains everything related to the virtual environment including the binary file that activates the virtual environment, to activate *venv* virtual environment run the following command:

```sh
$ source venv/bin/activate
```

Once we install python packages, they will be stored in *venv/lib/python-version/site-packages*

## Install flask and gunicorn packages

Once the virtual environment is activated, we are ready to install the packages that we need:

```sh
(venv) $ python -m pip install flask gunicorn
```

## Setup Flask Web Application

Now since Flask is successfully installed, we will create python web application using flask. We will start by creating a python file and naming it "app.py":

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello world!'

if __name__ == '__main__':
    app.run()
```

To start the python web application, just execute app.py using python binary as shown below:

```sh
$ python app.py
 * Serving Flask app 'app' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
```

Access 127.0.0.1:5000 on your browser of the same Linux server and you should be able to get "Hello World!" message.

Hit *Ctrl+C* on your terminal to exit the web application once you are finished.

## Configure Gunicorn

Now that our basic web app is up and running, we will continue to configure Gunicorn. Using our Flask application from earlier, we can get it up and running using just a few steps

### Create WSGi Entry Point

First, we need to create a python file that will be used as an entry point to our application by gunicorn, we will name it wsgi.py:

```python
from app import app

if __name__ == "__main__":
    app.run()
```

### Access Flask web app using Gunicorn

Gunicorn offers a lot of command line options (flags) which can be used to tune the performance of the server to match your needs, the most commonly used options are `-w` to specify the number of workers that the server will use and  `--bind` which specify the interface and port to which the server should bind (`0.0.0.0` will be your server's public IP address)

Now we can test the gunicorn server and see whether it can run the flask app, use the following command to start the gunicorn server with 4 workers `-w` (You can increase or decrease the number of workers depending on your server's specs), we also need to specify the interface and the port to which the server should bind using the `--bind` command line option:

```sh
(venv) $ python -m gunicorn -w 4 --bind 127.0.0.1:8000 wsgi:app
[2021-11-03 14:27:01 +0300] [15406] [INFO] Starting gunicorn 20.1.0
[2021-11-03 14:27:01 +0300] [15406] [INFO] Listening at: http://127.0.0.1:8000 (15406)
[2021-11-03 14:27:01 +0300] [15406] [INFO] Using worker: sync
[2021-11-03 14:27:01 +0300] [15407] [INFO] Booting worker with pid: 15407
[2021-11-03 14:27:01 +0300] [15408] [INFO] Booting worker with pid: 15408
[2021-11-03 14:27:02 +0300] [15409] [INFO] Booting worker with pid: 15409
[2021-11-03 14:27:02 +0300] [15410] [INFO] Booting worker with pid: 15410
```

As seen in the above output, the gunicorn server is listening on port 8000 of  the localhost, and 4 workers have started each with a different process Id (PID). If you visit `127.0.0.1:8000/`, you will see the root directory of your website (same as we say with python web app on port 5000 earlier:

## Configuring Nginx

Let's start by installing nginx:

```sh
$ sudo apt install nginx
```

Then navigate to the nginx directory:

```sh
$ cd /etc/nginx/
```

This directory contains all the files related to nginx, we need to create a configuration file that will make nginx act as a proxy for our flask app.

The main configuration file is the one named `nginx.conf`, by convention, this file is not touched by developers or sys-admins, new configuration files are created in the `sites-available/` directory and then sym-linked to the `/sites-enabled/ `directory.

Let's create a new file called `my-server` in the `sites-available/` directory:

```
server {
    listen 80;

    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/my-server/ipc.sock;
    }
}
```

Next run the `sudo nginx -t` to make sure that the syntax of the configuration file is ok

```sh
$ sudo nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

Once the syntax check passes, create a symbolic link of this file into sites-enabled directory:

```sh
$ sudo ln -s /etc/nginx/sites-available/my-server /etc/nginx/sites-enabled/

$ sudo ls -l  /etc/nginx/sites-enabled/
total 0
lrwxrwxrwx 1 root root 34 Nov 03 10:56 default -> /etc/nginx/sites-available/default
lrwxrwxrwx 1 root root 36 Nov 03 11:05 my-server -> /etc/nginx/sites-available/my-server
```

If everything is fine run `sudo nginx -s reload` for the configuration file to take place:

```sh
$ sudo nginx -s reload
```

The above configurations instructs nginx to listen on port 80 and proxy all the connections to the socket that we created earlier, so that gunicorn can read from the socket and allows our flask app to respond, then gunicorn takes the response from the flask app and writes it to the socket so that nginx can read from the socket and return the response to the user.

## Summary

In this article, we went through the process of deploying a flask app using gunicorn and nginx. This setup allows us to utilize the concurrency of gunicorn and nginx and also facilitates the scaling process in case of an expansion.
