import os
import torch
import sys
sys.modules['torch.classes'] = None
import requests
import logging
import torch
from pathlib import Path
from PIL import Image
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

from transformers import AutoTokenizer, CLIPProcessor, CLIPModel
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_community.vectorstores import SQLiteVec
from langchain.text_splitter import TokenTextSplitter
from langchain_text_splitters import TokenTextSplitter
from langchain.schema import Document
import shutil
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError

# Load .env file
load_dotenv()

# AWS credentials from .env
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = "streamlit-pdfs"

# Initialize S3 client
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# -------------------------------
# Setup logging
logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

# Constants
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DB_FILE = "user_queries.sqlite"
TABLE_NAME = "sql_vect"
IMAGE_EMBEDDING_MODEL = "openai/clip-vit-base-patch32"
IMAGE_RESOLUTION_SCALE = 2.0

# Output folders
OUTPUT_IMAGE_DIR = Path("./extracted_images")
# DATA_DIR = Path("./data")
OUTPUT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
# DATA_DIR.mkdir(parents=True, exist_ok=True)

# Initialize components
tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)
embedding_model = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
clip_model = CLIPModel.from_pretrained(IMAGE_EMBEDDING_MODEL)
clip_processor = CLIPProcessor.from_pretrained(IMAGE_EMBEDDING_MODEL)
text_splitter = TokenTextSplitter(chunk_size=500, chunk_overlap=50)

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=PdfPipelineOptions(
                images_scale=IMAGE_RESOLUTION_SCALE,
                generate_page_images=True,
                generate_picture_images=True,
            )
        )
    }
)
pdf_chunker = HybridChunker(tokenizer=tokenizer, max_tokens=500)

# -----------------------------
# 1. YouTube Transcript Support
# -----------------------------
def get_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc == "youtu.be":
        return parsed_url.path.lstrip("/")
    if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
        query_params = parse_qs(parsed_url.query)
        if "v" in query_params:
            return query_params["v"][0]
        if parsed_url.path.startswith("/live/"):
            return parsed_url.path.split("/live/")[1].split("?")[0]
    raise ValueError("Invalid YouTube URL format.")

def get_transcript(video_url):
    try:
        video_id = get_video_id(video_url)
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([i['text'] for i in transcript_data])
    except (TranscriptsDisabled, NoTranscriptFound):
        return ""
    except Exception as e:
        return ""




def embed_youtube_transcript(video_url: str) -> str:
    transcript = get_transcript(video_url)
    if not transcript.strip():
        return f"⚠️ No transcript to embed for {video_url}"
    chunks = text_splitter.split_text(transcript)
    docs = [Document(page_content=chunk, metadata={"source": video_url, "type": "youtube-transcript"}) for chunk in chunks]
    try:
        SQLiteVec.from_documents(docs, embedding=embedding_model, table=TABLE_NAME, db_file=DB_FILE)
        return f"✅ Embedded {len(docs)} transcript chunks from: {video_url}"
    except Exception as e:
        return f"❌ Error embedding transcript: {e}"

# -----------------------------
# 2. Generic URL Text Scraper
# -----------------------------
def jinaai_readerapi_web_scrape_url(url: str, proxies: dict = None) -> str:
    try:
        response = requests.get("https://r.jina.ai/" + url, proxies=proxies)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"❌ Error scraping URL: {e}"

def embed_url_text_to_sqlite(text: str, source_url: str, org_id: int) -> str:
    try:
        chunks = text_splitter.split_text(text)
        docs = [Document(page_content=chunk, metadata={"source": source_url, "type": "text", "org_id": org_id}) for chunk in chunks]
        SQLiteVec.from_documents(docs, embedding=embedding_model, table=TABLE_NAME, db_file=DB_FILE)
        return f"✅ Stored {len(docs)} chunks from URL: {source_url}(org_id={org_id})"
    except Exception as e:
        return f"❌ Error embedding URL text: {e}"





def embed_pdf_to_sqlite(file_path: str, source_name: str,  org_id: int) -> str:
    try:
        # Clean image output directory
        if OUTPUT_IMAGE_DIR.exists():
            shutil.rmtree(OUTPUT_IMAGE_DIR)
        OUTPUT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

        # Upload PDF to S3
        try:
            with open(file_path, 'rb') as f:
                s3_key = f"{source_name}"
                s3_client.upload_fileobj(f, S3_BUCKET_NAME, s3_key, ExtraArgs={'ContentType': 'application/pdf'})
                _log.info(f"✅ Uploaded {source_name} to s3://{S3_BUCKET_NAME}/{s3_key}")
        except (BotoCoreError, NoCredentialsError, Exception) as aws_err:
            return f"❌ Failed to upload PDF to S3: {aws_err}"

        # Convert PDF
        conv_res = converter.convert(file_path)
        doc = conv_res.document

        # Save extracted page images locally
        for page_no, page in doc.pages.items():
            image_path = OUTPUT_IMAGE_DIR / f"{source_name}-page-{page_no}.png"
            page.image.pil_image.save(image_path, format="PNG")

        # Extract figures and tables
        pic_count, table_count = 0, 0
        for element, _ in doc.iterate_items():
            if isinstance(element, PictureItem):
                pic_count += 1
                pic_path = OUTPUT_IMAGE_DIR / f"{source_name}-picture-{pic_count}.png"
                element.get_image(doc).save(pic_path, format="PNG")
            elif isinstance(element, TableItem):
                table_count += 1
                table_path = OUTPUT_IMAGE_DIR / f"{source_name}-table-{table_count}.png"
                element.get_image(doc).save(table_path, format="PNG")

        # Text chunking
        chunks = list(pdf_chunker.chunk(doc))
        serialized_chunks = [pdf_chunker.serialize(c) for c in chunks if c]
        text_docs = [
            Document(page_content=chunk, metadata={"source": source_name, "type": "text",  "org_id": org_id})
            for chunk in serialized_chunks if chunk.strip()
        ]

        # Image embedding
        image_docs = []
        for element, _ in doc.iterate_items():
            if isinstance(element, PictureItem):
                pil_img = element.get_image(doc)
                inputs = clip_processor(images=pil_img, return_tensors="pt")
                with torch.no_grad():
                    image_embeds = clip_model.get_image_features(**inputs).cpu().numpy()[0]
                image_docs.append(Document(page_content="", metadata={"source": source_name, "type": "image","org_id": org_id}, embedding=image_embeds))

        all_docs = text_docs + image_docs
        if not all_docs:
            return f"❌ No chunks found to embed in {source_name}"

        SQLiteVec.from_documents(all_docs, embedding=embedding_model, table=TABLE_NAME, db_file=DB_FILE)
        return f"✅ Stored {len(all_docs)} chunks from PDF: {source_name} and uploaded to S3"

    except Exception as e:
        if OUTPUT_IMAGE_DIR.exists():
            try:
                shutil.rmtree(OUTPUT_IMAGE_DIR)
                OUTPUT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            except Exception as cleanup_error:
                _log.warning(f"⚠️ Failed to clean up image folder after error: {cleanup_error}")
        return f"❌ Error embedding PDF: {e}"

# ----------------------------------------
# 4. Smart Dispatcher (URL or YouTube)
# ----------------------------------------
def embed_from_url(url: str,org_id: int) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return embed_youtube_transcript(url,org_id)
    else:
        text = jinaai_readerapi_web_scrape_url(url)
        if not text or text.startswith("❌"):
            return text
        return embed_url_text_to_sqlite(text, url,org_id)





