import functools
import time

def timer(function):
    """
    Decorator that measures function execution time
    """
    @functools.wraps(function)
    def wrapper(*args,**kwargs):

        start = time.perf_counter()

        try:
            return function(*args,**kwargs)
        finally:
            elapsed = time.perf_counter() - start
            print(f"'{function.__name__}()' Executed in: [{elapsed:.6f} seconds]")
    return wrapper

def counter(function):
    """
    Decorator that counts the amount of times a given function runs.
    :param function:
    :return:
    """
    print(f"Calling {function.__name__} function")

    # apparently this is necessary.
    @functools.wraps(function)
    def wrapper(*args,**kwargs):
        wrapper.calls += 1
        print(f"Function call count: {wrapper.calls}")
        return function(*args,**kwargs)

    wrapper.calls = 0
    return wrapper

def argument_dump(function):
    """
    Decorator that prints all positional and keyword arguments passed to a function.
    :param function:
    :return:
    """
    @functools.wraps(function)
    def wrapper(*args,**kwargs):
        print(f"[{function.__name__} function dump] args: {args} | kwargs: {kwargs}")
        return function(*args,**kwargs)
    return wrapper

def verbose_mode(function):
    """
    Decorator that prints the state of a given method.
    :param function:
    :return:
    """

    timed_funct = timer(function)
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        print("========== VERBOSE ==========")

        print(f"Function '{timed_funct.__name__}()' initiated.")

        result = timed_funct(*args, **kwargs)

        print(f"'{timed_funct.__name__}()' returned: {result}")
        print("=============================")

        return result
    return wrapper