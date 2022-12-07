import io
from pathlib import Path
from test import get_help
from unittest import TestCase

from readme_renderer import rst

README_TEXT = (Path(__file__).parents[1] / 'README.rst').read_text()


class TestDoc(TestCase):
    def test_rendering(self):
        out = io.StringIO()
        actual = rst.render(README_TEXT, out)
        if actual is None:
            print('Rendering error!')
            print(out.getvalue())
            assert False

    def test_help(self):
        actual = Path(get_help.HELP_FILE).read_text()
        expected = get_help.get_help()
        assert expected == actual
