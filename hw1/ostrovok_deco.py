"""
Функция - это объект Callable
Чтобы функцию можно было вызывать со скобками и без, нужно,
чтобы это был класс, который одинаково себя ведет как класс и как объект
и представлял собой декоратор - т.е. при вызове (__call__)
принимал на вход параметры
"""


class MetaDeco:
    def __new__(cls, *args, **kwargs):
        pass


class MyDecorator(metaclass=MetaDeco):
    """Decorator example mixing class and function definitions."""
    def __init__(self, *args, **kwargs):
        if not args or not callable(args[0]):

        # self.func = func
        self.args, self.kwargs = args, kwargs

    def __call__(self, *args, **kwargs):
        print(f"args: {self.args}, kwargs: {self.kwargs}")
        result = self.func(*args, **kwargs)
        # use self.param2
        return result


