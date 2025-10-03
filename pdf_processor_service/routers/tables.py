import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from utils.session import validate_session_doc_pair
from utils.proxy import load_or_create_extraction_job

router = APIRouter(prefix="/tables", tags=["tables"])
logger = logging.getLogger(__name__)


@router.get("/{doc_id}")
async def get_pdf_tables(
    doc_id: str,
    _validated: bool = Depends(validate_session_doc_pair),
    job = Depends(load_or_create_extraction_job)
):
    tables = job.get("data", {}).get("result", {}).get("tables")
    if tables is None:
        logger.error(f"Could not find 'tables' in job result for doc_id: {doc_id}")
        raise HTTPException(status_code=404, detail="Tables not found for this document.")
    return JSONResponse(content=tables)
