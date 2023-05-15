"""
The module that brings it all together! We intentionally keep this as small as possible,
delegating functionality to various modules.
"""

from classv2 import ClassDef
from intbase import InterpreterBase, ErrorType
from bparser import BParser
from objectv2 import ObjectDef


class Interpreter(InterpreterBase):
    """
    Main interpreter class that subclasses InterpreterBase.
    """

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.main_object = None
        self.class_index = {}

    def run(self, program):
        """
        Run a program (an array of strings, where each item is a line of source code).
        Delegates parsing to the provided BParser class in bparser.py.
        """
        status, parsed_program = BParser.parse(program)
        if not status:
            super().error(
                ErrorType.SYNTAX_ERROR, f"Parse error on program: {parsed_program}"
            )
        print(parsed_program)
        self.__map_class_names_to_class_defs(parsed_program)

        # instantiate main class
        invalid_line_num_of_caller = None
        self.main_object = self.instantiate(
            InterpreterBase.MAIN_CLASS_DEF, invalid_line_num_of_caller
        )

        # call main function in main class; return value is ignored from main
        self.main_object.call_method(
            InterpreterBase.MAIN_FUNC_DEF, [], invalid_line_num_of_caller
        )

        # program terminates!

    def instantiate(self, class_name, line_num_of_statement):
        """
        Instantiate a new class. The line number is necessary to properly generate an error
        if a `new` is called with a class name that does not exist.
        This reports the error where `new` is called.
        """
        if class_name not in self.class_index:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No class named {class_name} found",
                line_num_of_statement,
            )
        class_def = self.class_index[class_name]
        # print(f"CLASS NAME {class_def.name}")
        obj = ObjectDef(
            self, class_def, self.trace_output
        )  # Create an object based on this class definition
        return obj

    def __map_class_names_to_class_defs(self, program):
        self.class_index = {}
        for item in program:
            if item[0] == InterpreterBase.CLASS_DEF:
                if item[1] in self.class_index:
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Duplicate class name {item[1]}",
                        item[0].line_num,
                    )
                # no inheritance
                if isinstance(item[2], list) and item[2] != InterpreterBase.INHERITS_DEF:
                    self.class_index[item[1]] = ClassDef(item, self, None)
                    # print(f"NO INHERITANCE {item[1]}")
                elif item[2] == InterpreterBase.INHERITS_DEF:
                    # print(f"STUDENT {item[3]}")
                    if item[3] not in self.class_index:
                        # inheriting from a class that doesn't exist
                        super().error(
                            ErrorType.NAME_ERROR,
                            f"Base class {item[3]} does not exist",
                            item[0].line_num,
                        )
                    else:
                        parent = self.class_index[item[3]]
                        # print(f"INHERITING PARENT CLASS {item[3]}")
                        self.class_index[item[1]] = ClassDef(
                            item, self, parent)
