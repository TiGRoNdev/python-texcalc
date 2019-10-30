import re

from TeXCalc.defines import reserved_words
from TeXCalc.core import TeXCalc, avoid_parentheses
from TeXCalc.processors import ContextProcessor, Processor, FibonacciFunction


string = "\\frac{1}{4}(3\\sin{a} - \\sin{3a})"
variables = {
    'a': - 3.1415926536 / 6,
    'b': 3
}

hashmap = {}
pat = re.compile(r"\{(?P<context>[^\{\}]+)\}")
pat_brackets = re.compile(r"\((?P<context>[^\(\)]+)\)")
pat_sq_brackets = re.compile(r"(?<=\[)(?P<context>[^\(\)]+)(?=\])")

i = 0  # iterations counter
k = 0  # counter of hashmap elements
expr = string.replace(" ", "")  # deleting all spaces

# firstly remove {}
result = pat.search(expr)

while result:
    context = avoid_parentheses(result.group('context'))

    if context not in hashmap:
        k += 1
        hashmap[context] = k

    expr = f"{expr[:result.start()]}@/{hashmap[context]}/@{expr[result.end():]}"
    result = pat.search(expr)
    i += 1

hashmap[expr] = 0  # context with zero index is the main expression

# for the next removing () and extracting context from []
for i in range(k + 1):
    hashmap_reversed = {v: k for k, v in hashmap.items()}

    tmp_expr = hashmap_reversed.get(i, None)
    if not tmp_expr:
        continue

    tmp_index = None

    while True:
        prev_expr = tmp_expr
        found = pat_brackets.search(tmp_expr)

        if not found:
            found = pat_sq_brackets.search(tmp_expr)

            if not found:
                break
            elif re.fullmatch(r"@/\d+/@", found.group()):
                break

        if found.group('context') not in hashmap:
            k += 1
            hashmap[found.group('context')] = k
            tmp_index = k
        else:
            tmp_index = hashmap[found.group('context')]

        tmp_expr = f"{tmp_expr[:found.start()]}@/{tmp_index}/@{tmp_expr[found.end():]}"
        hashmap[tmp_expr] = i
        del hashmap[prev_expr]

hashmap = {v: k for k, v in hashmap.items()}  # index: context

processors = []

# Processing all the contexts in the hashmap before we can't get a processor with borders
# that equals to context borders

processing = True

while processing:
    processing = False

    for index in range(k + 1):
        for processor_class in Processor._subclasses:
            processor = processor_class.process(hashmap[index], once=True)

            while processor:
                hashmap_reversed = {v: k for k, v in hashmap.items()}

                if processor.borders == (0, len(hashmap[index])):
                    break

                processing = True

                index_to_replace = None
                if processor.matched not in hashmap_reversed:
                    k += 1
                    hashmap[k] = processor.matched
                    index_to_replace = k
                else:
                    index_to_replace = hashmap_reversed[processor.matched]

                hashmap[
                    index] = f"{hashmap[index][0:processor.borders[0]]}@/{index_to_replace}/@{hashmap[index][processor.borders[1]:]}"

                processor = processor_class.process(hashmap[index], once=True)


for var in variables.keys():
    index = {v: k for k, v in hashmap.items()}.get(var, None)
    if index is None:
        k += 1
        index = k

    hashmap[index] = var if var != 'e' else '2.7182818284'

    for i, context in hashmap.items():
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

        hashmap[i] = tmp_context.replace('|', f"@/{index}/@")

func = TeXCalc(
    variables=('a', 'b'),
    custom_processors=(FibonacciFunction,),
    skip_context_processing=True
)

hashmap = {
    index: ContextProcessor(func, context, index, variable_names=('a', 'b'))
    for index, context in hashmap.items()
}

func._context_map = hashmap

print(func(**variables))
