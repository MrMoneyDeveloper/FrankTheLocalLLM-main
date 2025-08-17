from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, dependencies
from . import UnitOfWork, get_uow

router = APIRouter(tags=["entries"], prefix="/entries")


class EntryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.db: Session = uow.db

    def create(self, data: schemas.EntryCreate) -> models.Entry:
        entry = models.Entry(title=data.title, group=data.group, content=data.content)
        self.uow.add(entry)
        return entry

    def read(self, group: str | None = None, q: str | None = None) -> list[models.Entry]:
        query = self.db.query(models.Entry)
        if group:
            query = query.filter(models.Entry.group == group)
        if q:
            like = f"%{q}%"
            query = query.filter(
                models.Entry.title.ilike(like) | models.Entry.content.ilike(like)
            )
        return query.all()

    def update(self, entry_id: int, data: schemas.EntryCreate) -> models.Entry:
        entry = self.db.query(models.Entry).get(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry.title = data.title
        entry.group = data.group
        entry.content = data.content
        self.uow.update(entry)
        return entry

    def delete(self, entry_id: int) -> None:
        entry = self.db.query(models.Entry).get(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        self.db.delete(entry)
        self.uow.flush()


def _get_uow(db: Session = Depends(dependencies.get_db)):
    yield from get_uow(db)


def get_service(uow: UnitOfWork = Depends(_get_uow)) -> EntryService:
    return EntryService(uow)


@router.post("/", response_model=schemas.EntryRead)
def create_entry(
    entry: schemas.EntryCreate,
    service: EntryService = Depends(get_service),
):
    result = service.create(entry)
    service.uow.flush()
    return result


@router.get("/", response_model=list[schemas.EntryRead])
def list_entries(
    group: str | None = None,
    q: str | None = None,
    service: EntryService = Depends(get_service),
):
    return service.read(group, q)
