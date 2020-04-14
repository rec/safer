from __future__ import print_function
import inspect
import safer


def main():
    with safer.printer('README.rst') as print:
        print(safer.__doc__.strip())
        print()

        sigs = []
        examples = {}
        for name in safer.__all__:
            func = getattr(safer, name)
            sig = inspect.signature(func)
            examples[name] = getattr(func, '_examples', '')
            doc = func.__doc__.rstrip()
            sigs.append('``safer.{name}{sig}``\n{doc}'.format(locals()))

        print('EXAMPLES')
        print('---------')
        print()
        for name, example in examples.items():
            print(EXAMPLE_FMT.format(name=name))
            for line in example.splitlines():
                print('  ', line)
            print()

        print('API call documentation')
        print('-----------------------')
        print()
        print(*sigs, sep='\n\n')


EXAMPLE_FMT = """``safer.{name}``
================

.. code-block:: python
"""

if __name__ == '__main__':
    main()
