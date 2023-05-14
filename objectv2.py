"""
Module handling the operations of an object. This contains the meat
of the code to execute various instructions.
"""

from env_v2 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev2 import create_value, check_type
from type_valuev2 import Type, Value


class ObjectDef:
    STATUS_PROCEED = 0
    STATUS_RETURN = 1
    STATUS_NAME_ERROR = 2
    STATUS_TYPE_ERROR = 3

    def __init__(self, interpreter, class_def, trace_output):
        # objref to interpreter object. used to report errors, get input, produce output
        self.interpreter = interpreter
        # take class body from 3rd+ list elements, e.g., ["class",classname", [classbody]]
        self.class_def = class_def
        print(f"MY CLASS DEFINITION {self.class_def.name}")
        if self.class_def.parent:
            self.parent = ObjectDef(
                self.interpreter, self.interpreter.class_index[self.class_def.parent.name], self.interpreter.trace_output)
            print(
                f"HI IM A {self.class_def.name} AND THIS IS MY PARENT {self.parent.class_def.name}")
        else:
            self.parent = None
        self.trace_output = trace_output
        self.__map_fields_to_values()
        self.__map_method_names_to_method_definitions()
        # sets up maps to facilitate binary and unary operations, e.g., (+ 5 6)
        self.__create_map_of_operations_to_lambdas()

    def call_method(self, method_name, actual_params, line_num_of_caller):
        """
        actual_params is a list of Value objects (all parameters are passed by value).

        The caller passes in the line number so we can properly generate an error message.
        The error is then generated at the source (i.e., where the call is initiated).
        """
        # print("METHOD NAMES")
        # for method in self.methods.keys():
        #     print(method)

        method_info = None
        if method_name in self.methods:
            method_def = self.methods[method_name]
            if self.__check_method_def(method_def, actual_params):
                method_info = method_def
        elif self.parent:
            print(
                f"CHECKING PARENT OF {self.class_def.name} ({self.parent.class_def.name}) FOR {method_name}")
            return self.parent.call_method(method_name, actual_params, line_num_of_caller)
        if not method_info:  # throw this error when you've gone through all the parents and the method has not been found
            self.interpreter.error(
                ErrorType.NAME_ERROR,
                "unknown method " + method_name,
                line_num_of_caller,
            )
        env = []
        args = (
            EnvironmentManager(self.interpreter)
        )  # maintains lexical environment for function; just params for now
        for (formal_var, formal_type), actual in zip(list(method_info.formal_params.items()), actual_params):
            # don't think i need to type check bc we've already done it in check method def function
            if actual.value() is None and actual.class_name() is None:
                actual = Value(Type.CLASS, actual.value(), formal_type)
            print(f"SETTING {formal_var} to {actual.value()}")
            args.set(formal_var, actual, formal_type)
        env.append(args)
        return_type = method_info.return_type
        # since each method has a single top-level statement, execute it.
        status, return_value = self.__execute_statement(
            env, method_info.code, return_type)
        # if the method explicitly used the (return expression) statement to return a value, then return that
        # value back to the caller
        if status == ObjectDef.STATUS_RETURN:
            return return_value
        # The method didn't explicitly return a value, so return the default value of the function's return type
        ret_val = self.__get_default_return(return_type)
        print("RETURNING THIS VALUE OBJECT",
              ret_val.value())
        return ret_val

    def __execute_statement(self, env, code, return_type):
        """
        returns (status_code, return_value) where:
        - status_code indicates if the next statement includes a return
            - if so, the current method should terminate
            - otherwise, the next statement in the method should run normally
        - return_value is a Value containing the returned value from the function
        """
        if self.trace_output:
            print(f"{code[0].line_num}: {code}")
        tok = code[0]
        if tok == InterpreterBase.BEGIN_DEF:
            return self.__execute_begin(env, code, return_type)
        if tok == InterpreterBase.SET_DEF:
            return self.__execute_set(env, code)
        if tok == InterpreterBase.IF_DEF:
            return self.__execute_if(env, code, return_type)
        if tok == InterpreterBase.CALL_DEF:
            return self.__execute_call(env, code)
        if tok == InterpreterBase.WHILE_DEF:
            return self.__execute_while(env, code, return_type)
        if tok == InterpreterBase.RETURN_DEF:
            return self.__execute_return(env, code, return_type)
        if tok == InterpreterBase.INPUT_STRING_DEF:
            return self.__execute_input(env, code, True)
        if tok == InterpreterBase.INPUT_INT_DEF:
            return self.__execute_input(env, code, False)
        if tok == InterpreterBase.PRINT_DEF:
            return self.__execute_print(env, code)
        if tok == InterpreterBase.LET_DEF:
            return self.__execute_let(env, code, return_type)

        self.interpreter.error(
            ErrorType.SYNTAX_ERROR, "unknown statement " + tok, tok.line_num
        )

    def __execute_let(self, env, code, return_type):
        block = EnvironmentManager(self.interpreter)
        # var: [type name value]
        for var in code[1]:
            var_type = var[0]
            var_name = var[1]
            var_val = create_value(var[2], var_type)
            if var_val.type() == Type.CLASS:
                if self.__polymorphic(var_type, var_val.class_name()):
                    block.set(var_name, var_val, var_type)
                else:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR, f"setting variable {var_name} to wrong type", code[0].line_num)
            elif check_type(var_val.type(), var_type):
                block.set(var_name, var_val, var_type)
            else:
                self.interpreter.error(
                    ErrorType.TYPE_ERROR, f"setting variable {var_name} to wrong type", code[0].line_num)
        env.append(block)
        status, return_value = self.__execute_begin(env, code[1:], return_type)
        env.pop()
        return status, return_value

    # (begin (statement1) (statement2) ... (statementn))
    def __execute_begin(self, env, code, return_type):
        for statement in code[1:]:
            status, return_value = self.__execute_statement(
                env, statement, return_type)
            if status == ObjectDef.STATUS_RETURN:
                return (
                    status,
                    return_value,
                )  # could be a valid return of a value or an error
        # if we run thru the entire block without a return, then just return proceed
        # we don't want the calling block to exit with a return
        return ObjectDef.STATUS_PROCEED, None

    # (call object_ref/me methodname param1 param2 param3)
    # where params are expressions, and expresion could be a value, or a (+ ...)
    # statement version of a method call; there's also an expression version of a method call below
    def __execute_call(self, env, code):
        return ObjectDef.STATUS_PROCEED, self.__execute_call_aux(
            env, code, code[0].line_num
        )

    # (set varname expression), where expresion could be a value, or a (+ ...)
    def __execute_set(self, env, code):
        val = self.__evaluate_expression(env, code[2], code[0].line_num)
        self.__set_variable_aux(env, code[1], val, code[0].line_num)
        return ObjectDef.STATUS_PROCEED, None

    # (return expression) where expresion could be a value, or a (+ ...)
    def __execute_return(self, env, code, return_type):
        if len(code) == 1 and return_type == InterpreterBase.VOID_DEF:
            # [return] with no return expression
            return ObjectDef.STATUS_RETURN, create_value(InterpreterBase.NOTHING_DEF)
        elif len(code) == 1:    # if we return but function's return type isn't void
            return ObjectDef.STATUS_RETURN, self.__get_default_return(return_type)
        else:
            ret_val = self.__evaluate_expression(
                env, code[1], code[0].line_num)
            if ret_val.type() == Type.CLASS and return_type in self.interpreter.class_index:
                if ret_val.value() is None and ret_val.class_name() is None:    # return null literal
                    ret_val = Value(Type.CLASS, None, return_type)
                if self.__polymorphic(return_type, ret_val.class_name()):
                    return ObjectDef.STATUS_RETURN, ret_val
            elif check_type(ret_val.type(), return_type):
                return ObjectDef.STATUS_RETURN, ret_val

        self.interpreter.error(ErrorType.TYPE_ERROR,
                               "Function returns wrong type", code[0].line_num)

    # (print expression1 expression2 ...) where expresion could be a variable, value, or a (+ ...)
    def __execute_print(self, env, code):
        print(f"HELLO PRINT {code[1]}")
        output = ""
        for expr in code[1:]:
            # TESTING NOTE: Will not test printing of object references
            term = self.__evaluate_expression(env, expr, code[0].line_num)
            val = term.value()
            typ = term.type()
            print(f"PRINTING {expr} {val} {typ}")
            if typ == Type.BOOL:
                val = "true" if val else "false"
            # document - will never print out an object ref
            output += str(val)
        self.interpreter.output(output)
        return ObjectDef.STATUS_PROCEED, None

    # (inputs target_variable) or (inputi target_variable) sets target_variable to input string/int
    def __execute_input(self, env, code, get_string):
        inp = self.interpreter.get_input()
        if get_string:
            val = Value(Type.STRING, inp)
        else:
            val = Value(Type.INT, int(inp))

        self.__set_variable_aux(env, code[1], val, code[0].line_num)
        return ObjectDef.STATUS_PROCEED, None

    # helper method used to set either parameter variables or member fields; parameters currently shadow
    # member fields
    def __set_variable_aux(self, env, var_name, value, line_num):
        print(f"SETTING VARIABLE AUX WITH {value.type()}")
        # parameter shadows fields
        if value.type() == Type.NOTHING:
            self.interpreter.error(
                ErrorType.TYPE_ERROR, "can't assign to nothing " + var_name, line_num
            )
        param_val = None
        if len(env) == 1:
            param_val = env[0].get(var_name)
            if param_val:
                var_type = env[0].get_type(var_name)
                current = 0
        else:
            for i in range(len(env)-1, 0, -1):
                param_val = env[i].get(var_name)
                if param_val:
                    var_type = env[i].get_type(var_name)
                    current = i
                    break
        if param_val is not None:   # the variable is a parameter to the function
            print(f"FOUND PARAM {var_name} {value.value()}")
            if value.type() == Type.CLASS:
                print(
                    f"-1. TRYING TO ASSIGN {var_type} {var_name} TO {value.type()} {value.value()}")
                if value.value() is None and value.class_name() is None:  # setting variable to null literal
                    value = Value(Type.CLASS, value.value(), var_type)
                # CHANGE THIS TO DEAL WITH POLYMORPHISM
                if self.__polymorphic(var_type, value):
                    env[current].set(var_name, value, var_type)
                else:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR, f"assigning {var_name} to a class variable of the wrong type", line_num
                    )
            elif check_type(value.type(), var_type):
                env[current].set(var_name, value, var_type)
            else:
                print(
                    f"-3. TRYING TO ASSIGN {var_type} {var_name} TO {value.type()} {value.value()}")
                self.interpreter.error(
                    ErrorType.TYPE_ERROR, f"assigning {var_name} to a value of the wrong type", line_num
                )
            return

        if var_name not in self.fields:
            self.interpreter.error(
                ErrorType.NAME_ERROR, "unknown variable " + var_name, line_num
            )
        print(f"SETTING FIELD TO NEW VALUE {var_name} {value.value()}")
        field_type = self.fields[var_name][1]
        if value.type() == Type.CLASS:
            print(
                f"1. TRYING TO ASSIGN {field_type} {var_name} TO {value.type()} {value.value()}")
            # CHANGE THIS TO DEAL WITH POLYMORPHISM
            print(f"HELLO YOOHOO CLASSNAME {value.class_name()}")
            if value.value() is None and value.class_name() is None:  # setting variable to null literal
                value = Value(Type.CLASS, value.value(), field_type)
            if self.__polymorphic(field_type, value.class_name()):
                self.fields[var_name] = (value, field_type)
            else:
                self.interpreter.error(
                    ErrorType.TYPE_ERROR, f"assigning {var_name} to a class variable of the wrong type", line_num
                )
        elif check_type(value.type(), field_type):
            self.fields[var_name] = (value, field_type)
        else:
            print(
                f"3. TRYING TO ASSIGN {field_type} {var_name} TO {value.type()} {value.value()}")
            self.interpreter.error(
                ErrorType.TYPE_ERROR, f"assigning {var_name} to a value of the wrong type", line_num
            )

    # (if expression (statement) (statement) ) where expresion could be a boolean constant (e.g., true), member
    # variable without ()s, or a boolean expression in parens, like (> 5 a)
    def __execute_if(self, env, code, return_type):
        condition = self.__evaluate_expression(env, code[1], code[0].line_num)
        if condition.type() != Type.BOOL:
            self.interpreter.error(
                ErrorType.TYPE_ERROR,
                "non-boolean if condition " + ' '.join(x for x in code[1]),
                code[0].line_num,
            )
        if condition.value():
            status, return_value = self.__execute_statement(
                env, code[2], return_type
            )  # if condition was true
            return status, return_value
        if len(code) == 4:
            status, return_value = self.__execute_statement(
                env, code[3], return_type
            )  # if condition was false, do else
            return status, return_value
        return ObjectDef.STATUS_PROCEED, None

    # (while expression (statement) ) where expresion could be a boolean value, boolean member variable,
    # or a boolean expression in parens, like (> 5 a)
    def __execute_while(self, env, code, return_type):
        while True:
            condition = self.__evaluate_expression(
                env, code[1], code[0].line_num)
            if condition.type() != Type.BOOL:
                self.interpreter.error(
                    ErrorType.TYPE_ERROR,
                    "non-boolean while condition " +
                    ' '.join(x for x in code[1]),
                    code[0].line_num,
                )
            if not condition.value():  # condition is false, exit loop immediately
                return ObjectDef.STATUS_PROCEED, None
            # condition is true, run body of while loop
            status, return_value = self.__execute_statement(
                env, code[2], return_type)
            if status == ObjectDef.STATUS_RETURN:
                return (
                    status,
                    return_value,
                )  # could be a valid return of a value or an error

    # given an expression, return a Value object with the expression's evaluated result
    # expressions could be: constants (true, 5, "blah"), variables (e.g., x), arithmetic/string/logical expressions
    # like (+ 5 6), (+ "abc" "def"), (> a 5), method calls (e.g., (call me foo)), or instantiations (e.g., new dog_class)
    def __evaluate_expression(self, env, expr, line_num_of_statement):
        print(f"EXPRESSIONING {expr}")
        if not isinstance(expr, list):
            # locals shadow member variables
            val = None
            # print(f"VALLL {len(env)}")
            if len(env) == 1:
                val = env[0].get(expr)
            else:
                for i in range(len(env)-1, 0, -1):
                    val = env[i].get(expr)
                    if val:
                        print(f"HELLO VAL {val}")
                        break
            if val is not None:  # if parameter to function
                print("HEY VAL", val.value())
                return val
            if expr in self.fields:  # if it's a field
                print(f"GET FIELD {self.fields[expr][0].value()}")
                return self.fields[expr][0]
            # need to check for variable name and get its value too
            # if it's hard to differentiate between primitives and null check this out
            if expr == InterpreterBase.ME_DEF:
                return Value(Type.CLASS, self, self.class_def.name)
            value = create_value(expr)
            if value is not None:
                return value
            self.interpreter.error(
                ErrorType.NAME_ERROR,
                "invalid field or parameter " + expr,
                line_num_of_statement,
            )

        operator = expr[0]
        if operator in self.binary_op_list:
            operand1 = self.__evaluate_expression(
                env, expr[1], line_num_of_statement)
            operand2 = self.__evaluate_expression(
                env, expr[2], line_num_of_statement)
            if operand1.type() == operand2.type() and operand1.type() == Type.INT:
                if operator not in self.binary_ops[Type.INT]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to ints",
                        line_num_of_statement,
                    )
                return self.binary_ops[Type.INT][operator](operand1, operand2)
            if operand1.type() == operand2.type() and operand1.type() == Type.STRING:
                if operator not in self.binary_ops[Type.STRING]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to strings",
                        line_num_of_statement,
                    )
                return self.binary_ops[Type.STRING][operator](operand1, operand2)
            if operand1.type() == operand2.type() and operand1.type() == Type.BOOL:
                if operator not in self.binary_ops[Type.BOOL]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to bool",
                        line_num_of_statement,
                    )
                return self.binary_ops[Type.BOOL][operator](operand1, operand2)
            if operand1.type() == operand2.type() and operand1.type() == Type.CLASS:
                if operator not in self.binary_ops[Type.CLASS]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to class",
                        line_num_of_statement,
                    )
                # if operand1.value() is None or operand2.value() is None or operand1.class_name() == operand2.class_name():
                if self.comp_obj(operand1, operand2):
                    print(
                        f"OPERAND CLASSES {operand1.class_name()} {operand2.class_name()}")
                    # if either operand is null or both of of the same type (CHANGE THIS TO INCLUDE POLYMORPHISM)
                    return self.binary_ops[Type.CLASS][operator](operand1, operand2)
            # error what about an obj reference and null
            self.interpreter.error(
                ErrorType.TYPE_ERROR,
                f"operator {operator} applied to two incompatible types",
                line_num_of_statement,
            )
        if operator in self.unary_op_list:
            operand = self.__evaluate_expression(
                env, expr[1], line_num_of_statement)
            if operand.type() == Type.BOOL:
                if operator not in self.unary_ops[Type.BOOL]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid unary operator applied to bool",
                        line_num_of_statement,
                    )
                return self.unary_ops[Type.BOOL][operator](operand)

        # handle call expression: (call objref methodname p1 p2 p3)
        if operator == InterpreterBase.CALL_DEF:
            return self.__execute_call_aux(env, expr, line_num_of_statement)
        # handle new expression: (new classname)
        if operator == InterpreterBase.NEW_DEF:
            return self.__execute_new_aux(env, expr, line_num_of_statement)

    # (new classname)
    def __execute_new_aux(self, _, code, line_num_of_statement):
        obj = self.interpreter.instantiate(code[1], line_num_of_statement)
        print(f"CREATING NEW OBJECT WITH CLASS NAME {code[1]}")
        return Value(Type.CLASS, obj, code[1])

    # this method is a helper used by call statements and call expressions
    # (call object_ref/me methodname p1 p2 p3)
    def __execute_call_aux(self, env, code, line_num_of_statement):
        # determine which object we want to call the method on
        obj_name = code[1]
        if obj_name == InterpreterBase.ME_DEF:
            obj = self
        elif obj_name == InterpreterBase.SUPER_DEF:
            if not self.parent:
                self.interpreter.error(
                    ErrorType.NAME_ERROR, "Called super on an object that's not inherited", line_num_of_statement
                )
            obj = self.parent
        else:
            obj = self.__evaluate_expression(
                env, obj_name, line_num_of_statement
            ).value()
        # prepare the actual arguments for passing
        if obj is None:
            self.interpreter.error(
                ErrorType.FAULT_ERROR, "null dereference", line_num_of_statement
            )
        actual_args = []
        for expr in code[3:]:
            actual_args.append(
                self.__evaluate_expression(env, expr, line_num_of_statement)
            )
        if actual_args == []:
            print(f"CODE {code[2]}")
        else:
            for arg in actual_args:
                print(f"CODE {code[2]}, actual_args {arg.value()}")

        return obj.call_method(code[2], actual_args, line_num_of_statement)

    def __get_default_return(self, return_type):
        # returns a default value object of the function's return type
        if return_type == InterpreterBase.INT_DEF:
            return Value(Type.INT, 0)
        elif return_type == InterpreterBase.STRING_DEF:
            return Value(Type.STRING, "")
        elif return_type == InterpreterBase.BOOL_DEF:
            return Value(Type.BOOL, False)
        else:
            return Value(Type.CLASS, None, return_type)

    def __check_method_def(self, method_def, my_params):
        # checks if method call arguments match number and types of parameters of this method definition object
        if len(method_def.formal_params) != len(my_params):
            return False
        # zip formal parameter types with values of the arguments
        for param_type, param_val in zip(method_def.formal_params.values(), my_params):
            if param_type in self.interpreter.class_index:
                if param_val.type() != Type.CLASS:  # assigning primitive value to class type parameter
                    return False
                # assigning object of invalid class to this class type parameter
                if param_val.value() is None and param_val.class_name is None:  # if param_val is a null literal
                    continue    # we can assign a null literal to any class variable
                if not self.__polymorphic(param_type, param_val.class_name()):
                    return False
            elif not check_type(param_val.type(), param_type):
                return False
        return True

    def __polymorphic(self, base_name, derived_name):
        if base_name not in self.interpreter.class_index or derived_name is None:
            self.interpreter.error(
                ErrorType.TYPE_ERROR, "Non-existent or primitive type"
            )
        if base_name == derived_name:
            return True
        class_def = self.interpreter.class_index[derived_name]
        parent_def = class_def.parent
        while parent_def:
            if base_name == parent_def.name:
                return True
            parent_def = parent_def.parent
        return False

    def __map_method_names_to_method_definitions(self):
        self.methods = self.class_def.get_methods()

    def __map_fields_to_values(self):
        self.fields = {}
        for field in self.class_def.get_fields():
            val = create_value(
                field.default_field_value, field.field_type)
            # print(f"FIELD TYPE CHECKING {field.field_type} {val.type()}")
            if field.field_type in self.interpreter.class_index and val.type() == Type.CLASS:
                print(
                    f"FIELD TYPE CHECKING {field.field_name} {field.field_type} {val.class_name()}")
                self.fields[field.field_name] = (val, field.field_type)
            elif field.field_type in self.interpreter.class_index:
                self.interpreter.error(
                    ErrorType.TYPE_ERROR, f"trying to assign a non-null object to {field.field_name}")
            elif check_type(val.type(), field.field_type):
                self.fields[field.field_name] = (val, field.field_type)
            else:   # class name not found or primitive types don't match
                self.interpreter.error(
                    ErrorType.TYPE_ERROR, f"invalid type/type mismatch with field {field.field_name}")

    def __create_map_of_operations_to_lambdas(self):
        self.binary_op_list = [
            "+",
            "-",
            "*",
            "/",
            "%",
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
            "&",
            "|",
        ]
        self.unary_op_list = ["!"]
        self.binary_ops = {}
        self.binary_ops[Type.INT] = {
            "+": lambda a, b: Value(Type.INT, a.value() + b.value()),
            "-": lambda a, b: Value(Type.INT, a.value() - b.value()),
            "*": lambda a, b: Value(Type.INT, a.value() * b.value()),
            "/": lambda a, b: Value(
                Type.INT, a.value() // b.value()
            ),  # // for integer ops
            "%": lambda a, b: Value(Type.INT, a.value() % b.value()),
            "==": lambda a, b: Value(Type.BOOL, a.value() == b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() != b.value()),
            ">": lambda a, b: Value(Type.BOOL, a.value() > b.value()),
            "<": lambda a, b: Value(Type.BOOL, a.value() < b.value()),
            ">=": lambda a, b: Value(Type.BOOL, a.value() >= b.value()),
            "<=": lambda a, b: Value(Type.BOOL, a.value() <= b.value()),
        }
        self.binary_ops[Type.STRING] = {
            "+": lambda a, b: Value(Type.STRING, a.value() + b.value()),
            "==": lambda a, b: Value(Type.BOOL, a.value() == b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() != b.value()),
            ">": lambda a, b: Value(Type.BOOL, a.value() > b.value()),
            "<": lambda a, b: Value(Type.BOOL, a.value() < b.value()),
            ">=": lambda a, b: Value(Type.BOOL, a.value() >= b.value()),
            "<=": lambda a, b: Value(Type.BOOL, a.value() <= b.value()),
        }
        self.binary_ops[Type.BOOL] = {
            "&": lambda a, b: Value(Type.BOOL, a.value() and b.value()),
            "|": lambda a, b: Value(Type.BOOL, a.value() or b.value()),
            "==": lambda a, b: Value(Type.BOOL, a.value() == b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() != b.value()),
        }
        self.binary_ops[Type.CLASS] = {
            "==": lambda a, b: Value(Type.BOOL, a.value() is b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() is not b.value()),
        }

        self.unary_ops = {}
        self.unary_ops[Type.BOOL] = {
            "!": lambda a: Value(Type.BOOL, not a.value()),
        }

    def comp_obj(self, obj1, obj2):
        if obj1.class_name() is None or obj2.class_name() is None:
            return True
        if self.__polymorphic(obj1.class_name(), obj2.class_name()):
            return True
        if self.__polymorphic(obj2.class_name(), obj1.class_name()):
            return True
        return False
