from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from models.translate import TranslateResponse
from shared_utils.s3_utils import save_job, load_job, upload_fileobj

import os
import logging
import httpx
import io

import asyncio
from asyncio import Semaphore
import traceback
import json

router = APIRouter(prefix="/translation", tags=["translation"])
logger = logging.getLogger(__name__)

LLM_URL = os.getenv("LLM_URL")
TOKEN = os.getenv("LLM_API_TOKEN")

LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "5"))
semaphore = Semaphore(LLM_CONCURRENCY)

async def translate(prompt, source_lang=None, target_lang="English"):
    if source_lang:
        system_prompt = (
            f"You are a professional translator. Given the input language '{source_lang}', "
            f"think deeply and translate the following to '{target_lang}'. "
            f"Return only the translated text."
        )
    else:
        system_prompt = (
            f"You are a professional translator. Think deeply and translate the following to '{target_lang}'. "
            f"Detect the source language automatically and return only the translated text."
        )
    retries = 3
    delay = 2

    for attempt in range(retries):
        try:
            timeout = httpx.Timeout(60.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(
                    LLM_URL,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {TOKEN}"
                    },
                    json={
                        "model": "qwen2.5",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0
                    }
                )
        except httpx.ReadTimeout as e:
            logger.warning(f"ReadTimeout during LLM call (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise

    r.raise_for_status()
    try:
        response_json = r.json()
        return response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return None

async def safe_translate(entry, source_lang, target_lang):
    async with semaphore:
        original_text = entry.get("text") or entry.get("orig")
        entry_dict = dict(entry) if not isinstance(entry, dict) else entry

        if original_text:
            try:
                translated = await translate(original_text, source_lang=source_lang, target_lang=target_lang)
                entry_dict["translated_text"] = translated or "error"
            except Exception as e:
                logger.warning(f"Translation failed for text '{original_text[:30]}...': {e}")
                entry_dict["translated_text"] = "error"
        else:
            entry_dict["translated_text"] = "error"

        return entry_dict

@router.post("/", response_model=TranslateResponse)
async def doc_translate(payload: TranslateResponse = Body(...)):
    doc_id = payload.doc_id
    data = payload.docling
    source_lang = payload.source_lang
    target_lang = payload.target_lang or "English"

    logger.info(f"Received translation request: doc_id={doc_id}")
    save_job(doc_id=doc_id, job_data={}, status="processing", job_type="translation")

    try:
        # Translate texts concurrently
        text_tasks = [
            safe_translate(entry, source_lang, target_lang)
            for entry in data.texts
        ]
        data.texts = await asyncio.gather(*text_tasks)

        # Track all tasks and positions to reassign later
        all_table_tasks = []
        table_cell_refs = []  # (table_idx, cell_idx)

        for table_idx, table in enumerate(data.tables):
            table_data = table.get("data", {})
            table_cells = table_data.get("table_cells", [])
            for cell_idx, entry in enumerate(table_cells):
                all_table_tasks.append(safe_translate(entry, source_lang, target_lang))
                table_cell_refs.append((table_idx, cell_idx))

        translated_cells = await asyncio.gather(*all_table_tasks)

        # Reassign translated cells back to their correct table
        for (table_idx, cell_idx), translated_entry in zip(table_cell_refs, translated_cells):
            data.tables[table_idx]["data"]["table_cells"][cell_idx] = translated_entry

        json_bytes = io.BytesIO(json.dumps(data.model_dump()).encode('utf-8'))
        json_key = f"{doc_id}/translated.json"
        if not upload_fileobj(json_bytes, json_key, "application/json"):
            raise IOError(f"Failed to upload translated JSON to S3 for doc_id={doc_id}")

        save_job(doc_id=doc_id, job_data=data, status="completed", job_type="translation")
        logger.info(f"Translation completed: doc_id={doc_id}")

        return TranslateResponse(
            doc_id=doc_id,
            source_lang=source_lang,
            target_lang=target_lang,
            docling=data
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM API error during translation for doc_id={doc_id}: {e.response.status_code} - {e.response.text}")
        save_job(doc_id=doc_id, 
                 job_data={}, 
                 status="failed", 
                 job_type="translation"
                 )
        
        return JSONResponse(content={"error": f"LLM API error: {e.response.text}"}, status_code=e.response.status_code)
    
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse LLM response for doc_id={doc_id}: {e}")
        save_job(doc_id=doc_id, 
                 job_data={}, 
                 status="failed", 
                 job_type="translation"
                 )
        
        return JSONResponse(content={"error": "Failed to parse LLM response."}, status_code=500)
    
    except Exception as e:
        logger.error(f"Translation failed: doc_id={doc_id} - {e}")
        logger.error(traceback.format_exc())
        save_job(doc_id=doc_id, 
                 job_data={}, 
                 status="failed", 
                 job_type="translation"
                 )
        
        return JSONResponse(content={"error": "Translation failed."}, status_code=500)

@router.get("/status/{doc_id}")
async def get_status(doc_id: str):
    job = load_job(doc_id=doc_id, job_type="translation")
    if job is None:
        return JSONResponse(content={"status": "failed"}, status_code=404)
    return JSONResponse(
        content={"status": job["status"]},
        status_code=200 if job["status"] == "completed" else 202
    )