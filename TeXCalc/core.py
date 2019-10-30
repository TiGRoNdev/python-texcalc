import re
from decimal import Decimal

from .exceptions import TeXCalcException
from .defines import reserved_words
from .processors import (
    Processor,
    ContextProcessor,
    Sqrt,
    Exponentiation,
    TrigFunction,
    InverseTrigFunction,
    Constant,
    Fraction,
    Logarithm
)


def avoid_parentheses(context):
    if (
        not isinstance(context, (str, list, tuple))
        or len(context) <= 2
        or (context[0] != '(' and context[-1] != ')')
    ):
        return context

    balance = 0
    for char in context[1:-1]:
        if char == '(':
            balance += 1
        elif char == ')' and balance > 0:
            balance -= 1
        elif char == ')' and balance <= 0:
            return context

    return context[1:-1] if balance == 0 else context


class TeXCalc:
    """
    ... func = TeXCalc("\\frac{-b\\pm\\sqrt{b^{2}-4ac}}{2a}", variables=('a', 'b', 'c'))
    You can get the 'func' which is a TeX math function but in real Python

    ... result = func(a=-2.34, b=4.87, c=13, round=3)  # result = (-1.536, 3.617)
    It's the simplest way to use TeXCalc. 'round' param is to what number we should round results.
    """

    pi = ContextProcessor.STATIC_OPERANDS[r"\\pi"][0]

    DEFAULT_ROUND = 5

    def __init__(self, expression=None, variables=None, context_map=None, **kwargs):
        if variables:
            if (
                not isinstance(variables, tuple)
                or any([not isinstance(v, str) or len(v) != 1 for v in variables])
                or any([v in ContextProcessor.STATIC_OPERANDS.keys() for v in variables])
            ):
                raise TeXCalcException.InitError.BadVariables()

        if expression and context_map:
            raise TeXCalcException.InitError.BadArguments()

        if not kwargs.get('skip_context_processing', None) and context_map:
            raise TeXCalcException.InitError.BadArguments()

        self.__expr = expression if not context_map else None
        self._context_map = context_map if not expression else None

        self._processors = (
            *kwargs.get('custom_processors', []),
            Sqrt,
            Exponentiation,
            Logarithm,
            Fraction,
            TrigFunction,
            InverseTrigFunction,
            Constant,
        )

        unsupported_operands = self.__has_unsupported_operands()
        if unsupported_operands:
            raise TeXCalcException.InitError.UnsupportedOperands(unsupported_operands=unsupported_operands)

        if variables is not None and (
                not isinstance(variables, tuple)
                or not all([re.match('[a-z]$', v) for v in variables])
                or any([v in reserved_words for v in variables])
        ):
            raise TeXCalcException.InitError.BadVariables()

        self._vars = variables

        if not self._vars and self.__expr and not self.__is_immutable():
            raise TeXCalcException.InitError.NotAConst()

        if not kwargs.get('skip_context_processing', None):
            self.__make_context_map()

    def __call__(self, **kwargs):
        if self._context_map is None:
            raise TeXCalcException.InvalidContextMap.NotDefined()

        if not isinstance(self._context_map, dict):
            raise TeXCalcException.InvalidContextMap.NotDict(wrong_type=type(self._context_map))

        for k, v in self._context_map.items():
            if not isinstance(k, int):
                raise TeXCalcException.InvalidContextMap.NotIntegerIndex(wrong_type=type(k))

            if not isinstance(v, ContextProcessor):
                raise TeXCalcException.InvalidContextMap.NotContextProcessor(wrong_type=type(v))

        vars_dict = {}
        for var_name in self._vars:
            if var_name not in kwargs:
                raise TeXCalcException.UserError.NotEnoughVariables(var_name=var_name)

            try:
                vars_dict[var_name] = Decimal(str(kwargs[var_name]))
            except:
                raise TeXCalcException.UserError.NotDecimal(
                    wrong_var_name=var_name,
                    wrong_var=kwargs[var_name]
                )

        return tuple([
            round(answer, kwargs.get('round', self.DEFAULT_ROUND))
            for answer in self._context_map[0].compute(**vars_dict)
        ])

    def __has_unsupported_operands(self):
        """ Checks is there any unsupported operand and returns a list of all its occurrences if exists  """
        if not self.__expr:
            return None

        unsupported_operands = []

        for matched in re.finditer(r'\\(?P<operand>\w+)', self.__expr):
            if matched.group('operand') not in reserved_words:
                unsupported_operands.append(matched.group('operand'))

        return unsupported_operands

    def __is_immutable(self):
        """ Checks is any variable exists in self.__expr """
        if not self.__expr:
            return None

        for word in re.finditer(r'(?<!\\)\w+', self.__expr):
            if word not in reserved_words:
                return False

        return True

    def __make_context_map(self):
        self._context_map = {}

        pat_context = re.compile(r"\{(?P<context>[^\{\}]+)\}")
        pat_brackets = re.compile(r"\((?P<context>[^\(\)]+)\)")
        pat_sq_brackets = re.compile(r"(?<=\[)(?P<context>[^\(\)]+)(?=\])")

        i = 0  # sum of all iterations
        k = 0  # counter for _context_map
        self.__expr = self.__expr.replace(" ", "")  # delete all spaces

        # firstly remove {}
        result = pat_context.search(self.__expr)

        while result:
            context = avoid_parentheses(result.group('context'))

            if context not in self._context_map:
                k += 1
                self._context_map[context] = k

            self.__expr = f"{self.__expr[:result.start()]}@/{self._context_map[context]}/@{self.__expr[result.end():]}"
            result = pat_context.search(self.__expr)
            i += 1

        self._context_map[self.__expr] = 0  # context with index 0 is a main expression

        # for the second we should remove () and []
        for i in range(k + 1):
            hashmap_reversed = {v: k for k, v in self._context_map.items()}

            tmp_expr = hashmap_reversed.get(i, None)
            if not tmp_expr:
                continue

            while True:
                prev_expr = tmp_expr
                found = pat_brackets.search(tmp_expr)

                if not found:
                    found = pat_sq_brackets.search(tmp_expr)

                    if not found:
                        break
                    elif re.fullmatch(r"@/\d+/@", found.group()):
                        break

                if found.group('context') not in self._context_map:
                    k += 1
                    self._context_map[found.group('context')] = k
                    tmp_index = k
                else:
                    tmp_index = self._context_map[found.group('context')]

                tmp_expr = f"{tmp_expr[:found.start()]}@/{tmp_index}/@{tmp_expr[found.end():]}"
                self._context_map[tmp_expr] = i
                del self._context_map[prev_expr]

        self._context_map = {index: context for context, index in self._context_map.items()}

        processing = True

        while processing:
            processing = False

            for index in range(k + 1):
                for processor_class in Processor._subclasses:
                    processor = processor_class.process(self._context_map[index], once=True)

                    while processor:
                        hashmap_reversed = {v: k for k, v in self._context_map.items()}

                        if processor.borders == (0, len(self._context_map[index])):
                            break

                        processing = True

                        if processor.matched not in hashmap_reversed:
                            k += 1
                            self._context_map[k] = processor.matched
                            index_to_replace = k
                        else:
                            index_to_replace = hashmap_reversed[processor.matched]

                        self._context_map[index] = (
                            f"{self._context_map[index][0:processor.borders[0]]}@/{index_to_replace}/@"
                            f"{self._context_map[index][processor.borders[1]:]}"
                        )

                        processor = processor_class.process(self._context_map[index], once=True)

        for var in self._vars:
            index = {v: k for k, v in self._context_map.items()}.get(var, None)
            if index is None:
                k += 1
                index = k

            self._context_map[index] = var if var != 'e' else '2.7182818284'

            for i, context in self._context_map.items():
                if i == index:
                    continue

                tmp_context = context
                reserved_word_span_map = {}
                for reserved_word in reserved_words:
                    if reserved_word not in tmp_context:
                        continue

                    for matched in re.finditer(reserved_word, tmp_context):
                        reserved_word_span_map[matched.span()] = reserved_word

                    tmp_context = tmp_context.replace(reserved_word, "".join(["_" for i in range(len(reserved_word))]))

                tmp_context = tmp_context.replace(var, '|')

                for span, reserved_word in reserved_word_span_map.items():
                    tmp_context = f"{tmp_context[:span[0]]}{reserved_word}{tmp_context[span[1]:]}"

                self._context_map[i] = tmp_context.replace('|', f"@/{index}/@")

        self._context_map = {
            index: ContextProcessor(self, context, index, variable_names=self._vars)
            for index, context in self._context_map.items()
        }

    @property
    def SUPPORTED_OPERANDS(self):
        max_len = {
            'verbose_name': 0,
            'example': 0
        }

        try:
            for processor in self._processors:
                for attr, attr_max_len in max_len.items():
                    attr_len = len(getattr(processor.Doc, attr))

                    if attr_len > attr_max_len:
                        max_len[attr] = attr_len

            max_len = {k: v + 5 for k, v in max_len.items()}

            supported_operands = "\n".join([
                f"{processor.Doc.verbose_name}" \
                f"{''.join([' ' for i in range(max_len['verbose_name'] - len(processor.Doc.verbose_name))])}" \
                f"{processor.Doc.example}" \
                f"{''.join([' ' for i in range(max_len['example'] - len(processor.Doc.example))])}" \
                f"{processor.Doc.description}"
                for processor in self._processors
            ])

            supported_operands += \
                f"\nAlso:\t{', '.join([operand for operand in ContextProcessor.STATIC_OPERANDS.keys()])}"
        except:
            raise TeXCalcException.UserError.InvalidDoc()

        return supported_operands
