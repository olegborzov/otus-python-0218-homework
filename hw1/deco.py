#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(func):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    memo = disable
    '''
    return func


def decorator(deco):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''

    def wrapper(func):
        return update_wrapper(deco(func), func)

    return wrapper


@decorator
def countcalls(func):
    '''Decorator that counts calls made to the function decorated'''
    def wrapper(*args, **kwargs):
        wrapper.calls = getattr(wrapper, "calls", 0) + 1
        return func(*args, **kwargs)
    wrapper.calls = 0
    return wrapper


@decorator
def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    def wrapper(*args, **kwargs):
        update_wrapper(wrapper, func)
        key = str(args) + str(kwargs)
        if key not in wrapper.cache:
            wrapper.cache[key] = func(*args, **kwargs)

        return wrapper.cache[key]

    wrapper.cache = {}
    return wrapper


@decorator
def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''
    def wrapper(*args):
        return args[0] if len(args) == 1 else func(args[0], wrapper(*args[1:]))
    return wrapper


def trace(indent="___"):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''
    @decorator
    def decorate(func):
        def wrapper(*args, **kwargs):
            print("{indent} {arrow} {func_name}({func_params})".format(
                indent=indent * wrapper.level,
                arrow="-->",
                func_name=func.__name__,
                func_params=", ".join([str(arg) for arg in args])
            ))

            wrapper.level += 1
            result = func(*args, **kwargs)
            wrapper.level -= 1

            print("{indent} {arrow} {func_name}({func_params}) == {res}".format(
                indent=indent * wrapper.level,
                arrow="<--",
                func_name=func.__name__,
                func_params=", ".join([str(arg) for arg in args]),
                res=result
            ))
            return result

        wrapper.level = 0
        return wrapper
    return decorate


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")

    print(fib.__doc__)
    fib(3)
    print(fib.calls, 'calls made')


if __name__ == '__main__':
    main()
