Title: Python app with poetry & docker
Author: Nekrasov Pavel
Date: 2023-02-20 12:00
Category: Blog
Tags: python, poetry, development
Slug: python-poetry-docker
Summary: This post is about building multi-stage docker image with python app and poetry.

## Abstract

This post is about building multi-stage docker image with python app and poetry.

Lets start from the end? here is the final Dockerfile:

```bash
FROM python:3.11-slim as os-base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
RUN apt-get update
RUN apt-get install -y curl

FROM os-base as poetry-base

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.poetry/bin:$PATH"
RUN poetry config virtualenvs.create false
RUN apt-get remove -y curl

FROM poetry-base as app-base

ARG APPDIR=/app
WORKDIR $APPDIR/
COPY pyproject.toml ./pyproject.toml
RUN poetry install --no-dev
COPY your_project ./your_project

FROM app-base as main

CMD tail -f /dev/null
```

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Build Stage 1: os-base](#build-stage-1-os-base)
- [Build Stage 2: poetry-base](#build-stage-2-poetry-base)
- [Build Stage 3: app-base](#build-stage-3-app-base)
- [Build Stage 4: main](#build-stage-4-main)

## Build Stage 1: os-base

```bash
FROM python:3.11-slim as os-base

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
RUN apt-get update
RUN apt-get install -y curl
```

1. Named stage.
2. PYTHONUNBUFFERED forces the stdout and stderr streams to go straight to terminal.
3. PYTHONDONTWRITEBYTECODE prevents Python from writing .pyc files to disk. This is useful inside a docker container as a marginal performance gain if your process runs only once and needs not be saved to byte code for subsequent invocations.
4. "... used to resynchronise the package index files from their sources", therefore does not hurt to run.
5. We need curl for installing poetry in the next step.

## Build Stage 2: poetry-base

```bash
FROM os-base as poetry-base

RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.poetry/bin:$PATH"
RUN poetry config virtualenvs.create false
RUN apt-get remove -y curl
```

1. Named stage.
2. Installing poetry as per the install instructions.
3. Docker variables declared with ENV can be used across all docker stages. Here we're modifying our PATH environment variable so that we can execute poetry here and in subsequent stages.
4. While we are inside a docker container there is no immediate reason to use a virtual environment.
5. Since we have no use for curl anymore, it doesn't hurt to remove it. In case you're wondering what the "-y" flag does, it's answering "yes" if the uninstaller asks you a question.

## Build Stage 3: app-base

Here's where you'll copy your app specific files and directories. I left it quite open so you can replace it with your own.

```bash
FROM poetry-base as app-base

ARG APPDIR=/app
WORKDIR $APPDIR/
COPY pyproject.toml ./pyproject.toml
RUN poetry install --no-dev
COPY your_project ./your_project
```

1. Named stage.
2. The ARG instruction defines a variable that users can pass at build-time to the builder with the docker build command using the --build-arg <varname>=<value> flag.
3. WORKDIR does what it says on the tin. It's also magically created if it doesn't exist.
4. Notice that we are only copying pyproject.toml and NOT the poetry.lock.
5. Copying project files

## Build Stage 4: main

This is where you launch your app. We're not launching an app in this tutorial but using the space to show you a little trick instead.

```bash
FROM app-base as main

CMD tail -f /dev/null
```

Your container will now remain running. You can either ssh to it to e.g check manually the dependencies have been installed.
