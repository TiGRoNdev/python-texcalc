from TeXCalc import TeXCalc, FibonacciFunction

# Sum of sin(a) and sin(b)
func = TeXCalc(
    "2\\sin{\\frac{a + b}{2}}\\cos{\\frac{a - b}{2}}",
    variables=('a', 'b'),
)

# For the next we can use the func with many different values, each result will be cached
print(f"Example 1.1: {func(a=-TeXCalc.pi / 6, b=TeXCalc.pi / 2)}")  # sin(-pi/6) + sin(pi/2)
print(f"Example 1.2: {func(a=TeXCalc.pi, b=3 * TeXCalc.pi)}")


# Roots of the quadratic equation
func = TeXCalc(
    "\\frac{-b \\pm \\sqrt{b^{2} - 4ac}}{2a}",
    variables=('a', 'b', 'c')
)

print(f"Example 2.1: {func(a=1, b=-8, c=15)}")
print(f"Example 2.2: {func(a=-2, b=10, c=12)}")
print(f"Example 2.3: {func(a=1.5, b=-7.5, c=6)}")


# Example with using the CustomFunction(Fibonacci) and logarithms
func = TeXCalc(
    "fib(x) - \\log_{2}{\\sqrt[3]{x - 1} + 2}",
    variables=('x',),
    custom_processors=(FibonacciFunction,)
)

print(f"Example 3.1: {func(x=9)}")  # 1 1 2 3 5 8 13 21 34
