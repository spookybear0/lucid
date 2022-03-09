from sly.yacc import SlyLogger
from enum import Enum


class exprs(Enum):
    UNKNOWN = 0
    PROGRAM = 1
    VAR_ASSIGN = 2
    ADD = 3
    SUB = 4
    MUL = 5
    DIV = 6
    EXPONENT = 7
    EQUALS = 8
    VAR = 9
    NUM = 10
    STR = 11
    CALL = 12
    PAREN = 13
    GETCHILD = 14
    USING = 15
    LESS = 16
    GREATER = 17


def disable_warnings():
    def warning(*args, **kwargs):
        pass

    SlyLogger.warning = warning
