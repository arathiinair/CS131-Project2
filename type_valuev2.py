"""
Module that contains the Value definition and associated type constructs.
"""

from enum import Enum
from intbase import InterpreterBase


class Type(Enum):
    """Enum for all possible Brewin types."""

    INT = 1
    BOOL = 2
    STRING = 3
    CLASS = 4
    NOTHING = 5


# Represents a value, which has a type and its value
class Value:
    """A representation for a value that contains a type tag."""

    def __init__(self, value_type, value=None):
        self.__type = value_type
        self.__value = value
        self.__class_name = None
        if self.__type == Type.CLASS and self.__value is not None:
            self.__class_name = self.__value.class_def.name

    def type(self):
        return self.__type

    def value(self):
        return self.__value
    
    def class_name(self):
        return self.__class_name

    def set(self, other):
        self.__type = other.type()
        self.__value = other.value()


# pylint: disable=too-many-return-statements
def create_value(val):
    """
    Create a Value object from a Python value.
    """
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True)
    if val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False)
    if val[0] == '"':
        return Value(Type.STRING, val.strip('"'))
    if val.lstrip('-').isnumeric():
        return Value(Type.INT, int(val))
    if val == InterpreterBase.NULL_DEF:
        return Value(Type.CLASS, None)
    if val == InterpreterBase.NOTHING_DEF:
        return Value(Type.NOTHING, None)
    return None


def check_type(value_type, variable_type):
    if value_type == Type.BOOL and variable_type == InterpreterBase.BOOL_DEF:
        return True
    elif value_type == Type.STRING and variable_type == InterpreterBase.STRING_DEF:
        return True
    elif value_type == Type.INT and variable_type == InterpreterBase.INT_DEF:
        return True
    else:
        return False
    # ADD CLASS TYPE CHECKING
