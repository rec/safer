from pathlib import Path
from unittest import TestCase, skipIf
import doc_safer
import platform


class TestDoc(TestCase):
    @skipIf(platform.python_version() < '3.6', 'Needs Python 3.6 or greater')
    def test_make_doc(self):
        actual = doc_safer.make_doc()
        in_repo = Path(doc_safer.README_FILE).read_text()
        assert actual.rstrip() == in_repo.rstrip()
