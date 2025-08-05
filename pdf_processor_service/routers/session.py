from fastapi import Depends, APIRouter, Response

from utils.session import (
    delete_session,
    get_session_id,
    get_session_storage,
    SessionStorage,
    create_new_session,
    validate_session_id,
)
from models.session import SessionResponse

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/")
async def set_session(
    response: Response,
    session_storage: SessionStorage = Depends(get_session_storage),
    session_id: str = Depends(get_session_id),
    valid_session: bool = Depends(validate_session_id)
):
    if valid_session:
        delete_session(response, session_id, session_storage)
    new_session_id = create_new_session(response, session_storage=session_storage)
    return SessionResponse(session_id=new_session_id, valid_session=True)


@router.get("/")
async def get_session_status(
    session_id: str = Depends(get_session_id),
    valid_session: bool = Depends(validate_session_id)
):
    return SessionResponse(session_id=session_id, valid_session=valid_session)


@router.delete("/")
async def end_session(
    response: Response,
    session_id: str = Depends(get_session_id),
    session_storage: SessionStorage = Depends(get_session_storage)
):
    delete_session(response, session_id, session_storage)
    return {"message": "Session ended successfully"}
