from fastapi import APIRouter

router = APIRouter()

@router.get('/status')
async def status():
    return {"llm_loaded": True, "docs_indexed": 342}
