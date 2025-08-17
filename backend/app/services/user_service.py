from fastapi import APIRouter, Depends
from .. import schemas, dependencies


router = APIRouter(tags=["user"], prefix="/user")



@router.get("/me", response_model=schemas.UserRead)
def read_me(current_user = Depends(dependencies.get_current_user)):
    return current_user
