from pathlib import Path
from unittest.mock import call, Mock
from urllib.parse import urlparse
import pytest
from notesdir.accessors.base import BaseAccessor, FileInfo, Move, ReplaceRef, SetAttr
from notesdir.store import ref_path, path_as_ref, FSStore


def test_ref_path_same_file():
    src = Path('foo/bar')
    dest = Path('foo/bar')
    assert ref_path(src, dest) == Path('bar')


def test_ref_path_same_dir():
    src = Path('foo/bar')
    dest = Path('foo/baz')
    assert ref_path(src, dest) == Path('baz')


def test_ref_path_sibling_descendant():
    src = Path('foo/bar')
    dest = Path('foo/baz/meh')
    assert ref_path(src, dest) == Path('baz/meh')


def test_ref_path_common_ancestor():
    src = Path('foo/bar/baz')
    dest = Path('foo/meh')
    assert ref_path(src, dest) == Path('../meh')


def test_ref_path_root_is_only_common_ancestor():
    src = Path('/foo/bar')
    dest = Path('/baz/meh')
    assert ref_path(src, dest) == Path('../baz/meh')


def test_ref_path_root_is_only_common_ancestor_relative(fs):
    src = Path('foo/bar')
    dest = Path('baz/meh')
    fs.cwd = '/'
    assert ref_path(src, dest) == Path('../baz/meh')


# Not sure if this is a real use case for this function
def test_ref_path_child():
    src = Path('foo')
    dest = Path('foo/bar')
    assert ref_path(src, dest) == Path('foo/bar')


# Not sure if this is a real use case for this function
def test_ref_path_parent():
    src = Path('foo/bar')
    dest = Path('foo')
    assert ref_path(src, dest) == Path('.')


def test_ref_path_relative_to_absolute(fs):
    src = Path('foo/bar')
    dest = Path('/somewhere/beta/file')
    fs.cwd = '/somewhere/alpha'
    assert ref_path(src, dest) == Path('../../beta/file')


def test_ref_path_absolute_to_relative(fs):
    src = Path('/somewhere/beta/file')
    dest = Path('foo/bar')
    fs.cwd = '/somewhere/alpha'
    assert ref_path(src, dest) == Path('../alpha/foo/bar')


def test_ref_path_symlinks(fs):
    src = Path('/foo/bar/baz')
    dest = Path('/whatever/hello')
    fs.create_symlink('/whatever', '/foo/meh')
    assert ref_path(src, dest) == Path('../meh/hello')


def test_ref_path_symlinks_relative(fs):
    src = Path('foo/bar/baz')
    dest = Path('whatever/hello')
    fs.create_symlink('/cwd/whatever', '/cwd/foo/meh')
    fs.cwd = '/cwd'
    assert ref_path(src, dest) == Path('../meh/hello')


def test_path_as_ref_absolute():
    assert path_as_ref(Path('/foo/bar/baz')) == '/foo/bar/baz'


def test_path_as_ref_relative():
    assert path_as_ref(Path('../bar/baz')) == '../bar/baz'


def test_path_as_ref_absolute_into_url():
    parts = urlparse('/foo/bar/baz#f?k=v')
    assert path_as_ref(Path('/meh/ok'), parts) == '/meh/ok#f?k=v'


def test_path_as_ref_relative_into_url():
    parts = urlparse('/foo/bar/baz#f?k=v')
    assert path_as_ref(Path('../meh/ok'), parts) == '../meh/ok#f?k=v'


def test_path_as_ref_absolute_into_url_with_scheme():
    parts = urlparse('file://localhost/foo/bar/baz')
    assert path_as_ref(Path('/meh/ok'), parts) == 'file://localhost/meh/ok'


def test_path_as_ref_relative_into_url_with_scheme():
    parts = urlparse('file://localhost/foo/bar/baz')
    with pytest.raises(ValueError):
        path_as_ref(Path('../meh/ok'), parts)


def test_path_as_ref_special_characters():
    assert path_as_ref(Path('/a dir/a file!.md')) == '/a%20dir/a%20file%21.md'


def test_path_as_ref_special_characters_into_url():
    parts = urlparse('/foo/bar/baz#f?k=v')
    assert path_as_ref(Path('/a dir/a file!.md'), parts) == '/a%20dir/a%20file%21.md#f?k=v'


class MockAccessor(BaseAccessor):
    def __init__(self, infos=None):
        self.infos = infos or {}

    def parse(self, path):
        return self.infos.get(path)

    def _change(self, path, edits):
        raise NotImplementedError()

    def mockinfo(self, pathstr):
        path = Path(pathstr).resolve()
        if path not in self.infos:
            self.infos[path] = FileInfo(path)
        return self.infos[path]


def test_referrers(fs):
    fs.cwd = '/notes/foo'
    fs.create_file('/notes/foo/subject')
    fs.create_file('/notes/bar/baz/r1')
    fs.create_file('/notes/bar/baz/no')
    fs.create_file('/notes/r2')
    fs.create_file('/notes/foo/r3')
    accessor = MockAccessor()
    accessor.mockinfo('/notes/bar/baz/r1').refs = {'no', '../../foo/subject'}
    accessor.mockinfo('/notes/bar/baz/no').refs = {'../../foo/bogus'}
    accessor.mockinfo('/notes/r2').refs = {'foo/subject', 'foo/bogus'}
    accessor.mockinfo('/notes/foo/r3').refs = {'subject'}
    store = FSStore(Path('/notes'), accessor)
    expected = {Path(p) for p in {'/notes/bar/baz/r1', '/notes/r2', '/notes/foo/r3'}}
    assert store.referrers(Path('subject')) == expected


def test_referrers_self(fs):
    fs.create_file('/notes/subject')
    accessor = MockAccessor()
    accessor.mockinfo('/notes/subject').refs = {'subject'}
    store = FSStore(Path('/notes'), accessor)
    expected = {Path('/notes/subject')}
    assert store.referrers(Path('/notes/subject')) == expected


def test_change(fs):
    fs.create_file('/notes/one')
    fs.create_file('/notes/two')
    edits = [SetAttr(Path('/notes/one'), 'title', 'New Title'),
             ReplaceRef(Path('/notes/one'), 'old', 'new'),
             Move(Path('/notes/one'), Path('/notes/moved')),
             ReplaceRef(Path('/notes/two'), 'foo', 'bar')]
    accessor = Mock()
    store = FSStore(Path('/notes'), accessor)
    store.change(edits)
    assert not Path('/notes/one').exists()
    assert Path('/notes/moved').exists()
    accessor.assert_has_calls([call.change(edits[0:2]), call.change([edits[3]])])
