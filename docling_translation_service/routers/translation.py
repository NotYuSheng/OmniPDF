from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from models.translate import TranslateResponse
from shared_utils.s3_utils import upload_fileobj
from shared_utils.job_status import save_job, load_job, JobType
from shared_utils.redis_utils import RedisDocumentFileList

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
document_files = RedisDocumentFileList()

# Default LLM configuration (base URL without endpoint path)
DEFAULT_LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("LLM_URL", "").replace("/v1/chat/completions", "")
DEFAULT_TOKEN = os.getenv("LLM_API_TOKEN")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL")

# OpenAI-compatible chat completions endpoint
CHAT_COMPLETIONS_ENDPOINT = "/v1/chat/completions"

LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "5"))
semaphore = Semaphore(LLM_CONCURRENCY)

# Language mapping to environment variable keys
# Maps detected/specified language names to their env var prefix
LANGUAGE_MAPPING = {
    "indonesian": "INDONESIAN",
    "bahasa indonesia": "INDONESIAN",
    "bahasa": "INDONESIAN",
    "malay": "MALAY",
    "bahasa melayu": "MALAY",
    "melayu": "MALAY",
    "chinese": "CHINESE",
    "mandarin": "CHINESE",
    "simplified chinese": "CHINESE",
    "traditional chinese": "CHINESE",
    "中文": "CHINESE",
}


def get_llm_config(language: str) -> dict:
    """
    Get LLM configuration based on the language.

    Args:
        language: The language name (e.g., "Indonesian", "Malay", "Chinese")

    Returns:
        Dictionary with 'base_url', 'model', and 'token' keys
    """
    # Normalize language name
    lang_key = language.lower().strip()

    # Check if we have a specific configuration for this language
    env_prefix = LANGUAGE_MAPPING.get(lang_key)

    if env_prefix:
        # Try to get language-specific config (base URL without endpoint)
        base_url = os.getenv(f"LLM_{env_prefix}_BASE_URL")
        model = os.getenv(f"LLM_{env_prefix}_MODEL")
        token = os.getenv(f"LLM_{env_prefix}_API_TOKEN")

        # If all configs exist, use them
        if base_url and model and token:
            logger.info(f"Using language-specific LLM config for {language}: {model}")
            return {"base_url": base_url, "model": model, "token": token}

    # Fallback to default configuration
    logger.info(f"Using default LLM config for {language}")
    return {"base_url": DEFAULT_LLM_BASE_URL, "model": DEFAULT_LLM_MODEL, "token": DEFAULT_TOKEN}


async def detect_language(text):
    """Detect the language of the given text using LLM."""
    system_prompt = (
        "You are a language detection expert. Identify the language of the following text. "
        "Return ONLY ONE of these exact language names:\n"
        "- Indonesian (for Bahasa Indonesia)\n"
        "- Malay (for Bahasa Melayu)\n"
        "- Chinese (for Mandarin, Simplified Chinese, or Traditional Chinese)\n"
        "- English\n"
        "- Spanish\n"
        "- French\n"
        "- German\n"
        "- Japanese\n"
        "- Korean\n"
        "- Arabic\n"
        "- Russian\n"
        "- Portuguese\n"
        "- Italian\n"
        "- Hindi\n"
        "Return ONLY the language name with no explanation or additional text."
    )

    # Use default LLM for language detection
    llm_config = {"base_url": DEFAULT_LLM_BASE_URL, "model": DEFAULT_LLM_MODEL, "token": DEFAULT_TOKEN}

    try:
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{llm_config['base_url']}{CHAT_COMPLETIONS_ENDPOINT}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {llm_config['token']}",
                },
                json={
                    "model": llm_config["model"],
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text[:500]},  # Use first 500 chars for detection
                    ],
                    "temperature": 0,
                },
            )
        r.raise_for_status()
        response_json = r.json()
        detected_lang = response_json["choices"][0]["message"]["content"].strip()
        logger.info(f"Detected language: {detected_lang}")
        return detected_lang
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return "Unknown"


async def translate(prompt, source_lang=None, target_lang="English"):
    """
    Translate text using language-specific LLM configuration.

    Args:
        prompt: Text to translate
        source_lang: Source language (used to select appropriate LLM)
        target_lang: Target language

    Returns:
        Translated text or None on failure
    """
    # Get appropriate LLM config based on source language
    # Try source language first, then target language, then default
    llm_config = None
    if source_lang:
        llm_config = get_llm_config(source_lang)
    if not llm_config or llm_config["base_url"] == DEFAULT_LLM_BASE_URL:
        # Fallback to target language config if source config not found
        llm_config = get_llm_config(target_lang)

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
                    f"{llm_config['base_url']}{CHAT_COMPLETIONS_ENDPOINT}",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {llm_config['token']}",
                    },
                    json={
                        "model": llm_config["model"],
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0,
                    },
                )
        except httpx.ReadTimeout as e:
            logger.warning(
                f"ReadTimeout during LLM call (attempt {attempt + 1}/{retries}): {e}"
            )
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
                translated = await translate(
                    original_text, source_lang=source_lang, target_lang=target_lang
                )
                entry_dict["translated_text"] = translated or "error"
            except Exception as e:
                logger.warning(
                    f"Translation failed for text '{original_text[:30]}...': {e}"
                )
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

    logger.info(f"Received translation request: doc_id={doc_id}, source_lang={source_lang}, target_lang={target_lang}")

    # Refresh document expiry to prevent cleanup during long translation
    document_files[doc_id]

    # Detect language if source_lang is "auto" or not specified
    detected_source_lang = source_lang
    if not source_lang or source_lang.lower() in ["auto", "auto-detect"]:
        # Get sample text for language detection (first text element)
        if data.texts and len(data.texts) > 0:
            sample_text = data.texts[0].get("text") or data.texts[0].get("orig", "")
            if sample_text:
                detected_source_lang = await detect_language(sample_text)
                logger.info(f"Auto-detected source language: {detected_source_lang}")
            else:
                detected_source_lang = "Unknown"
        else:
            detected_source_lang = "Unknown"

    save_job(doc_id=doc_id, job_data={}, status="processing", job_type=JobType.TRANSLATION, source_lang=detected_source_lang, target_lang=target_lang)

    try:
        # Translate texts concurrently
        text_tasks = [
            safe_translate(entry, source_lang, target_lang) for entry in data.texts
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
        for (table_idx, cell_idx), translated_entry in zip(
            table_cell_refs, translated_cells
        ):
            data.tables[table_idx]["data"]["table_cells"][cell_idx] = translated_entry

        json_bytes = io.BytesIO(json.dumps(data.model_dump()).encode("utf-8"))
        json_key = f"{doc_id}/translated.json"
        if not upload_fileobj(json_bytes, json_key, "application/json"):
            raise IOError(f"Failed to upload translated JSON to S3 for doc_id={doc_id}")
        document_files.add(doc_id, json_key)

        save_job(doc_id=doc_id, job_data=data.model_dump(), status="completed", job_type=JobType.TRANSLATION, source_lang=detected_source_lang, target_lang=target_lang)
        logger.info(f"Translation completed: doc_id={doc_id}")

        return TranslateResponse(
            doc_id=doc_id,
            source_lang=detected_source_lang,
            target_lang=target_lang,
            docling=data,
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM API error during translation for doc_id={doc_id}: {e.response.status_code} - {e.response.text}")
        save_job(doc_id=doc_id, 
                 job_data={}, 
                 status="failed", 
                 job_type=JobType.TRANSLATION
                 )
        
        return JSONResponse(content={"error": f"LLM API error: {e.response.text}"}, status_code=e.response.status_code)
    
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse LLM response for doc_id={doc_id}: {e}")
        save_job(doc_id=doc_id, 
                 job_data={}, 
                 status="failed", 
                 job_type=JobType.TRANSLATION
                 )
        
        return JSONResponse(content={"error": "Failed to parse LLM response."}, status_code=500)
    
    except Exception as e:
        logger.error(f"Translation failed: doc_id={doc_id} - {e}")
        logger.error(traceback.format_exc())
        save_job(doc_id=doc_id, 
                 job_data={}, 
                 status="failed", 
                 job_type=JobType.TRANSLATION
                 )
        
        return JSONResponse(content={"error": "Translation failed."}, status_code=500)


@router.get("/status/{doc_id}")
async def get_status(doc_id: str):
    job = load_job(doc_id=doc_id, job_type=JobType.TRANSLATION)
    if job is None:
        return JSONResponse(content={"status": "failed"}, status_code=404)
    return JSONResponse(
        content={"status": job["status"]},
        status_code=200 if job["status"] == "completed" else 202,
    )
