from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from .config import Settings
from . import models
from .db import Base

settings = Settings()
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)

SAMPLE_MD = Path(__file__).resolve().parents[1] / 'data' / 'sample.md'

def migrate():
    """Create or upgrade the SQLite schema.

    ``Base.metadata.create_all`` only creates tables; it does not add missing
    columns on existing databases.  Development databases created before the
    introduction of the ``title``, ``group``, ``summary`` and
    ``is_summarised`` columns would therefore lack these fields and cause the
    .NET application to crash.  Here we detect the legacy schema and apply the
    minimal ``ALTER TABLE`` statements to bring it up to date.
    """

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("entries")}
    with engine.begin() as conn:
        if "title" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE entries ADD COLUMN title TEXT NOT NULL DEFAULT ''"
                )
            )
        if "group" not in existing:
            # 'group' is a reserved keyword in SQL, hence the quoting
            conn.execute(
                text(
                    'ALTER TABLE entries ADD COLUMN "group" TEXT NOT NULL DEFAULT \'\''
                )
            )
        if "summary" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE entries ADD COLUMN summary TEXT NOT NULL DEFAULT ''"
                )
            )
        if "is_summarised" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE entries ADD COLUMN is_summarised BOOLEAN NOT NULL DEFAULT 0"
                )
            )


def seed():
    if not SAMPLE_MD.exists():
        return
    session = Session()
    with SAMPLE_MD.open() as f:
        text = f.read()
    entry = models.Entry(content=text)
    session.add(entry)
    session.commit()
    session.close()

if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'migrate'
    if cmd == 'migrate':
        migrate()
    elif cmd == 'seed':
        seed()
