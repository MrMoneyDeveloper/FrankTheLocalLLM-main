from pydantic import BaseModel

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int

    model_config = {"from_attributes": True}


class EntryBase(BaseModel):
    title: str
    group: str | None = None
    content: str


class EntryCreate(EntryBase):
    pass


class EntryRead(EntryBase):
    id: int
    summary: str | None = None
    summarized: bool

    model_config = {"from_attributes": True}

