from datetime import datetime
from pathlib import Path
from typing import List, Optional
from PyPDF4 import PdfFileReader, PdfFileMerger
from notesdir.accessors.base import BaseAccessor, FileInfo, FileEdit


def pdf_strptime(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.replace("'", '').replace('Z0000', 'Z')
    if len(s) < 17:
        return datetime.strptime(s, 'D:%Y%m%d%H%M%S')
    else:
        return datetime.strptime(s, 'D:%Y%m%d%H%M%S%z')


def pdf_strftime(d: Optional[datetime]) -> Optional[str]:
    if not d:
        return None
    s = datetime.strftime(d, 'D:%Y%m%d%H%M%S')
    tz = datetime.strftime(d, '%z')
    if tz == '+0000':
        return f"{s}Z00'00'"
    else:
        return f"{s}{tz[:3]}'{tz[3:]}'"


class PDFAccessor(BaseAccessor):
    def parse(self, path: Path) -> FileInfo:
        info = FileInfo(path)
        with path.open('rb') as file:
            try:
                pdf = PdfFileReader(file)
                pdfinfo = pdf.getDocumentInfo()
                info.title = pdfinfo.title or None
                info.created = pdf_strptime(pdfinfo['/CreationDate'])
                info.tags.update(t.strip() for t in pdfinfo['/Keywords'].split(',') if t.strip())
            except:
                # TODO
                pass
        return info

    def _change(self, edits: List[FileEdit]) -> bool:
        path = edits[0].path
        merger = PdfFileMerger()

        with path.open('rb') as file:
            pdf = PdfFileReader(file)
            oldmeta = {k: v for k, v in pdf.getDocumentInfo().items()}
            newmeta = oldmeta.copy()

            for edit in edits:
                if edit.ACTION == 'set_attr':
                    if edit.key == 'title':
                        newmeta['/Title'] = edit.value
                    elif edit.key == 'created':
                        newmeta['/CreationDate'] = pdf_strftime(edit.value)

            if oldmeta == newmeta:
                return False

            merger.append(file)

        merger.addMetadata(newmeta)
        with path.open('wb') as file:
            merger.write(file)

        return True
