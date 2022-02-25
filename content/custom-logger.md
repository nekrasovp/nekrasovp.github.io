Title: Custom logger handlers
Author: Nekrasov Pavel
Date: 2022-02-25 18:45
Category: Blog
Tags: python, logging
Slug: custom-logger
Summary: The Python logging module may be used to build your own custom logger featuring special functionality according to your use case.

## Contents

- [Contents](#contents)
- [Logging](#logging)
- [Custom logger with stdout and file handlers](#custom-logger-with-stdout-and-file-handlers)
- [Check whether the logger has a stream handler and/or a file handler](#check-whether-the-logger-has-a-stream-handler-andor-a-file-handler)
- [Disable logger console output](#disable-logger-console-output)
- [Disable logger file output](#disable-logger-file-output)
- [Verbosity setting for the custom logger](#verbosity-setting-for-the-custom-logger)
- [Custom logging level that overrides the verbosity setting](#custom-logging-level-that-overrides-the-verbosity-setting)
- [Putting the custom logger to use](#putting-the-custom-logger-to-use)
  - [Quiet mode](#quiet-mode)
  - [Verbose mode](#verbose-mode)

## Logging

The Python [logging](https://docs.python.org/3/library/logging.html) module may be used to build your own custom logger featuring special functionality according to your use case, such as:

- Adding both console and file handlers (i.e. logging to both stdout and to a file)
- Temporarily disabling console logging (e.g. if a global verbose flag is False)
- Temporarily disabling file logging (e.g. if we want to print with color to stdout using ANSI codes, but without color to the log file)
- Adding an extra logging level that logs to both console and log file (e.g. even if a global verbose flag is False)

This srticle will show how to build such a custom logger for the above use cases, that we will be going through incrementally.

## Custom logger with stdout and file handlers

We will be creating a *CustomLogger* class based on *logging.getLoggerClass()* (the logger used in Python’s *logging* module) with a default stdout handler. If the user of the class specifies a log directory, then a file handler will also be added. The format of the logs is also different:

- we use the bare message to log for the stdout handler
- we show the date, time, logging level, file and line number for the file handler

```python
class CustomLogger(logging.getLoggerClass()):
    def __init__(self, name, log_dir=None):
        # Create custom logger logging all five levels
        super().__init__(name)
        self.setLevel(logging.DEBUG)

        # Create stream handler for logging to stdout (log all five levels)
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.stdout_handler.setLevel(logging.DEBUG)
        self.stdout_handler.setFormatter(logging.Formatter('%(message)s'))
        self.enable_console_output()

        # Add file handler only if the log directory was specified
        self.file_handler = None
        if log_dir:
            self.add_file_handler(name, log_dir)

    def add_file_handler(self, name, log_dir):
        """Add a file handler for this logger with the specified `name` (and
        store the log file under `log_dir`)."""
        # Format for file log
        fmt = '%(asctime)s | %(levelname)8s | %(filename)s:%(lineno)d | %(message)s'
        formatter = logging.Formatter(fmt)

        # Determine log path/file name; create log_dir if necessary
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_name = f'{str(name).replace(" ", "_")}_{now}'
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except:
                print('{}: Cannot create directory {}. '.format(
                    self.__class__.__name__, log_dir),
                    end='', file=sys.stderr)
                log_dir = '/tmp' if sys.platform.startswith('linux') else '.'
                print(f'Defaulting to {log_dir}.', file=sys.stderr)

        log_file = os.path.join(log_dir, log_name) + '.log'

        # Create file handler for logging to a file (log all five levels)
        self.file_handler = logging.FileHandler(log_file)
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(formatter)
        self.addHandler(self.file_handler)
```

Notice that we store both the stdout handler and the file handler as members of the *CustomLogger*, through the instance variables *self.stdout_handler* and *self.file_handler*. This is to facilitate the forthcoming tasks, namely to check whether the logger has such handlers and to be able to enable and disable them individually.

## Check whether the logger has a stream handler and/or a file handler

The Python logging documentation explains that *logging.StreamHandler* is the base class for *logging.FileHandler*. We  add methods to our *CustomLogger* class to find out whether the logger instance has a console logger and/or a file logger:

```python
def has_console_handler(self):
    return len([h for h in self.handlers if type(h) == logging.StreamHandler]) > 0

def has_file_handler(self):
    return len([h for h in self.handlers if isinstance(h, logging.FileHandler)]) > 0
```

## Disable logger console output

Using the *has_console_handler()* check to ensure internal API consistency, we can now write methods for our *CustomLogger* class to temporarily enable/disable console output. Since the logger retains the instance variable *self.stdout_handler*, we can add it and remove it as we please:

```python
def disable_console_output(self):
    if not self.has_console_handler():
        return
    self.removeHandler(self.stdout_handler)

def enable_console_output(self):
    if self.has_console_handler():
        return
    self.addHandler(self.stdout_handler)
```

## Disable logger file output

Similarly to what we’ve seen above, via the *has_file_handler()* check in order to ensure internal API consistency, we can now write methods for our *CustomLogger* class to temporarily enable/disable file output. Since the logger retains the instance variable *self.file_handler*, we can add it and remove it as we please:

```python
def disable_file_output(self):
    if not self.has_file_handler():
        return
    self.removeHandler(self.file_handler)

def enable_file_output(self):
    if self.has_file_handler():
        return
    self.addHandler(self.file_handler)
```

## Verbosity setting for the custom logger

In certain situations, you way need to create a more quiet or a more verbose logger. If the logger needs to be quiet, you may want to skip logging altogether. This means we need to override the *info()*, *debug()*, *warning()*, *error()* and *critical()* methods of the base class and make them behave differently according to the verbosity setting. (Your use case might be different and you may want to keep logging enabled for **ERROR** and **CRITICAL** levels for example.)

First, we introduce a verbose boolean flag to the *__init__()* method of our *CustomLogger* class and store its value in the logger instance. Then, we override the logging methods:

```python 
class CustomLogger(logging.getLoggerClass()):
    def __init__(self, name, verbose, log_dir=None):
        ...
        self.verbose = verbose

    def debug(self, msg, *args, **kwargs):
        self._custom_log(super().debug, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._custom_log(super().info, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._custom_log(super().warning, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._custom_log(super().error, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._custom_log(super().critical, msg, *args, **kwargs)

    def _custom_log(self, func, msg, *args, **kwargs):
        """Helper method for logging DEBUG through CRITICAL messages by
        calling the appropriate `func()` from the base class."""
        # Log normally if verbosity is on
        if self.verbose:
            return func(msg, *args, **kwargs)

        # If verbosity is off and there is no file handler, there is
        # nothing left to do
        if not self.has_file_handler():
            return

        # If verbosity is off and a file handler is present, then disable
        # stdout logging, log, and finally reenable stdout logging
        self.disable_console_output()
        func(msg, *args, **kwargs)
        self.enable_console_output()
```

## Custom logging level that overrides the verbosity setting

Well all this is fine, but what if you do want to display certain messages after all, even if verbosity is off? Think of them as “system” or “framework” messages that should not be silenced.

The solution to this is to add a new logging level to the *CustomLogger* class. Let’s call it **FRAMEWORK** and have it log at **INFO** priority (for the purpose of illustration). We just need to add the level and to write the corresponding *framework()* method:

```python 
class CustomLogger(logging.getLoggerClass()):
    def __init__(self, name, verbose, log_dir=None):
        ...
        logging.addLevelName(logging.INFO, 'FRAMEWORK')

    def framework(self, msg, *args, **kwargs):
        """Logging method for the FRAMEWORK level. The `msg` gets
        logged both to stdout and to file (if a file handler is
        present), irrespective of verbosity settings."""
        return super().info(msg, *args, **kwargs)
```

For neat display in the file logs, we should also think of changing the formatter to accommodate 9 characters instead of 8:

```python
fmt = '%(asctime)s | %(levelname)9s | %(filename)s:%(lineno)d | %(message)s'
```

## Putting the custom logger to use

We can now test the logger in both quiet and verbose mode.

### Quiet mode

In quiet mode this is really straightforward:

```python
quiet_log = CustomLogger('quiet', verbose=False, log_dir='logs')
quiet_log.warning('We now log only to a file log')
quiet_log.framework('We now log everywhere irrespective of verbosity')
```

### Verbose mode

```python
verbose_log = CustomLogger('verbose', verbose=True, log_dir='logs')
verbose_log.warning('We now log to both stdout and a file log')
verbose_log.disable_file_output()
verbose_log.info(msg + ', but not here')
verbose_log.enable_file_output()
verbose_log.framework('We now log everywhere irrespective of verbosity')

```