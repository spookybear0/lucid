
__name__ = "types"

class Object:
    def __init__(self) -> None:
        pass

class false_t(Object):
    def __bool__(self):
        return False
    
    def __repr__(self):
        return "false"
    
    def __str__(self):
        return "false"

class true_t(Object):
    def __bool__(self):
        return True
    
    def __repr__(self):
        return "true"
    
    def __str__(self):
        return "true"
    
true = true_t()
false = false_t()

class Boolean(Object):
    def __init__(self, value: bool):
        if value:
            self.value = true
        else:
            self.value = false
        
    def __bool__(self):
        return self.value
    
    def __repr__(self):
        return self.value

class Integer(Object, int):
    def __new__(cls, value: int):
        return int.__new__(cls, value)

    def __init__(self, value: int):
        Object.__init__(self)

class String(Object, str):      
    def __new__(cls, content):
        return str.__new__(cls, content)
    
    def __init__(self, content):
        Object.__init__(self)
        
class Callable(Object):
    def __init__(self, func):
        self._func = func
        Object.__init__(self)
        
    def call(self, *args, **kwargs):
        return self._func(*args, **kwargs)
    
types = {
    "true": true,
    "false": false,
    "Boolean": Boolean,
    "Callable": Callable,
    "String": String,
    "Integer": Integer,
    "Object": Object
}

funcs = {
    "print": print,
    "type": type
}

lucid_builtins = {
    **types,
    **funcs
}