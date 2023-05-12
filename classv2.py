# pylint: disable=too-few-public-methods

"""
Module with classes for class, field, and method definitions.

In P1, we don't allow overloading within a class;
two methods cannot have the same name with different parameters.
"""

from intbase import InterpreterBase, ErrorType


class MethodDef:
    """
    Wrapper struct for the definition of a member method.
    """

    def __init__(self, method_def):
        self.return_type = method_def[1]
        self.method_name = method_def[2]
        self.formal_params = {}
        for item in method_def[3]:
            self.formal_params[item[1]] = item[0]
        self.code = method_def[4]


class FieldDef:
    """
    Wrapper struct for the definition of a member field.
    """

    def __init__(self, field_def):
        self.field_type = field_def[1]
        self.field_name = field_def[2]
        self.default_field_value = field_def[3]

    def name(self):
        return self.field_name

    def value(self):
        return self.default_field_value


class ClassDef:
    """
    Holds definition for a class:
        - list of fields (and default values)
        - list of methods

    class definition: [class classname [field1 field2 ... method1 method2 ...]]
    """

    def __init__(self, class_def, interpreter, parent):
        self.interpreter = interpreter
        self.name = class_def[1]
        self.ancestors = []  # ancestors include self, parent, ...
        self.parent = parent
        if not parent:  # no inheritance, just defining fields and/or methods
            self.ancestors.append(self)
            self.__create_field_list(class_def[2:], None)
            self.__create_method_list(class_def[2:])
        else:
            self.ancestors.append(self)
            for old_person in parent.ancestors:     # give derived classes a list of class definitions that it inherits from
                self.ancestors.append(old_person)
            self.__create_field_list(class_def[4:], parent)
            self.__create_method_list(class_def[4:])

    def get_fields(self):
        """
        Get a list of FieldDefs for *all* fields in the class.
        """
        return self.fields

    def get_methods(self):
        """
        Get a list of MethodDefs for *all* methods in the class.
        """
        return self.methods

    def get_ancestors(self):
        """
        Get a list of ClassDefs for all ancestors of the current class.
        """
        return self.ancestors

    def __create_field_list(self, class_body, parent):
        fields_already = {}
        if parent:
            # fields_already = self.__create_parent_fields(parent)
            fields_already = parent.get_fields()
        self.fields = {}
        fields_defined_so_far = set()
        for member in class_body:
            if member[0] == InterpreterBase.FIELD_DEF:
                # redefinition of a field within the same class
                if member[2] in fields_defined_so_far:
                    self.interpreter.error(
                        ErrorType.NAME_ERROR,
                        "duplicate field " + member[2],
                        member[0].line_num,
                    )
                print(f"FIELD NAME: {member[2]}")
                # replaces a parent's field if it's redefined in child
                fields_already[member[2]] = FieldDef(member)
                print(f"FINAL FIELDS FOR {self.name} {member[2]} {member[3]}")
                # otherwise just adds new field to dictionary
                fields_defined_so_far.add(member[2])
        self.fields = fields_already
        # for name, field in fields_already.items():
        #     self.fields[name] = FieldDef(field)

    def __create_method_list(self, class_body):
        self.methods = {}
        methods_defined_so_far = set()
        for member in class_body:
            if member[0] == InterpreterBase.METHOD_DEF:
                if member[2] in methods_defined_so_far:  # redefinition
                    self.interpreter.error(
                        ErrorType.NAME_ERROR,
                        "duplicate method " + member[2],
                        member[0].line_num,
                    )
                self.methods[member[2]] = MethodDef(member)
                methods_defined_so_far.add(member[2])

    # def __create_parent_fields(self, parent):
    #     # create a dictionary of parent's fields
    #     parent_fields = {}
    #     parent_field_list = parent.fields
    #     for field in parent_field_list:
    #         print(f"PARENT FIELD NAME: {field.name()}")
    #         parent_fields[field.name()] = field
    #     return parent_fields