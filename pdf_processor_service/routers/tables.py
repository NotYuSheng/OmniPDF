import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse

from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_job

router = APIRouter(prefix="/tables", tags=["tables"])
logger = logging.getLogger(__name__)


@router.get("/{doc_id}")
async def get_pdf_tables(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job_or_reposnse = Depends(load_or_create_job)
):
    if isinstance(job_or_reposnse, Response):
        return job_or_reposnse
    
    tables = job_or_reposnse.get("data", {}).get("result", {}).get("tables")
    if tables is None:
        logger.error(f"Could not find 'tables' in job result for doc_id: {doc_id}")
        raise HTTPException(status_code=500, detail="A server error has occurred.")
    return JSONResponse(content=tables)
