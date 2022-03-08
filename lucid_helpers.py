from sly.yacc import SlyLogger

def disable_warnings():
    SlyLogger.warning = lambda a, b, c: None