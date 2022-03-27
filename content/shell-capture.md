Title: Capturing shell output in python
Author: Nekrasov Pavel
Date: 2022-03-26 12:00
Category: Blog
Tags: linux, python, shell
Slug: shell-capture
Summary: In this article we will use python subprocess to run shell comand and capture its output.

## Abstract

Sometimes we spend significant time in Python trying to do something which is trivial is *bash*. This is especially useful when we are working with very large files that will take a long time to read in. Why read in an entire file to get the last line, when we could just use `tail -n 1`? Or if we want the line count, why read it in when `wc -l` will get the job done faster?

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Use python subprocess check_output](#use-python-subprocess-check_output)
- [Use python subprocess run](#use-python-subprocess-run)

## Use python subprocess check_output

When we use Python, capturing shell output is easy. You can use the subprocess module to get the output in bytes, then decode and parse it.

```python
import subprocess
fname = 'path/to/file'
last_line = subprocess.check_output("tail -n 1 " + fname, shell = True)
last_line = last_line.decode('UTF-8').strip()
```

## Use python subprocess run

If you're using Python 3.5+, and do not need backwards compatibility, the new run function is recommended by the official documentation for most tasks. It provides a very general, high-level API for the subprocess module. To capture the output of a program, pass the subprocess.PIPE flag to the stdout keyword argument. Then access the stdout attribute of the returned CompletedProcess object:

```python
import subprocess
result = subprocess.run(['ls', '-l'], stdout=subprocess.PIPE)
result.stdout.decode('utf-8')
```
