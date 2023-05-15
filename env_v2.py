"""
Module that manages program environments. Currently a mapping from variables to values.
"""

from intbase import ErrorType


class EnvironmentManager:
    """
    The EnvironmentManager class maintains the lexical environment for a construct.
    In project 1, this is just a mapping between each variable (aka symbol)
    in a brewin program and the value of that variable - the value that's passed in can be
    anything you like. In our implementation we pass in a Value object which holds a type
    and a value (e.g., Int, 10).
    """

    def __init__(self, interpreter):
        self.environment = {}
        self.interpreter = interpreter

    def get(self, symbol):
        """
        Get data associated with variable name.
        """
        if symbol in self.environment:
            return self.environment[symbol][0]

        return None

    def get_type(self, symbol):
        """
        Get type associated with variable name.
        """
        if symbol in self.environment:
            return self.environment[symbol][1]

        return None

    def set(self, symbol, value, symbol_type):
        """
        Set data associated with a variable name.
        """
        if symbol in self.environment and symbol_type != self.environment[symbol][1]:
            # RAISE A TYPE ERROR HERE, CAN'T CHANGE THE TYPE OF A VARIABLE PLEASE AND THANK YOU
            self.interpreter.error(
                ErrorType.TYPE_ERROR, f"cannot change the type of {symbol} variable")
        print(f"SETTING {symbol} to {value}")
        self.environment[symbol] = (value, symbol_type)
