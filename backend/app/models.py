
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship


from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    group = Column(String, nullable=True)
    content = Column(String, nullable=False)
    summary = Column(String, nullable=True)
    # Align column name with the .NET application's schema which expects
    # ``is_summarised``.  Expose it in Python as ``summarized`` to keep the
    # existing API and model attribute names stable.
    summarized = Column("is_summarised", Boolean, default=False)


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    content = Column(String, nullable=False)
    content_hash = Column(String, unique=True, index=True)
    start_line = Column(Integer)
    end_line = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file = relationship("File")


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True)
    summary_date = Column(DateTime, default=datetime.utcnow)
    summary = Column(String, nullable=False)
    token_count = Column(Integer)


class Backlink(Base):
    __tablename__ = "backlinks"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("chunks.id"))
    target_id = Column(Integer, ForeignKey("chunks.id"))

