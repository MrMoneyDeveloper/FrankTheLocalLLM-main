
from fastapi import APIRouter, HTTPException, Body
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.llms import Ollama
from langchain_experimental.sql import SQLDatabaseChain

from ..db import engine

router = APIRouter(tags=["agent"], prefix="/agent")

_AGENT = None
_CHAIN = None

def get_agent():
    global _AGENT
    if _AGENT is None:
        db = SQLDatabase(engine)
        llm = Ollama(model="llama3")
        _AGENT = create_sql_agent(llm=llm, db=db, agent_type="openai-tools")
    return _AGENT


def get_chain():
    global _CHAIN
    if _CHAIN is None:
        db = SQLDatabase(engine)
        llm = Ollama(model="llama3")
        _CHAIN = SQLDatabaseChain.from_llm(llm, db, return_intermediate_steps=True)
    return _CHAIN


@router.post("/run")
def run_agent(command: str = Body(..., embed=True)):
    try:
        result = get_agent().invoke({"input": command})
        return {"response": result["output"]}
    except Exception as exc:  # pragma: no cover - runtime failure
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sql")
def run_sql(question: str = Body(..., embed=True)):
    try:
        result = get_chain().invoke({"question": question})
        return {
            "answer": result.get("result"),
            "sql": result.get("intermediate_steps", [{}])[-1].get("query") if result.get("intermediate_steps") else None,
        }
    except Exception as exc:  # pragma: no cover - runtime failure
        raise HTTPException(status_code=500, detail=str(exc))
