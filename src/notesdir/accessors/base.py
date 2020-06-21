from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, List, Set, Union
from urllib.parse import urlparse, unquote_plus


@dataclass
class FileInfo:
    path: Path
    refs: Set[str] = field(default_factory=set)
    tags: Set[str] = field(default_factory=set)
    title: Optional[str] = None

    def refs_to_path(self, dest: Path) -> Set[str]:
        """Returns the subset of self.refs that refer to the specified file.

        This excludes out refs that do not refer to local files, or refer to different
        local files; but includes refs that refer to the same file despite having a different
        query string or URL fragment, or being specified via relative paths or a path
        including symlinks.

        Relative paths in self.refs are assumed to be relative to the parent of self.path.
        """
        dest = dest.resolve()
        result = set()
        for ref in self.refs:
            try:
                url = urlparse(ref)
                if (not url.scheme) or (url.scheme == 'file' and url.netloc in ['', 'localhost']):
                    src = Path(unquote_plus(url.path))
                    if not src.is_absolute():
                        src = self.path.joinpath('..', src)
                    src = src.resolve()
                    if src == dest:
                        result.add(ref)
            except ValueError:
                pass
        return result


@dataclass
class FileEdit:
    ACTION = 'unknown'
    path: Path


@dataclass
class SetAttr(FileEdit):
    ACTION = 'set_attr'
    key: str
    value: Any


@dataclass
class ReplaceRef(FileEdit):
    ACTION = 'replace_ref'
    original: str
    replacement: str


@dataclass
class Move(FileEdit):
    ACTION = 'move'
    dest: Path


class BaseAccessor:
    def parse(self, path: Path) -> FileInfo:
        raise NotImplementedError()

    def change(self, edits: List[FileEdit]) -> bool:
        if len(edits) == 0:
            return False
        if len({e.path for e in edits}) > 1:
            raise ValueError(f"change() received edits for multiple paths, which is unsupported: {edits}")
        return self._change(edits)

    def _change(self, edits: List[FileEdit]) -> bool:
        raise NotImplementedError()


class MiscAccessor(BaseAccessor):
    def parse(self, path: Path) -> FileInfo:
        return FileInfo(path)

    def _change(self, edits: List[FileEdit]) -> bool:
        raise NotImplementedError()