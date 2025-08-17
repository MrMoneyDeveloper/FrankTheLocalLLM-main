from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama

from . import CachedLLMService

router = APIRouter()

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "trivia.md"


class TriviaService(CachedLLMService):
    def __init__(self):
        super().__init__(Ollama())
        loader = UnstructuredMarkdownLoader(str(DATA_FILE))
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
        splits = splitter.split_documents(docs)
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = Chroma.from_documents(splits, embeddings)
        self._chain = RetrievalQA.from_chain_type(llm=self._llm, retriever=vectorstore.as_retriever())

    def ask(self, q: str) -> dict:
        try:
            answer = self._chain.run(q)
            return {"answer": answer}
        except Exception as exc:  # pragma: no cover - runtime failure
            raise HTTPException(status_code=500, detail=str(exc))


def get_service() -> TriviaService:
    return TriviaService()


@router.get("/trivia")
def ask_trivia(q: str = Query(..., description="Question for the trivia bot"), service: TriviaService = Depends(get_service)):
    return service.ask(q)
