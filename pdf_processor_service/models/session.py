from pydantic import BaseModel


class SessionResponse(BaseModel):
    session_id: str
    valid_session: bool


class SessionDataResponse(BaseModel):
    session_id: str
    session_data: list[str]
