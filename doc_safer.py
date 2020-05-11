import inspect
import safer
from test import get_help

README_FILE = 'README.rst'


def undent(s):
    return '\n'.join(i[:4] for i in s.splitlines())


def make_doc():
    def api(name):
        func = getattr(safer, name)
        sig = inspect.signature(func)
        doc = func.__doc__
        title = '``safer.{name}{sig}``'.format(**locals())
        underscore = '=' * len(title)

        return '{title}\n{underscore}\n{doc}\n'.format(**locals())

    doc = safer.__doc__.strip()
    apis = '\n'.join(api(name) for name in safer.__all__)
    return BODY.format(**locals()).strip()


def main():
    with safer.printer(README_FILE) as print:
        print(make_doc())

    get_help.write_help()


BODY = """
{doc}

FUNCTIONS
---------

{apis}
"""


if __name__ == '__main__':
    main()
