from pathlib import Path
from typing import List

from notesdir.models import FileInfo, FileEditCmd


class ParseError(Exception):
    def __init__(self, message: str, path: Path, cause: BaseException = None):
        self.message = message
        self.path = path
        self.cause = cause


class ChangeError(Exception):
    def __init__(self, message: str, edits: List[FileEditCmd], cause: BaseException = None):
        self.message = message
        self.edits = edits
        self.cause = cause


class UnsupportedChangeError(ChangeError):
    def __init__(self, edit: FileEditCmd):
        super().__init__('Unsupported edit', [edit])


class BaseAccessor:
    def parse(self, path: Path) -> FileInfo:
        raise NotImplementedError()

    def change(self, edits: List[FileEditCmd]) -> bool:
        if len(edits) == 0:
            return False
        if len({e.path for e in edits}) > 1:
            raise ValueError(f"change() received edits for multiple paths, which is unsupported: {edits}")
        return self._change(edits)

    def _change(self, edits: List[FileEditCmd]) -> bool:
        raise NotImplementedError()


class MiscAccessor(BaseAccessor):
    def parse(self, path: Path) -> FileInfo:
        return FileInfo(path)

    def _change(self, edits: List[FileEditCmd]) -> bool:
        raise NotImplementedError()
