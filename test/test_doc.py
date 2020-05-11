from pathlib import Path
from unittest import TestCase, skipIf
import doc_safer
import io
import platform
from readme_renderer import rst
from test import get_help

README_TEXT = Path(doc_safer.README_FILE).read_text()


class TestDoc(TestCase):
    @skipIf(platform.python_version() < '3.6', 'Needs Python 3.6 or greater')
    def test_make_doc(self):
        actual = doc_safer.make_doc()
        assert actual.rstrip() == README_TEXT.rstrip()

    def test_rendering(self):
        out = io.StringIO()
        actual = rst.render(README_TEXT, out)
        if actual is None:
            print('Rendering error!')
            print(out.getvalue())
            assert False

    def test_help(self):
        with open(get_help.HELP_FILE) as fp:
            actual = fp.read()

        expected = get_help.get_help()
        assert expected == actual
