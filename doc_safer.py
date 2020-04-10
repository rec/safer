from __future__ import print_function
import inspect
import safer


def main():
    with safer.printer('README.rst') as print:
        print(safer.__doc__.strip())
        print()
        print('API call documentation')
        print('-----------------------')
        print()
        for i, f in enumerate(safer.__all__):
            if i:
                print()

            func = getattr(safer, f)
            print('``safer.%s%s``' % (f, inspect.signature(func)))
            print(func.__doc__.rstrip())


if __name__ == '__main__':
    main()
