import logging
from io import BytesIO

from fastapi import APIRouter, HTTPException
from wordcloud import WordCloud

from shared_utils.s3_utils import load_job, upload_fileobj
from models.wordcloud import WordcloudResponse

router = APIRouter(prefix="/wordcloud", tags=["wordcloud"])

logger = logging.getLogger(__name__)

MAX_WORDS = 50


async def concat_text(doc_id: str) -> str:
    job = load_job(doc_id=doc_id, job_type="extraction")
    if not job:
        raise HTTPException(
            status_code=404, detail="Document not found or not processed yet"
        )
    if job.get("status") == "processing":
        raise HTTPException(
            status_code=202,
            detail="The document is still being processed. Please try again later.",
        )
    texts = job.get("data", {}).get("result", {}).get("texts", [])
    text_list = [entry.get("text", "") or entry.get("orig", "") for entry in texts]
    return "\n".join(text_list)


@router.get("/{doc_id}", response_model=WordcloudResponse)
async def get_wordcloud(
    doc_id: str,
):
    doc_text = await concat_text(doc_id)
    wordcloud = WordCloud(max_words=MAX_WORDS)
    words = wordcloud.process_text(doc_text)
    top_words = dict(sorted(words.items(), key=lambda item: item[1], reverse=True)[0:MAX_WORDS]).keys()

    wordcloud.generate_from_frequencies(words)
    with BytesIO() as img_file:
        img = wordcloud.to_image()
        img.save(img_file, format="PNG")
        img_file.seek(0)
        if not upload_fileobj(img_file, f"{doc_id}/wordcloud.png"):
            raise HTTPException(status_code=500, detail="failed to upload file")

    return WordcloudResponse(doc_id=doc_id, top_words=top_words)
