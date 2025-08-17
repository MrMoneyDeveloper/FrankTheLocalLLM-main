from sqlalchemy.orm import Session

from ..llm import LLMClient
from . import CachedLLMService
from ..models import Entry

class SummarizationService(CachedLLMService):
    def __init__(self, llm: LLMClient):
        super().__init__(llm)

    def summarize_pending_entries(self, db: Session) -> None:
        entries = db.query(Entry).filter(Entry.summarized == False).all()
        for entry in entries:
            summary = self.llm_invoke(f"Summarize the following text:\n{entry.content}")
            entry.summary = summary.strip()
            entry.summarized = True
