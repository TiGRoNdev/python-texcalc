import logging
import math
import re
from itertools import count, product
from decimal import Decimal

from .exceptions import TeXCalcException
from .fields import Field, DecimalField


logger = logging.getLogger(__name__)


class ProcessorMetaclass(type):
    @staticmethod
    def _get_needed_attr(key, attrs, bases):
        attr = attrs.get(key, None)

        if not attr:
            for base in bases:
                attr_tmp = getattr(base, key, None)
                if attr_tmp is not None:
                    return attr_tmp

        return attr

    def __new__(mcs, name, bases, attrs):
        pattern = mcs._get_needed_attr("pattern", attrs, bases)
        customized = mcs._get_needed_attr("_custom", attrs, bases)
        custom_name = mcs._get_needed_attr("name", attrs, bases)

        instances = mcs._get_needed_attr("_subclasses", attrs, bases)
        register = mcs._get_needed_attr("_register", attrs, bases)

        if pattern:
            if customized:
                if not custom_name:
                    raise TeXCalcException.CustomFunctionError.NotFoundName()

                if not isinstance(pattern, str):
                    pattern = pattern.pattern

                pattern = pattern.replace("<name>", custom_name)

            attrs["pattern"] = re.compile(pattern)

        new_cls = super().__new__(mcs, name, bases, attrs)

        if register:
            instances.add(new_cls)

        return new_cls


class Processor(metaclass=ProcessorMetaclass):
    _id_counter = count(0)
    _subclasses = set()
    _custom = False
    _register = False

    def __init__(self, *args, **kwargs):
        self._id = next(self._id_counter)
        self.borders = None
        self.matched = None
        self.context = None

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __str__(self):
        return str({**{
            field_name: getattr(self, field_name)
            for field_name in self.__fields().keys()
        }, **{
            'borders': self.borders,
            'matched': self.matched,
            'context': self.context
        }})

    def __bool__(self):
        return bool(self.matched)

    @classmethod
    def __create_from_search(cls, search_result, carriage, context, debug=False):
        if debug:
            logger.warning({
                'carriage': carriage,
                'search_result.start()': search_result.start(),
                'search_result.end()': search_result.end(),
                'matched': search_result.group(),
                'processed_context': context
            })

        return cls(**{
            **{
                field_name: search_result.group(field_name)
                for field_name in cls.__fields().keys()
            },
            'borders': (search_result.start() + carriage, search_result.end() + carriage),  # borders of matched
            'matched': search_result.group(),  # matched expression
            'context': context
        })

    @classmethod
    def __fields(cls):
        return {
            attr: value
            for attr, value in cls.__dict__.items()
            if isinstance(value, Field)
        }

    @classmethod
    def process(cls, context, once=False, debug=False):
        processors = []
        carriage = 0
        search_result = True
        tmp_context = context

        while search_result:
            search_result = cls.pattern.search(tmp_context)  # search in a part of context
            if not search_result:
                if once:
                    return None
                break

            processor = cls.__create_from_search(  # create processor
                search_result,
                carriage,
                tmp_context,
                debug=debug
            )
            if once:
                return processor

            processors.append(processor)

            tmp_context = tmp_context[search_result.end():]

            carriage += search_result.end()

        return processors

    @classmethod
    def validate(cls, not_context=None, index_exist=None):
        def wrapper(func):
            def function(self, indices, **kwargs):
                if not_context:
                    for attr in not_context:
                        if getattr(self, attr)['context']:
                            raise TeXCalcException.ComputeError.NotComputableField(
                                index=kwargs.get('index', None),
                                field=attr,
                                processor_cls=self.Doc.verbose_name,
                                processor=str(self)
                            )

                if index_exist:
                    for attr in index_exist:
                        value = getattr(self, attr)
                        if value['index'] and value['value'] not in indices:
                            raise TeXCalcException.ComputeError.NotComputableField(
                                index=kwargs.get('index', None),
                                field=attr,
                                processor_cls=self.Doc.verbose_name,
                                processor=str(self)
                            )

                return func(self, indices, **kwargs)

            return function

        return wrapper

    def compute(self, indices, **kwargs):
        """ Calculates own value based on variables' values in kwargs and a piece of context map(indices) """
        pass


class ContextProcessor:
    STATIC_OPERANDS = {
        r"\\pm": ('+', '-'),
        r"\\mp": ('-', '+'),
        r"\\Phi": (Decimal('1.6180339887'),),
        r"\\pi": (Decimal('3.1415926536'),),
        r"\\Omega": (Decimal('0.0078749969'),),
    }

    def __init__(self, texcalc_instance, context, index, variable_names=None, **kwargs):
        self._computed = {}  # computations cache

        if variable_names:
            if not isinstance(variable_names, tuple):
                raise TeXCalcException.InitError.BadVariables()
        """
        An order and immutability of self._vars are important, cause of a key to computations results stored in
        self._computed. The key is a tuple of variables' values in order that the variables' stored in self._vars.
        """
        self._vars = variable_names

        self._texcalc_instance = texcalc_instance
        self._context = context
        self._indices = set()  # all indices that exists in expression
        self._index = index

        self._pat_index = re.compile(r"@/(?P<index>\d+)/@")
        tmp_context = context

        # fill the _indices
        while True:
            sr = self._pat_index.search(tmp_context)
            if not sr:
                break

            self._indices.add(int(sr.group('index')))
            tmp_context = tmp_context[sr.end():]

    def __replace_static_operands(self):
        """ Returns a tuple of all possible contexts with replaced static values from STATIC_OPERANDS"""

        replacements = [
            (values, matched.span())
            for static_operand_regexp, values in self.STATIC_OPERANDS.items()
            for matched in re.finditer(static_operand_regexp, self._context)
        ]
        positions = tuple([replacement[1] for replacement in replacements])

        contexts = []
        for replacement_values in product(*[replacement[0] for replacement in replacements]):
            tmp_context = self._context

            for i in range(len(replacement_values)):
                tmp_context = \
                    f"{tmp_context[:positions[i][0]]}{replacement_values[i]}{tmp_context[positions[i][1]:]}"

            contexts.append(tmp_context)

        return tuple(contexts)

    def __computation_key(self, **kwargs):
        return tuple([str(kwargs[v]) for v in self._vars])

    def __calculate_origin(self, **kwargs):
        for processor_class in self._texcalc_instance._processors:
            processor = processor_class.process(self._context, once=True)

            if not processor:
                continue
            else:
                try:
                    return processor.compute({
                        index: self._texcalc_instance._context_map[index].compute(**kwargs)
                        for index in self._indices
                    }, index=self._index, **kwargs)
                except:
                    raise TeXCalcException.ComputeError.NotComputableProcessor(
                        processor_cls=processor.Doc.verbose_name,
                        processor=str(processor),
                        index=self._index
                    )

        # if the context is a single character variable
        if self._context in kwargs.keys():
            return (Decimal(str(kwargs[self._context])),)

        """
        If we're here, it means that context is a string which have only indexed items of hashmap, 
        operations of addition and subtraction, constants from STATIC_OPERANDS.
        Or it can be a start value of counter i=<some>
        """
        pat = re.compile(r'i=(?P<context>.*)')
        result = pat.fullmatch(self._context)
        if result:
            self._context = result.group('context')

        contexts_to_process = self.__replace_static_operands()
        index_options = tuple([
            (index, self._texcalc_instance._context_map[index].compute(**kwargs))
            for index in self._indices
        ])
        values_options = tuple(product(*[i[1] for i in index_options]))

        calculated = []

        for context in contexts_to_process:
            for value_option in values_options:
                tmp_context = context.replace("@@", "@*@")

                for i in range(len(index_options)):
                    tmp_context = tmp_context.replace(f"@/{index_options[i][0]}/@", str(value_option[i]))

                calculated.append(Decimal(str(eval(tmp_context))))

        return tuple(calculated)

    def is_computed_on(self, **kwargs):
        for v in self._vars:
            if not v in kwargs:
                raise TeXCalcException.UserError.NotEnoughVariables(var_name=v)

        return self.__computation_key(**kwargs) in self._computed

    def get_not_calculated_indices_for(self, **kwargs):
        indices = set()

        for index in self._indices:
            if not self._texcalc_instance._context_map[index].is_computed_on(**kwargs):
                indices.add(index)

        return tuple(indices)

    def compute(self, **kwargs):
        computation_key = self.__computation_key(**kwargs)

        while not self.is_computed_on(**kwargs):
            indices = self.get_not_calculated_indices_for(**kwargs)

            if len(indices) == 0:
                self._computed[computation_key] = tuple(set(self.__calculate_origin(**kwargs)))

            for index in indices:
                self._texcalc_instance._context_map[index].compute(**kwargs)

        return self._computed[computation_key]


class Constant(Processor):
    _register = True

    class Doc:
        verbose_name = "Constant"
        example = "1703.45"
        description = "You're already know what it is. Only dot is the separator."

    pattern = r'(?<![@\d/])(?P<value>[\d\.]+)'

    value = DecimalField()

    @Processor.validate(not_context=('value',), index_exist=('value',))
    def compute(self, indices, **kwargs):
        return self.value['value'],


class TrigFunction(Processor):
    _register = True

    class Doc:
        verbose_name = "Trigonometric functions"
        example = "\\sin{3}"
        description = "All supported trigonometrics: sin, cos, tan, cot, sec, csc, sinh, cosh, tanh, coth."

    pattern = r'\\(?P<function>sin|cos|tan|cot|sec|csc|sinh|cosh|tanh|coth)@(?P<parameter>/\d+/)@'

    parameter = DecimalField(indexed=True)
    function = Field(choices={
        'sin': lambda x: Decimal(str(math.sin(Decimal(str(x))))),
        'cos': lambda x: Decimal(str(math.cos(Decimal(str(x))))),
        'tan': lambda x: Decimal(str(math.tan(Decimal(str(x))))),
        'cot': lambda x: Decimal('1') / Decimal(str(math.tan(Decimal(str(x))))),
        'sec': lambda x: Decimal('1') / Decimal(str(math.cos(Decimal(str(x))))),
        'csc': lambda x: Decimal('1') / Decimal(str(math.sin(Decimal(str(x))))),
        'sinh': lambda x: Decimal(str(math.sinh(Decimal(str(x))))),
        'cosh': lambda x: Decimal(str(math.cosh(Decimal(str(x))))),
        'tanh': lambda x: Decimal(str(math.tanh(Decimal(str(x))))),
        'coth': lambda x: Decimal('1') / Decimal(str(math.tanh(Decimal(str(x)))))
    })

    @Processor.validate(not_context=('parameter',), index_exist=('parameter',))
    def compute(self, indices, **kwargs):
        if not self.parameter['index']:
            return self.function['value'](self.parameter['value']),
        else:
            return tuple([self.function['value'](parameter) for parameter in indices[self.parameter['value']]])


class InverseTrigFunction(TrigFunction):
    _register = True

    class Doc:
        verbose_name = "Inversed trigonometrics"
        example = "\\arccot{6x}"
        description = "All supported functions: arcsin, arccos, arctan, arccot, arcsec, arccsc."

    pattern = r'\\(?P<function>arcsin|arccos|arctan|arccot|arcsec|arccsc)@(?P<parameter>/\d+/)@'

    parameter = DecimalField(indexed=True)
    function = Field(choices={
        'arcsin': lambda x: Decimal(str(math.asin(Decimal(str(x))))),
        'arccos': lambda x: Decimal(str(math.acos(Decimal(str(x))))),
        'arctan': lambda x: Decimal(str(math.atan(Decimal(str(x))))),
        'arccot': lambda x: (Decimal(str(math.pi)) / Decimal('2')) - Decimal(str(math.atan(Decimal(str(x))))),
        'arcsec': lambda x: Decimal(str(math.acos(Decimal('1') / Decimal(str(x))))),
        'arccsc': lambda x: Decimal(str(math.asin(Decimal('1') / Decimal(str(x))))),
    })


class Logarithm(Processor):
    _register = True

    class Doc:
        verbose_name = "Logarithms"
        example = "\\log_{3}{8x}"
        description = "Logarithmic functions: \\lg, \\ln without a base and \\log"

    pattern = r'\\(?P<function>lg|ln|log)(_@(?P<base>/\d+/)@)?@(?P<parameter>/\d+/)@'

    base = DecimalField(indexed=True)
    parameter = DecimalField(indexed=True)
    function = Field(choices={
        'lg': lambda x, base: Decimal(str(math.log10(Decimal(str(x))))),
        'ln': lambda x, base: Decimal(str(math.log(Decimal(str(x))))),
        'log': lambda x, base: Decimal(str(math.log(Decimal(str(x)), Decimal(str(base))))),
    })

    @Processor.validate(not_context=('parameter', 'base'), index_exist=('parameter', 'base'))
    def compute(self, indices, **kwargs):
        if not self.parameter['index'] and not self.base['index']:
            return self.function['value'](self.parameter['value'], self.base['value']),
        elif not self.parameter['index'] and self.base['index']:
            return tuple([
                self.function['value'](self.parameter['value'], base)
                for base in indices[self.base['value']]
            ])
        elif self.parameter['index'] and not self.base['index']:
            return tuple([
                self.function['value'](parameter, self.base['value'])
                for parameter in indices[self.parameter['value']]
            ])
        else:
            return tuple([
                self.function['value'](parameter, base)
                for parameter in indices[self.parameter['value']]
                for base in indices[self.base['value']]
            ])


class Fraction(Processor):
    _register = True

    class Doc:
        verbose_name = "Fractions"
        example = "\\frac{1.3}{2}"
        description = "You cannot pass '/' symbol in expressions, only \\frac comm."

    pattern = r'\\frac@(?P<numerator>/\d+/)@@(?P<denominator>/\d+/)@'

    numerator = DecimalField(indexed=True)
    denominator = DecimalField(indexed=True)

    @Processor.validate(not_context=('numerator', 'denominator'), index_exist=('numerator', 'denominator'))
    def compute(self, indices, **kwargs):
        if not self.numerator['index'] and not self.denominator['index']:
            return Decimal(str(self.numerator['value'])) / Decimal(str(self.denominator['value'])),
        elif not self.numerator['index'] and self.denominator['index']:
            return tuple([
                Decimal(str(self.numerator['value'])) / Decimal(str(denominator))
                for denominator in indices[self.denominator['value']]
            ])
        elif self.numerator['index'] and not self.denominator['index']:
            return tuple([
                Decimal(str(numerator)) / Decimal(str(self.denominator['value']))
                for numerator in indices[self.numerator['value']]
            ])
        else:
            return tuple([
                Decimal(str(numerator)) / Decimal(str(denominator))
                for numerator in indices[self.numerator['value']]
                for denominator in indices[self.denominator['value']]
            ])


class Exponentiation(Processor):
    _register = True

    class Doc:
        verbose_name = "Exponentiation"
        example = "x^{2}"
        description = "You can pass whatever you need to exponentiate instead of x."

    pattern = r'(?<!_)(?P<value>(\w{1}|\\(?!sum_)(?!prod_)\w+[^^\*\-\+]+|[\d\.]+|\(.+\)|@/\d+/@))' \
              r'\^@(?P<exponent>/\d+/)@'

    value = DecimalField(context=True, indexed=True)
    exponent = DecimalField(indexed=True)

    # TODO: Simplify all compute functions because there are repeated validations
    @Processor.validate(not_context=('value', 'exponent'), index_exist=('value', 'exponent'))
    def compute(self, indices, **kwargs):
        if not self.value['index'] and not self.exponent['index']:
            return Decimal(str(self.value['value'])) ** Decimal(str(self.exponent['value'])),
        elif not self.value['index'] and self.exponent['index']:
            return tuple([
                Decimal(str(self.value['value'])) ** Decimal(str(exponent))
                for exponent in indices[self.exponent['value']]
            ])
        elif self.value['index'] and not self.exponent['index']:
            return tuple([
                Decimal(str(value)) ** Decimal(str(self.exponent['value']))
                for value in indices[self.value['value']]
            ])
        else:
            return tuple([
                Decimal(str(value)) ** Decimal(str(exponent))
                for value in indices[self.value['value']]
                for exponent in indices[self.exponent['value']]
            ])


class Sqrt(Processor):
    _register = True

    class Doc:
        verbose_name = "Square(or not) root"
        example = "\\sqrt[3]{2x}"
        description = "You can pass whatever you need to [] and {} brackets."

    pattern = r'\\sqrt(\[@(?P<exponent>/\d+/)@\])?@(?P<value>/\d+/)@'

    exponent = DecimalField(indexed=True, default=Decimal('2'))
    value = DecimalField(indexed=True)

    @Processor.validate(not_context=('value', 'exponent'), index_exist=('value',))
    def compute(self, indices, **kwargs):
        if not self.value['index'] and not self.exponent['index']:
            if self.exponent['value'] <= 0 or (self.exponent['value'] % 2 == 0 and self.value['value'] < 0):
                raise TeXCalcException.ComputeError.SqrtOfNegativeValue(
                    exponent=self.exponent['value'],
                    value=self.value['value']
                )

            return Decimal(str(self.value['value'])) ** (Decimal('1') / Decimal(str(self.exponent['value']))),
        elif not self.value['index'] and self.exponent['index']:
            if (
                any([exp <= 0 for exp in indices[self.exponent['value']]])
                or (any([exp % 2 == 0 for exp in indices[self.exponent['value']]]) and self.value['value'] < 0)
            ):
                raise TeXCalcException.ComputeError.SqrtOfNegativeValue(
                    exponent=indices[self.exponent['value']],
                    value=self.value['value']
                )

            return tuple([
                Decimal(str(self.value['value'])) ** (Decimal('1') / Decimal(str(exponent)))
                for exponent in indices[self.exponent['value']]
            ])
        elif self.value['index'] and not self.exponent['index']:
            if (
                self.exponent['value'] <= 0 or
                (self.exponent['value'] % 2 == 0 and any([value < 0 for value in indices[self.value['value']]]))
            ):
                raise TeXCalcException.ComputeError.SqrtOfNegativeValue(
                    exponent=self.exponent['value'],
                    value=indices[self.value['value']]
                )

            return tuple([
                Decimal(str(value)) ** (Decimal('1') / Decimal(str(self.exponent['value'])))
                for value in indices[self.value['value']]
            ])
        else:
            if (
                any([exp <= 0 for exp in indices[self.exponent['value']]]) or
                (
                        any([exp % 2 == 0 for exp in indices[self.exponent['value']]])
                        and any([value < 0 for value in indices[self.value['value']]])
                )
            ):
                raise TeXCalcException.ComputeError.SqrtOfNegativeValue(
                    exponent=indices[self.exponent['value']],
                    value=indices[self.value['value']]
                )

            return tuple([
                Decimal(str(value)) ** (Decimal('1') / Decimal(str(exponent)))
                for value in indices[self.value['value']]
                for exponent in indices[self.exponent['value']]
            ])


"""
class Sum(Processor):
    _register = True

    class Doc:
        verbose_name = "Sum"
        example = "\\sum_{i=0}^{x}{i}"
        description = "In this case, here is the sum of all numbers behind the x. i=<some> is required starts."

    pattern = r'\\sum_@(?P<i_start>/\d+/)@\^@(?P<i_end>/\d+/)@@(?P<value>/\d+/)@'

    i_start = IntegerField(indexed=True)
    i_end = IntegerField(indexed=True)
    value = DecimalField(indexed=True)

    @Processor.validate(not_context=('i_start', 'i_end', 'value'), index_exist=('i_start', 'i_end', 'value'))
    def compute(self, indices, **kwargs):
        i_start = self.i_start['value'] if not self.i_start['index'] else indices[self.i_start['value']]
        i_end = self.i_end['value'] if not self.i_end['index'] else indices[self.i_end['value']]
        value = self.value['value'] if not self.value['index'] else indices[self.value['value']]

        return Decimal(sum([value(i) for i in range(int(i_start), int(i_end) + 1)]))


class Prod(Processor):
    _register = True

    class Doc:
        verbose_name = "Product"
        example = "\\prod_{i=1}^{x+2}{i}"
        description = "In this case, its expression is equal to (x+2)!. i=<some> is required starts."

    pattern = r'\\prod_@(?P<i_start>/\d+/)@\^@(?P<i_end>/\d+/)@@(?P<value>/\d+/)@'

    i_start = IntegerField(indexed=True)
    i_end = IntegerField(indexed=True)
    value = DecimalField(indexed=True)

"""


# Processors with possibility of custom logic creation:

class CustomFunction(Processor):
    _register = False
    _custom = True

    pattern = r'<name>@(?P<parameter>[\d/]+)@'
    name = '<name>'

    parameter = DecimalField(indexed=True)


# Custom processors:

class FibonacciFunction(CustomFunction):
    _register = True

    class Doc:
        verbose_name = "Fibonacci function"
        example = "fib(x + 3)"
        description = "Returns an element of fibonacci sequence by given index, starts: 1, 1, 2, 3..."

    name = "fib"

    parameter = DecimalField(indexed=True)

    @Processor.validate(not_context=('parameter',), index_exist=('parameter',))
    def compute(self, indices, **kwargs):
        parameters = (
            [int(self.parameter['value'])]
            if not self.parameter['index'] else [int(i) for i in indices[int(self.parameter['value'])]]
        )
        answers = []

        for parameter in parameters:
            if parameter < 1:
                raise TeXCalcException.ComputeError.InvalidFibonacciPosition(parameter=parameter)

            prev = 1
            curr = 1
            for i in range(3, parameter + 1):
                if parameter < 3:
                    answers.append(Decimal('1'))
                    break

                tmp = curr

                curr += prev
                prev = tmp

            answers.append(Decimal(str(curr)))

        return tuple(answers)
