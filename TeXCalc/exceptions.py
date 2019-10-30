import re


def texcalc_error(attr, message, kwargs):
    def error(cls, **attr_kwargs):
        if not all([kwarg in attr_kwargs for kwarg in kwargs]):
            raise AttributeError(
                f"You should pass all values {kwargs} as kwargs, when you're rising TeXCalcException."
            )

        return cls(f"[{attr}] {message.format(**attr_kwargs)}")

    return classmethod(error)


class TeXCalcError(type):
    message = "Something gone wrong."

    def __new__(mcs, name, bases, attrs):
        for attr, message in attrs['errors'].items():
            kwargs = []
            tmp_msg = message

            while True:
                kwarg = re.search(r"\{(?P<kwarg_name>\w+)\}", tmp_msg)
                if not kwarg:
                    break
                else:
                    tmp_msg = tmp_msg[kwarg.end():]

                kwargs.append(kwarg.group('kwarg_name'))

            attrs[attr] = texcalc_error(attr, message, kwargs)

        return super().__new__(mcs, name, bases, attrs)


class TeXCalcException:
    class InitError(BaseException, metaclass=TeXCalcError):
        errors = {
            'NotAConst': "You've not passed variables to the TeXCalc. Unfortunately, it's also not a constant. "
                         "You should pass kwarg 'variables' with list of variables' names. "
                         "See TeXCalc_instance.SUPPORTED_OPERANDS to know what operands of LaTeX the TeXCalc "
                         "supports.",
            'BadArguments': "You cannot pass expression and context_map together on TeXCalc instantiation. "
                            "If you wish to run TeXCalc on preprocessed context_map then pass parameter "
                            "skip_context_processing=True.",
            'BadVariables': "In key 'variables' you should pass a tuple with variables' names. "
                            "Where variable name is a single letter character, or you want to use reserved var.",
            'UnsupportedOperands': "You should pass a LaTeX expression, only with supported operands, as a "
                                   "first parameter. Next operands aren't supported: {unsupported_operands}. "
                                   "You can check which LaTeX operands the TeXCalc supports, "
                                   "see TeXCalc_instance.SUPPORTED_OPERANDS. Notice: You should pass custom "
                                   "functions without \\ before function name(like it is in original LaTeX).",
        }

    class ComputeError(BaseException, metaclass=TeXCalcError):
        errors = {
            'NotComputableField': "Cannot compute {field} on {processor_cls}: {processor} with index {index}. "
                                  "There is a context or unaddressable index.",
            'NotComputableProcessor': "Cannot compute result on {processor_cls}: {processor} with index {index}.",
            'IncorrectLogarithm': "Logarithm functions must be without a base, except 'log'.",
            'InvalidFibonacciPosition': "Fibonacci function has received invalid position parameter={parameter}."
                                        "Only greater than 0 positions are supports.",
            'SqrtOfNegativeValue': "Can't get root with even exponent({exponent}) of negative value({value})."
        }

    class CustomFunctionError(BaseException, metaclass=TeXCalcError):
        errors = {
            'NotFoundName': "Cannot find name attribute for custom function. Please specify 'name' attr "
                            "for your CustomFunction subclass."
        }

    class FieldError(BaseException, metaclass=TeXCalcError):
        errors = {
            'BadFieldArgument': "Can't set value({value}) to field. Allow context/index operations on"
                                "field or try to set another value.",
            'BadChoicesMap': "Can't set value({value}) on field because the choices map doesn't have that key."
        }

    class InvalidContextMap(BaseException, metaclass=TeXCalcError):
        errors = {
            'NotDict': "Context map must be a dict-like object, not a {wrong_type}",
            'NotContextProcessor': "There are should be ContextProcessor's instances in a map, not {wrong_type}",
            'NotIntegerIndex': "All indices must be an int instances, not a {wrong_type}",
            'NotDefined': "Context map doesn't defined. You must define the context_map before computing a result"
        }

    class UserError(BaseException, metaclass=TeXCalcError):
        errors = {
            'NotDecimal': "You can pass only decimals as keyword parameters when calling TeXCalc instance, "
                          "not {wrong_var_name}={wrong_var}",
            'NotEnoughVariables': "You must pass all variables as keyword arguments that you've passed to "
                                  "TeXCalc constructor as 'variables' kwarg. {var_name} doesn't found.",
            'InvalidDoc': "You should define a Doc class on your CustomProcessor with string attributes: "
                          "verbose_name, example, description. For normally show help about supported operands."
        }
