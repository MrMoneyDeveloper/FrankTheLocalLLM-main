from fastapi import APIRouter, UploadFile, File as UploadFileType, Depends
from sqlalchemy.orm import Session
from zipfile import ZipFile
from pathlib import Path
import hashlib
import tempfile

from .. import models, dependencies, tasks

router = APIRouter(tags=["import"])
UPLOAD_ROOT = Path("uploads")
UPLOAD_ROOT.mkdir(exist_ok=True)


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8")


def split_by_heading(text: str):
    lines = text.splitlines()
    chunks = []
    start = 0
    current = []
    for idx, line in enumerate(lines, 1):
        if line.startswith("#") and current:
            chunks.append(("\n".join(current), start, idx-1))
            current = []
            start = idx
        current.append(line)
    if current:
        chunks.append(("\n".join(current), start, len(lines)))
    return chunks


def get_db(dep=Depends(dependencies.get_db)):
    yield from dep


@router.post("/import")
async def import_zip(file: UploadFile = UploadFileType(...), db: Session = Depends(get_db)):
    data = await file.read()
    tmp_dir = Path(tempfile.mkdtemp())
    zip_path = tmp_dir / "upload.zip"
    zip_path.write_bytes(data)
    with ZipFile(zip_path) as zf:
        zf.extractall(tmp_dir)
    for path in tmp_dir.rglob("*"):
        if path.suffix.lower() not in {".md", ".pdf"}:
            continue
        text = extract_text(path)
        db_file = db.query(models.File).filter_by(path=str(path.name)).first()
        if not db_file:
            db_file = models.File(path=str(path.name), name=path.name)
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
        for chunk_text, start, end in split_by_heading(text):
            h = hashlib.sha256(chunk_text.encode()).hexdigest()
            exists = db.query(models.Chunk).filter_by(content_hash=h).first()
            if exists:
                continue
            chunk = models.Chunk(file_id=db_file.id, content=chunk_text, content_hash=h,
                                 start_line=start, end_line=end)
            db.add(chunk)
            db.commit()
            db.refresh(chunk)
            tasks.embed_chunk.delay(chunk.id)
    return {"status": "ok"}
