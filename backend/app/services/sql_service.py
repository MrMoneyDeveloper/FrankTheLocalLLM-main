from fastapi import APIRouter, Body, HTTPException, Depends
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.llms import Ollama

from ..db import engine
from . import CachedLLMService

router = APIRouter(tags=["sql"], prefix="/sql")


class SQLService(CachedLLMService):
    def __init__(self):
        super().__init__(Ollama(model="llama3"))
        self._db = SQLDatabase(engine)
        self._agent = create_sql_agent(llm=self._llm, db=self._db, agent_type="openai-tools")

    def query(self, query: str) -> dict:
        try:
            result = self._agent.invoke({"input": query})
            return {"result": result["output"]}
        except Exception as exc:  # pragma: no cover - runtime failure
            raise HTTPException(status_code=500, detail=str(exc))


def get_service() -> SQLService:
    return SQLService()


@router.post("/query")
def query_sql(query: str = Body(..., embed=True), service: SQLService = Depends(get_service)):
    return service.query(query)
