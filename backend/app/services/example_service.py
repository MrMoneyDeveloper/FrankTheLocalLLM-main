from fastapi import APIRouter, Depends

from . import UnitOfWork, get_uow
from .. import dependencies

router = APIRouter()


class ExampleService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def read(self) -> dict:
        return {"message": "Hello from FastAPI"}

    def create(self, *a, **kw):
        raise NotImplementedError

    def update(self, *a, **kw):
        raise NotImplementedError

    def delete(self, *a, **kw):
        raise NotImplementedError


def _get_uow(db=Depends(dependencies.get_db)):
    yield from get_uow(db)


def get_service(uow: UnitOfWork = Depends(_get_uow)) -> ExampleService:
    return ExampleService(uow)


@router.get("/")
def api_root(service: ExampleService = Depends(get_service)):
    """Provide a basic response for the API root path."""
    return service.read()


@router.get("/hello")
def read_hello(service: ExampleService = Depends(get_service)):
    """Retain the original example endpoint under /api/hello."""
    return service.read()
