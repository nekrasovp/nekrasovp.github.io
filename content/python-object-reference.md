Title: Python object reference
Author: Nekrasov Pavel
Date: 2022-07-20 12:00
Category: Blog
Tags: python
Slug: python-object-reference
Summary: This post is about how python treats object assignment and some of the hidden gotcha’s that can cause unintended errors along the way.

## Abstract

This post is about how python treats object assignment and some of the hidden gotcha’s that can cause unintended errors along the way. Instead of “boxes” it is better to think of variables as “labels” that we attach to objects. And, as everything in python is an object its important to remember that all objects have three things; identity, type and values. Values are the only things that change once an object is created, and it values that we often care about, and hence label.

## Contents

- [Abstract](#abstract)
- [Contents](#contents)
- [Labels](#labels)
- [Equality and Identity](#equality-and-identity)
- [Alias Issues](#alias-issues)
- [Copies](#copies)
- [Summary](#summary)

## Labels

Lets look at the assignment of variables.

```python
a = 2 # we label the integer 2 as 'a'
b = a # 'a' is now labelled as 'b'
c = b # and 'b' is now labelled as 'c'
```

Above we can see that the object **2** is assigned to the variable **a**. Each subsequent assignment thereafter is simply a reference to the same object. When viewed through this lense you can start to see how objects have labels. It is not feasible that the **2** can exist in three different boxes rather we visualise **2** having three sticky notes attached to it. If we changed **a** like this `a = 20` then it is just a matter of peeling off the sticky note with a written on it from **2** and attaching it to **20**. To further aid in this thinking, always read assignments from right to left. The right side is where the object is created or retrieved and the left is what we bind to it.

When an object like **2** has many labels we called this **aliasing**. **Aliasing** is an important concept to grasp, and to illustrate why we will examine the identity of **a**, **b**, and **c**.

```python
print(f'{id(2)=}') # id(a)=11171976
print(f'{id(a)=}') # id(a)=11171976
print(f'{id(b)=}') # id(b)=11171976
print(f'{id(c)=}') # id(c)=11171976
```

All aliases of a have the same identity which in python is unique integer representing its C memory address. If any change were to be made the identity integer would also change to reflect that.

## Equality and Identity

Let’s check out Equality and Identity (and aliases, too)

An object’s identity never changes once it has been created. However its values might, and generally this is what we care about more. Python gives us the option to check either like so:

```python
assert a == b # compares the values
assert a is b # compares the identities
```

Lets extend this using a more complex example using some dictionaries.

```python
orig_dict = {'name': 'original', 'type': 'dict'}
my_dict = orig_dict
assert orig_dict == my_dict
assert orig_dict is my_dict
```

Both orig_dict and my_dict are equal in identity, and their values.
Lets create the same dict with other name.

```python
new_dict = {'name': 'original', 'type': 'dict'}
assert orig_dict == new_dict
assert orig_dict is not new_dict
```

In this case, both new_dict and orig_dict share equal values but not the same identity. new_dict is not an alias of my_dict or orig_dict, and thus has his own unique identity. This is because we created an entirely new identity albeit with the same values as orig_dict.

Much of the time we care mostly about the values an object holds not its identity but you will see is in a lot during conditionals such as:

```python
if x is None:
    ...
if x is not None:
    ...
```

## Alias Issues

Something I didn’t realise until it came back to haunt me much later is that aliases can have unintended side effects with mutable types. Let’s say we have two lists, the original and its alias. The alias will have items added to it but we want the original untouched for whatever reason.

```python
orig_list = [1, 'a', True, [1, 2]]
my_list = orig_list
```

Looks good, we can now make changes to my_list.

```python
my_list.append('smth')
print(orig) # [1, 'a', True, [1, 2], 'smth']
print(new)  # [1, 'a', True, [1, 2], 'smth']
```

After appending to my_list it becomes apparent that this change has affected both lists. This happens because the alias works two way with mutable types. I think this is really important to know - aliases are not copies!

## Copies

If aliases aren’t copies then how do we copy?

```python
print(f'{id(orig_list)=}') # id(orig_list)=140152571215488
print(f'{id(my_list)=}')   # id(my_list)=140152571215488
```

By using the list() class we successfully create two new objects. Now if we append or remove items from either list it does not propagate through. Except, it does sometimes.

In this case we are only making a new copy of the overall object but not any mutable nested types within the copy. So while any changes made within the first layer of the object are contained within the copy, any mutable objects nested more deeply will be aliases.

Confused, an example.

```python
orig_list = [1, 'a', True, [1, 2]]
new_list = list(orig_list)  # or with slices new_list = orig_list[::]
new_list.append('smth')
print(orig_list) # [1, 'a', True, [1, 2]]
print(new_list)  # [1, 'a', True, [1, 2], 'smth']
# first layer is not affected as it is a copy, not an alias
orig_list[-1].append('smth_new')
print(orig_list) # [1, 'a', True, [1, 2, 'smth_new']]
print(new_list)  # [1, 'a', True, [1, 2, 'smth_new'], 'smth']
```

While the orig_list and new_list are independent of each other when making changes to the first layer of abstraction, any mutable types within that are simply aliases of the copies source.

Another example to check this out.

```python
# before we started making alterations to the lists
print(id(orig_list))     # 139683504118592
print(id(new_list))      # 139683504118592
print(id(orig_list[-1])) # 139683504118592
print(id(new_list[-1]))  # 139683504118592
```

Inspecting the identities reveals that only the overall object's were initialised as new objects but the nested types within were bound to the original nested type - an alias!

This is something to take into consideration when passing variables around that have nested types. To circumvent this immutable types such as tuples can be used in place.

Python can do deep copies which will take care of this issue, but it has its own drawbacks. Of which we not be discussed here as this post is already quite long.

## Summary

In python all objects have a type, identity and values. Only the values can change after it is created and knowing a little bit more about how this works can help us prevent unintended bugs.

Notes:

- assignment does not create copies
- nested mutable types within shallow copies are aliases
- equality has two different checks; identity, and values
