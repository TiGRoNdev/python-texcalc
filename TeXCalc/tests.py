import unittest

from .processors import Processor, Constant, TrigFunction, Logarithm, Exponentiation, FibonacciFunction
from .core import avoid_parentheses


class AvoidParentBracketsTestCase(unittest.TestCase):
    expressions = (
        "",
        23,
        None,
        ['(', '2', '(', 'x', '-', ')', '-', '(', '3', 'x', ' ', '+', ' ', '5', ')', ')'],
        "asdasdasdasd",
        "(x^{2} + 5(2x - 4) + 3*34)",
        "(23 + 56)/(-(1 + 7)(4 - 7))",
        "(x)",
        "(2 - 7) - (34 + 4x)",
        "(2(x - (2^(3)))-(3x + 5))"
    )
    right_results = (
        "",
        23,
        None,
        ['2', '(', 'x', '-', ')', '-', '(', '3', 'x', ' ', '+', ' ', '5', ')'],
        "asdasdasdasd",
        "x^{2} + 5(2x - 4) + 3*34",
        "(23 + 56)/(-(1 + 7)(4 - 7))",
        "x",
        "(2 - 7) - (34 + 4x)",
        "2(x - (2^(3)))-(3x + 5)"
    )

    def setUp(self):
        self.results = tuple(avoid_parentheses(expr) for expr in self.expressions)

    def test_results(self):
        for i in range(len(self.right_results)):
            self.assertEqual(self.right_results[i], self.results[i])


class ProcessorTestCase(unittest.TestCase):
    processor_class = Processor
    expr = ""
    right_borders = ()
    right_matched = ()

    def setUp(self):
        self.processors = self.processor_class.process(self.expr)

    def test_borders(self):
        for i in range(len(self.processors)):
            self.assertEqual(self.processors[i].borders, self.right_borders[i])

    def test_matched(self):
        for i in range(len(self.processors)):
            self.assertEqual(self.processors[i].matched, self.right_matched[i])


class ConstantTestCase(ProcessorTestCase):
    processor_class = Constant
    expr = "\\sqrt[3.4]@/5/@-\\log_@/3/@(3.4x^@/1/@)+120.3452^@/23/@-2@/1/@"
    right_borders = (
        (6, 9),
        (27, 30),
        (39, 47),
        (55, 56)
    )
    right_matched = (
        "3.4",
        "3.4",
        "120.3452",
        "2"
    )


class TrigFunctionTestCase(ProcessorTestCase):
    processor_class = TrigFunction
    expr = "\\sqrt[\\cosh@/3/@]@/5/@-120.3452\\csc@/1/@^@/1/@+\\sin(10x^@/1/@)"
    right_borders = (
        (6, 16),
        (31, 40)
    )
    right_matched = (
        "\\cosh@/3/@",
        "\\csc@/1/@"
    )


class LogarithmTestCase(ProcessorTestCase):
    processor_class = Logarithm
    expr = "\\sqrt[\\lg@/5/@]@/5/@-\\log_@/3/@@/5/@+120.3452^@/23/@-\\ln@/3/@@/1/@"
    right_borders = (
        (6, 14),
        (21, 36),
        (53, 61)
    )
    right_matched = (
        "\\lg@/5/@",
        "\\log_@/3/@@/5/@",
        "\\ln@/3/@"
    )


class ExponentiationTestCase(ProcessorTestCase):
    processor_class = Exponentiation
    expr = "\\sqrt[\\lg@/5/@]@/5/@^@/2/@-\\log_@/3/@@/5/@+120.3452^@/23/@-(\\ln@/3/@@/1/@+4)^@/5/@-2xb" \
           "^@/3/@-23a@/2/@^@/3/@@/6/@x^@/3/@+\\sum_@/20/@^@/14/@@/29/@"
    right_borders = (
        (0, 26),
        (43, 58),
        (59, 82),
        (85, 92),
        (96, 107),
        (112, 119)
    )
    right_matched = (
        "\\sqrt[\\lg@/5/@]@/5/@^@/2/@",
        "120.3452^@/23/@",
        "(\\ln@/3/@@/1/@+4)^@/5/@",
        "b^@/3/@",
        "@/2/@^@/3/@",
        "x^@/3/@"
    )


class FibonacciFunctionTestCase(ProcessorTestCase):
    processor_class = FibonacciFunction
    expr = "\\sqrt[\\lg@/5/@fib@/3/@]@/5/@^@/2/@-2xb^@/3/@fib@/6/@-23a@/2/@^@/3/@"
    right_borders = (
        (14, 22),
        (44, 52)
    )
    right_matched = (
        "fib@/3/@",
        "fib@/6/@"
    )


if __name__ == '__main__':
    unittest.main()
