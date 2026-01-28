def greet(name):
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, name):
        self.name = name

    def say_hello(self):
        return f"Hi, {self.name}! Welcome!"
