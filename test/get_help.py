import os
import pydoc
import safer

HELP_FILE = os.path.join(os.path.dirname(__file__), 'help.txt')


def get_help():
    items = [getattr(safer, k) for k in safer.__all__] + [safer]
    text = ''.join(pydoc.render_doc(i, title='Help on %s:') for i in items)
    lines = text.splitlines()[:-5]
    return '\n'.join(lines) + '\n'


def write_help():
    with safer.open(HELP_FILE, 'w') as fp:
        fp.write(get_help())


if __name__ == '__main__':
    write_help()
