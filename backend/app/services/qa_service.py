from fastapi import APIRouter, Body
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler
from langchain_community.llms import Ollama
import asyncio

from ..config import Settings

router = APIRouter(tags=["qa"], prefix="/qa")
settings = Settings()


def _chain():
    embeddings = OllamaEmbeddings(model=settings.embed_model)

    persist_dir = Path(__file__).resolve().parents[2] / "data" / "chroma"
    vs = Chroma(

        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
    retriever = vs.as_retriever(search_kwargs={"k": settings.retrieval_k})
    template = (
        "Answer using the context. Append markdown citations linking back to "
        "{source_path}#{line}.\n{question}"
    )
    prompt = PromptTemplate.from_template(template)
    llm = Ollama(model=settings.model, streaming=True)
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


@router.post("/stream")
async def qa_stream(question: str = Body(..., embed=True)):
    chain = _chain()
    handler = AsyncIteratorCallbackHandler()
    task = asyncio.create_task(chain.acall(question, callbacks=[handler]))

    async def event_generator():
        async for token in handler.aiter():
            yield {"event": "token", "data": token}
        await task
        yield {"event": "end", "data": ""}

    return EventSourceResponse(event_generator())
