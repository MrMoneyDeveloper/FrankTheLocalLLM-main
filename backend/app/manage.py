from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import Settings
from . import models
from .db import Base

settings = Settings()
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)

SAMPLE_MD = Path(__file__).resolve().parents[1] / 'data' / 'sample.md'

def migrate():
    Base.metadata.create_all(bind=engine)


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
