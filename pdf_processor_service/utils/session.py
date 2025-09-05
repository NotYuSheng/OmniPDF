# Original code from https://github.com/duyixian1234/fastapi-redis-session
# Updated for package versions listed in requirements.txt

from typing import Callable, Generator
from uuid import uuid4

from fastapi import Depends, Request, Response, HTTPException

from shared_utils.redis_utils import (
    RedisDocumentFileList,
    RedisSetWithFlagExpiry,
    RedisPrefix,
    EXPIRY_DAY,
)

SESSION_COOKIE_NAME: str = "OmniPDFSession"


class SessionStorage(RedisSetWithFlagExpiry):
    def __init__(
        self,
        redis_client=None,
        prefix=RedisPrefix.SESSION_DOC_LIST,
        flag_prefix=RedisPrefix.SESSION_FLAG,
        default_expiry=EXPIRY_DAY,
    ):
        super().__init__(redis_client, prefix, flag_prefix, default_expiry)

    def generate_session(self) -> str:
        session_id = uuid4().hex
        while not self.client.set(
            self.flag_prefixed(session_id), 1, ex=self.flag_expiry, nx=True
        ):
            session_id = uuid4().hex
        return session_id


def get_session_storage() -> Generator[SessionStorage, None, None]:
    storage = SessionStorage()
    yield storage


def get_session_id(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE_NAME, "")
    return session_id


def create_new_session(
    response: Response, session_storage: SessionStorage = Depends(get_session_storage)
) -> str:
    session_id = session_storage.generate_session()
    response.set_cookie(SESSION_COOKIE_NAME, session_id, httponly=True)
    return session_id


def delete_session(
    response: Response,
    session_id: str = Depends(get_session_id),
    session_storage: SessionStorage = Depends(get_session_storage),
):
    if session_id:
        response.set_cookie(SESSION_COOKIE_NAME, session_id, httponly=True, max_age=0)
        del session_storage[session_id]


def validate_session_id(
    session_id: str = Depends(get_session_id),
    session_storage: SessionStorage = Depends(get_session_storage),
) -> bool:
    return session_id in session_storage


def validate_session_doc_pair(
    doc_id: str,
    session_id: str = Depends(get_session_id),
    session_storage: SessionStorage = Depends(get_session_storage),
    valid_session: bool = Depends(validate_session_id),
) -> bool:
    if valid_session:
        if session_storage.contains(session_id, doc_id):
            return True

    raise HTTPException(
        status_code=403,
        detail="User not authorized to access this document or invalid document ID",
    )


def get_doc_list_append_function(
    response: Response,
    session_id: str = Depends(get_session_id),
    session_storage: SessionStorage = Depends(get_session_storage),
) -> Callable[[str], None]:
    if not validate_session_id(session_id, session_storage):
        session_id = create_new_session(response, session_storage=session_storage)
    document_files = RedisDocumentFileList()

    def append_doc(doc_id: str, file_key: str, filename: str):
        session_storage.add(session_id, doc_id)
        document_files.init_doc_id(doc_id)
        document_files.add(doc_id, file_key)
        document_files.set_document_name(doc_id, filename)

    return append_doc


def get_doc_list_remove_function(
    session_id: str = Depends(get_session_id),
    session_storage: SessionStorage = Depends(get_session_storage),
) -> Callable[[str], None]:
    document_files = RedisDocumentFileList()

    def remove_doc(doc_id: str):
        session_storage.remove(session_id, doc_id)
        del document_files[doc_id]

    return remove_doc
