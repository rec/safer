from __future__ import print_function
import inspect
import safer

README_FILE = 'README.rst'


def make_doc(print):
    def api(name):
        func = getattr(safer, name)
        sig = inspect.signature(func)
        docs = safer._DOC_FUNC[name].splitlines()
        doc = '\n'.join('    ' + i for i in docs)
        return '``safer.{name}{sig}``\n{doc}\n'.format(**locals())

    doc = safer.__doc__.strip()
    failure = safer._DOC_FAILURE.strip()
    common = safer._DOC_COMMON.strip()
    args = safer._DOC_ARGS.strip()
    apis = '\n'.join(api(name) for name in safer.__all__)
    print(BODY.format(**locals()).strip())


def main():
    with safer.printer(README_FILE) as print:
        make_doc(print)


BODY = """
{doc}

NOTES
--------

{failure}

{common}

FUNCTIONS
---------

{args}

{apis}
"""


if __name__ == '__main__':
    main()
