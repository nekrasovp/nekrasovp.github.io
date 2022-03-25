Title: Why you need Python Global Interpreter Lock and how it works
Author: Nekrasov Pavel
Date: 2022-03-20 15:00
Category: Blog
Tags: python, gil, threading, multiprocessing
Slug: python-gil
Summary: In this article we will discuss how the GIL impacts application performance and how that impact can be mitigated.

## Abstract

The **Python Global Interpreter Lock (GIL)** is a kind of lock that allows only one thread to control the Python interpreter. This means that only one particular thread will be running at any given time.

The operation of the **GIL** may seem irrelevant to developers creating single-threaded programs. But in multi-threaded programs, the absence of the **GIL** can negatively affect the performance of processor-dependent programs.

Because the **GIL** only allows one thread to run, even in a multi-threaded application, it has earned a reputation as an "infamous" feature.

This article will talk about how the **GIL** affects the performance of applications, and how this very impact can be mitigated.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [What problem does the GIL solve in Python?](#what-problem-does-the-gil-solve-in-python)
- [Why was GIL chosen to solve the problem?](#why-was-gil-chosen-to-solve-the-problem)
- [The impact of the GIL on multithreaded applications](#the-impact-of-the-gil-on-multithreaded-applications)
- [How to deal with GIL?](#how-to-deal-with-gil)

## What problem does the GIL solve in Python?

Python counts the number of references for correct memory management. This means that objects created in Python have a reference count variable that stores the number of all references to that object. As soon as this variable becomes equal to zero, the memory allocated for this object is freed.

Here is a small code example demonstrating how reference counting variables work:

```python
>>> import sys
>>> a = []
>>> b = a
>>> sys.getrefcount(a)
3
```

In this example, the number of references to an empty array is 3. This array is referenced by variable *a*, variable *b*, and the argument passed to *sys.getrefcount()*.

The problem that the **GIL** solves is that in a multi-threaded application, multiple threads can increment or decrement this reference count at the same time. This can lead to the fact that the memory is cleaned up incorrectly and the object to which the reference still exists is deleted.

The reference count can be secured by adding blockers on all data structures that are propagated across multiple threads. In this case, the counter will change exclusively sequentially.

But adding a lock to multiple objects can lead to another problem - deadlocks, which only happen if there is a lock on more than one object. In addition, this problem would also reduce performance due to the repeated installation of blockers.

**GIL** is a single blocker of the Python interpreter itself. It adds the rule that any execution of bytecode in Python requires an interpreter lock. In this case, the deadlock can be avoided because the **GIL** will be the only lock in the application. In addition, its impact on processor performance is not critical at all. However, it is worth remembering that the **GIL** confidently makes any program single-threaded.

Although the **GIL** is used in other interpreters, such as Ruby, it is not the only solution to this problem. Some languages ​​solve the problem of thread-safe memory deallocation using garbage collection.

On the other hand, this means that such languages ​​often have to compensate for the loss of the single-threaded benefits of the **GIL** by adding some additional performance enhancement features, such as JIT compilers.

## Why was GIL chosen to solve the problem?

So why is this solution being used in Python? How critical is this decision for developers?

According to [Larry Hastings](https://www.youtube.com/watch?v=KVKufdTphKs&feature=youtu.be&t=12m11s), the **GIL** architecture is one of the things that made Python popular.

Python has been around since the days when operating systems didn't have the concept of threads. This language was designed to be easy to use and speed up the development process. More and more developers switched to Python.

Many of the extensions that Python needed were written for existing C libraries. To prevent inconsistent changes, the C language required thread-safe memory management, which the **GIL** was able to provide.

The **GIL** could be easily implemented and integrated into Python. It increased the performance of single-threaded applications because only one blocker was in control.

Those C libraries that were not thread-safe became easier to integrate. These C extensions are one of the reasons why the Python community has grown.

As you can see, the **GIL** is the actual solution to the problem that the CPython developers faced early in Python's life.

## The impact of the GIL on multithreaded applications

Looking at a typical program (not necessarily written in Python) it makes a difference whether that program is limited by CPU performance or I/O.

CPU-bound operations are all computational operations: matrix multiplication, search, image processing, etc.

I/O performance-bound operations (I/O-bound) are those operations that are often waiting for something from I/O sources (user, file, database, network). Such programs and operations can sometimes wait a long time until they get what they need from the source. This is because the source may be doing its own (internal) operations before it is ready to produce a result. For example, the user can think about what exactly to enter in the search string or what query to send to the database.

Below is a simple CPU-bound program that simply counts down:

```python
>>> import time
>>>
>>> def countdown(n):
>>>     while n > 0:
>>>         n -= 1
>>>
>>> start = time.time()
>>> countdown(50000000)
>>> end = time.time()
>>> print(f"Average execution time: {end - start} seconds")
Average execution time: 1.7815375328063965 seconds
```

Now the countdown is carried out in two parallel streams:

```python
>>> import time
>>> from threading import Thread
>>> 
>>> def countdown(n):
>>>     while n > 0:
>>>         n -= 1
>>> 
>>> t1 = Thread(target=countdown, args=(50000000//2,))
>>> t2 = Thread(target=countdown, args=(50000000//2,))
>>> 
>>> start = time.time()
>>> t1.start()
>>> t2.start()
>>> t1.join()
>>> t2.join()
>>> end = time.time()
>>> 
>>> print(f"Average execution time: {end - start} seconds")
Average execution time: 3.138119697570801 seconds
```

In the multithreaded version, the **GIL** prevented threads from running in parallel.

The **GIL** does not greatly affect the performance of I/O operations in multi-threaded programs, since the lock is propagated through the threads while waiting for I/O.

However, a program whose threads will work exclusively with the processor will not only become single-threaded due to blocking, but it will also take more time to execute it than if it were originally strictly single-threaded.

This increase in time is the result of the appearance and implementation of blocking.

## How to deal with GIL?

If the **GIL** is causing you problems, here are some solutions you can try:

Multiprocessing versus multithreading. A fairly popular solution, since each Python process has its own interpreter with memory allocated for it, so there will be no problems with the **GIL**. Python already has a multiprocessing module that makes it easy to create processes like this:

```python
>>> import time
>>> from multiprocessing import Pool
>>> 
>>> def countdown(n):
>>>     while n > 0:
>>>         n -= 1
>>> 
>>> pool = Pool(processes=2)
>>> start = time.time()
>>> r1 = pool.apply_async(countdown, [50000000//2])
>>> r2 = pool.apply_async(countdown, [50000000//2])
>>> pool.close()
>>> pool.join()
>>> end = time.time()
>>> 
>>> print(f"Average execution time: {end - start} seconds")
Average execution time: 1.0929028987884521 seconds
```

You can notice a decent performance improvement compared to the multi-threaded version. However, the time indicator did not drop to half. This is due to the fact that process management itself affects performance. Multiple processes are more complex than multiple threads, so they need to be handled with care.

Often, the **GIL** is seen as something complicated and incomprehensible. But keep in mind that as a python developer, you will only encounter the **GIL** if you write C extensions or multi-threaded CPU programs.

At this point, you should understand all the aspects required when working with the **GIL**. If you are interested in the low-level structure of the **GIL**, check out [Understanding the Python GIL](https://youtu.be/Obt-vMVdM8s) by David Beazley.
