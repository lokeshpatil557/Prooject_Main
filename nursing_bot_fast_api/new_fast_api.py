import sys
import uvicorn
sys.modules['torch.classes'] = None
from fastapi import Query
import time
import os
import tempfile
import re
from gemini_api import query_gemini
from langfuse_helper import langfuse_status, langfuse_trace_context, start_langfuse_observation
from guardrail import get_input_guard
from feedback import insert_feedback
from memo_zero import get_mem0_context, save_mem0_interaction, mem0_is_configured
import urllib.parse
from suggestion import get_most_frequent
from dashboard import (
    get_total_nurses, get_chat_query_count, get_most_active_nurse,
    get_avg_queries_per_user, get_most_frequent_questions,
    get_recent_active_nurses,
    get_upload_counts, get_total_uploads, 
    get_upload_trend, get_chat_trend, get_daily_upload_trend,
    get_inactive_nurses
)
from backend import (
    verify_user, register_user, get_relevant_docs,OrganisationNotFoundError, InvalidFAQFormatError,
    get_user_queries, store_user_query,get_org_id,add_faqs,get_all_faqs_by_org,update_organisation,
    store_uploaded_item,get_organisations,get_org_system_prompt,validate_faqs,replace_faqs,update_user_password,
    get_recent_uploaded_items, validate_admin_credentials, add_organisation, get_all_users_with_org,
    upsert_patient_record, get_patient_context_for_query, format_patient_context, list_patients_by_org,
    list_departments_by_org, get_patient_details_by_id, get_recent_user_messages,
    apply_patient_memory_updates
)
import pandas as pd
from admin_ingestion import embed_pdf_to_sqlite, embed_url_text_to_sqlite,embed_from_url
import datetime
from fastapi import FastAPI, HTTPException
from api_data_model import (
    LoginRequest, LoginResponse, RegisterNurseRequest, CreateOrganisationRequest,
    EditOrganisationRequest, ResetPasswordRequest, PatientUpsertRequest
)
from token_utils import create_access_token, get_current_user, admin_only, nurse_only, get_current_user_from_token
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File, Form, Depends
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import time
from typing import Optional, Any, Dict
import boto3
from botocore.exceptions import ClientError
# Logging setup (writes logs to ./logging/main.log)
import logging
from logging.handlers import RotatingFileHandler
import io
from pydantic import BaseModel
from typing import Dict, Any
from fastapi import UploadFile, File, Form, Body, WebSocket, WebSocketDisconnect, Depends
from jose import JWTError
import json
timestamp = datetime.now()
LOG_DIR = "logging"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("main_logger")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    # Console output - wrapped with UTF-8 stream if needed
    console_handler = logging.StreamHandler(stream=io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8'))
    console_handler.setFormatter(formatter)

    # File output with UTF-8 encoding
    file_handler = RotatingFileHandler(
        filename=os.path.join(LOG_DIR, "main.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"  # ← Ensures emoji and Unicode characters are supported
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


processing_status = {}
S3_BUCKET_NAME = "streamlit-pdfs"  # Your bucket name

# You might already have this set up
s3_client = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

def generate_presigned_url(file_name: str) -> str:
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": file_name},
            ExpiresIn=3600  # 1 hour valid
        )
    except ClientError as e:
        return "#"  # Fallback in case of error




# app = FastAPI(


# app = FastAPI(
#     root_path="/backend-api",
#     docs_url="/docs",
#     redoc_url=None,
#     openapi_url="/openapi.json"
# )


app = FastAPI(
    title="Lokesh API",   # 👈 your change
    root_path="/backend-api",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json"
)


#Allow all origins (for development/testing only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ Unsafe for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)







def process_upload_task(source_type: str, identifier: str, file_path: Optional[str] = None,org_id: int = None):
    try:
        logger.info(f"🔄 Started: {source_type} | {identifier}")
        time.sleep(3)  # Simulate long task

        if source_type == "pdf":
            logger.info(f"📄 Processing PDF file at: {file_path}")
            process_pdf_upload(file_path, identifier, org_id)  # ✅ Use your existing function

        elif source_type == "url":
            logger.info(f"🌐 Processing URL: {identifier}")
            process_url_upload(identifier,org_id)  # ✅ Use your existing function

        processing_status[identifier] = "completed"
        logger.info(f"✅ Completed: {identifier}")

    except Exception as e:
        processing_status[identifier] = "failed"
        logger.error(f"❌ Failed: {identifier} | {e}")


def format_docs_with_links(docs_with_source):
    formatted = []
    for content, source in docs_with_source:
        if source.startswith("http"):
            source_md = f"[Link]({source})"
        elif source.lower().endswith(".pdf"):
            filename = os.path.basename(source)
            #url = f"{FASTAPI_BASE_URL}/{urllib.parse.quote(filename)}"
            url= generate_presigned_url(filename)
            source_md = f"[{filename}]({url})"
        
        else:
            source_md = source
        formatted.append(f"{content}\n(Source: {source_md})")
    return "\n\n".join(formatted)


def process_pdf_upload(tmp_path: str, filename: str, org_id: int):
    try:
        embed_pdf_to_sqlite(tmp_path, source_name=filename, org_id=org_id)
        store_uploaded_item(filename, "pdf", org_id)
        logger.info(f"✅ PDF '{filename}' processed successfully.")
    except Exception as e:
        logger.error(f"❌ PDF processing failed for '{filename}': {e}")
    finally:
        os.remove(tmp_path)
        logger.debug(f"Temporary file '{tmp_path}' removed.")

def process_url_upload(url: str, org_id: int):
    try:
        text = embed_from_url(url,org_id)
        if text.startswith("❌"):
            raise ValueError(text)

        embed_url_text_to_sqlite(text, source_url=url,org_id=org_id)
        store_uploaded_item(url, "url", org_id)
        logger.info(f"✅ URL '{url}' processed successfully.")
    except Exception as e:
        logger.error(f"❌ URL processing failed for '{url}': {e}")




def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Nursing Chatbot API",
        version="1.0.0",
        description="API for Admins and Nurses with JWT Bearer authentication.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi





@app.get("/lokesh")
def lokesh_api():
    return {"message": "Lokesh API working"}


@app.get("/lokesh-add")
def add_numbers(a: int, b: int):
    return {"result": a + b}



@app.post("/login/nurse", response_model=LoginResponse)
def login_nurse(data: LoginRequest):
    """
    Nurse Login Endpoint

    Validates nurse credentials against the `users` table.
    If successful:
    - Fetches the linked organisation name via `org_id`.
    - Generates a JWT containing username, role, and org info.
    - Returns a welcome message in the username field: "Welcome <username> (<organisation>)".

    Returns:
    - success (bool)
    - username (str): "Welcome John (Nursing)"
    - role (str): "nurse"
    - access_token (str): signed JWT token
    - token_type (str): always "bearer"
    """
    try:
        logger.info(f"🔐 Nurse login attempt: username={data.username}")

        user = verify_user(data.username, data.password)
        if not user:
            logger.warning(f"⚠️ Invalid nurse login attempt: username={data.username}")
            raise HTTPException(status_code=401, detail="Invalid nurse credentials")

        # ✅ create real JWT token
        access_token = create_access_token(
            data={
                "sub": user["username"],
                "role": "nurse",
                "org_id": user["org_id"],
                "organisation_name": user["organisation_name"]
            }
        )

        welcome_msg = f"Welcome, {user['username']} to ({user['organisation_name']})"

        logger.info(f"✅ Nurse login successful: username={data.username}, org={user['organisation_name']}")
        return LoginResponse(
            success=True,
            username=welcome_msg,
            role="nurse",
            access_token=access_token,
            token_type="bearer"
        )

    except HTTPException:
        # already logged invalid attempt
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during nurse login: username={data.username} - {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



@app.post("/login/admin", response_model=LoginResponse)
def login_admin(data: LoginRequest):
    """
    Admin Login Endpoint

    Allows an administrator to log in using their username and password. If the 
    credentials are valid, a JWT access token is generated and returned along with 
    the admin's username and role. This token can then be used for authenticated access 
    to protected admin routes.

    Request:
    - username: Admin's login username.
    - password: Admin's password.

    Response:
    - success: Boolean indicating login status.
    - username: The admin's username.
    - role: "admin".
    - access_token: JWT access token for authentication.
    - token_type: "bearer".

    Returns:
    - 200 OK: If login is successful.
    - 401 Unauthorized: If the credentials are invalid.
    - 500 Internal Server Error: If an unexpected error occurs.

    Logs:
    - Logs all login attempts (success and failure).
    - Logs errors with descriptive messages for easier debugging.
    """
    logger.info(f"🔐 Attempting admin login for user: {data.username}")
    try:
        if validate_admin_credentials(data.username, data.password):
            access_token = create_access_token(
                data={"sub": data.username, "role": "admin"}
            )
            logger.info(f"✅ Admin login successful: {data.username}")
            # return {"access_token": access_token, "token_type": "bearer"}
            return LoginResponse(success=True, username=data.username, role="admin", access_token=access_token, token_type="bearer")
        logger.warning(f"⚠️ Invalid admin login attempt: {data.username}")
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    except Exception as e:
        logger.error(f"❌ Exception during admin login for user {data.username}: {e}")
        raise HTTPException(status_code=401, detail="Invalid admin credentials")


@app.get("/faq/all", dependencies=[Depends(nurse_only)])
def get_all_faqs(current_user: dict = Depends(get_current_user_from_token)) -> Dict[str, Any]:
    """
    Return ALL FAQs for the current user's organisation, grouped by category.
    """
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organisation not found in token")

    return get_all_faqs_by_org(org_id)



@app.get("/admin/dashboard/total-nurses", dependencies=[Depends(admin_only)])
def total_nurses():
    """
    Get Total Number of Nurses (Admin Only)

    This endpoint returns the total number of nurses registered in the system.
    It is accessible only to authenticated admin users (authorization required).

    Authorization:
    - Requires admin role via `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object with the total number of nurses.
      Example: { "total_nurses": 42 }

    Errors:
    - 500 Internal Server Error: If an error occurs while retrieving the data.

    Logs:
    - Logs the request and the number of nurses retrieved.
    - Logs any exceptions that occur during the process.
    """
    logger.info("📊 Admin requested total number of nurses.")
    try:
        total = get_total_nurses()
        logger.info(f"✅ Total nurses retrieved: {total}")
        return {"total_nurses": total}
    except Exception as e:
        logger.error(f"❌ Failed to fetch total nurses: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving total nurses")



@app.get("/admin/dashboard/chat-query-count", dependencies=[Depends(admin_only)])
def chat_query_count():
    """
    Get Total Chat Query Count (Admin Only)

    This endpoint retrieves the total number of chat queries submitted by users.
    It is intended for admin use only and provides analytics for system usage.

    Authorization:
    - Requires admin privileges via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object with the total number of chat queries.
      Example: { "total_queries": 128 }

    Errors:
    - 500 Internal Server Error: If an error occurs while fetching the data.

    Logs:
    - Logs the request and the total retrieved.
    - Captures and logs any errors encountered during processing.
    """
    logger.info("📊 Admin requested total chat query count.")
    try:
        total = get_chat_query_count()
        logger.info(f"✅ Total chat queries retrieved: {total}")
        return {"total_queries": total}
    except Exception as e:
        logger.error(f"❌ Failed to fetch chat query count: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving chat query count")



@app.get("/admin/dashboard/total-uploads", dependencies=[Depends(admin_only)])
def total_uploads():
    """
    Get Total Uploads Count (Admin Only)

    This endpoint returns the total number of file or document uploads performed
    in the system. It is restricted to admin users and is typically used for 
    monitoring system activity via the admin dashboard.

    Authorization:
    - Requires admin privileges via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object with the total number of uploads.
      Example: { "total_uploads": 74 }

    Errors:
    - 500 Internal Server Error: If an error occurs while retrieving the upload count.

    Logs:
    - Logs the admin's request and the total uploads retrieved.
    - Logs detailed error messages if something goes wrong.
    """
    logger.info("📁 Admin requested total uploads count.")
    try:
        total = get_total_uploads()
        logger.info(f"✅ Total uploads retrieved: {total}")
        return {"total_uploads": total}
    except Exception as e:
        logger.error(f"❌ Failed to fetch total uploads: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving total uploads")

@app.get("/admin/dashboard/most-active-nurse", dependencies=[Depends(admin_only)])
def most_active_nurse():
    """
    Get Most Active Nurse (Admin Only)

    This endpoint identifies and returns the nurse who has submitted the highest
    number of chat queries or interactions within the system. It is useful for 
    administrative insight into staff activity and engagement.

    Authorization:
    - Accessible only by admin users via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object containing the most active nurse's username
      and the number of queries they have submitted.
      Example: { "nurse": "nurse_jane", "query_count": 57 }

    Errors:
    - 500 Internal Server Error: If an error occurs while fetching the data.

    Logs:
    - Logs the request for most active nurse data.
    - Logs the result and any exceptions encountered.
    """
    logger.info("📊 Admin requested the most active nurse data.")
    try:
        nurse, count = get_most_active_nurse()
        logger.info(f"✅ Most active nurse: {nurse} with {count} queries.")
        #return {"nurse": nurse, "query_count": count}
        return {"nurse": str(nurse), "query_count": int(count)}
    except Exception as e:
        logger.error(f"❌ Failed to fetch most active nurse: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving most active nurse data")





@app.get("/admin/dashbaord/avg-queries", dependencies=[Depends(admin_only)])
def avg_queries():
    """
    Get Average Queries per Nurse (Admin Only)

    This endpoint calculates and returns the average number of chat queries 
    submitted by each nurse in the system. It provides admins with insight 
    into the overall activity and engagement levels of nursing staff.

    Authorization:
    - Requires admin privileges via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object with the average number of queries per nurse.
      Example: { "average_queries_per_nurse": 12.5 }

    Errors:
    - 500 Internal Server Error: If an error occurs while retrieving the data.

    Logs:
    - Logs the request for average queries.
    - Logs the computed average or any exceptions encountered during processing.
    """

    logger.info("📈 Admin requested average queries per nurse.")
    try:
        avg = get_avg_queries_per_user()
        logger.info(f"✅ Retrieved average queries per nurse: {avg}")
        return {"average_queries_per_nurse": avg}
    except Exception as e:
        logger.error(f"❌ Failed to fetch average queries: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving average queries per nurse")


@app.get("/admin/dashboard/most-frequent-questions", dependencies=[Depends(admin_only)])
def most_frequent_questions():
    """
    Get Most Frequently Asked Questions (Admin Only)

    This endpoint returns a list of the most frequently asked questions (FAQs)
    based on chat query history. Each item in the list includes the question text
    and the number of times it has been asked. It helps admins analyze common 
    user concerns and optimize support content.

    Authorization:
    - Requires admin access via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object with a list of FAQs.
      Example:
      {
        "faq": [
          { "question": "How do I reset my password?", "count": 15 },
          { "question": "What are the clinic hours?", "count": 12 }
        ]
      }

    Errors:
    - 500 Internal Server Error: If an error occurs while retrieving the data.

    Logs:
    - Logs the request and the number of frequent questions retrieved.
    - Logs detailed error messages in case of failure.
    """
    logger.info("📊 Admin requested most frequent questions.")
    try:
        questions = get_most_frequent_questions()
        logger.info(f"✅ Retrieved {len(questions)} frequent questions.")
        return {"faq": [{"question": q, "count": c} for q, c in questions]}
    except Exception as e:
        logger.error(f"❌ Failed to fetch most frequent questions: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving most frequent questions.")



@app.get("/admin/dashboard/recent-active-nurses", dependencies=[Depends(admin_only)])
def recent_active_nurses():
    """
    Get Recently Active Nurses (Admin Only)

    This endpoint retrieves a list of nurses who have been recently active in the system,
    typically based on their last interaction or login time. It helps admins monitor
    engagement and identify active staff members.

    Authorization:
    - Restricted to admin users via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object containing a list of nurses with their usernames
      and timestamps of their most recent activity.
      Example:
      {
        "recent_active": [
          { "username": "nurse_amy", "last_active": "2025-06-29T14:32:00Z" },
          { "username": "nurse_john", "last_active": "2025-06-29T12:10:00Z" }
        ]
      }

    Errors:
    - 500 Internal Server Error: If an error occurs while retrieving the data.

    Logs:
    - Logs the admin request and number of active nurses retrieved.
    - Logs detailed error information if something goes wrong.
    """

    logger.info("📋 Admin requested list of recently active nurses.")
    try:
        data = get_recent_active_nurses()
        logger.info(f"✅ Retrieved {len(data)} recently active nurses.")
        return {"recent_active": [{"username": x[0], "last_active": x[1]} for x in data]}
    except Exception as e:
        logger.error(f"❌ Failed to fetch recent active nurses: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving recent active nurses.")


@app.get("/admin/dashboard/upload-counts", dependencies=[Depends(admin_only)])
def upload_counts():
    """
    Get Upload Counts by Category (Admin Only)

    This endpoint retrieves the count of uploads grouped by category or type 
    (e.g., pdf, url). It helps admins monitor system usage 
    and understand the distribution of uploaded content.

    Authorization:
    - Accessible only to admin users via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object containing counts per category.
      Example:
     {
        "pdf": 9,
        "url": 31
    }

    Errors:
    - 500 Internal Server Error: If an error occurs while fetching the upload data.

    Logs:
    - Logs the admin's request and a success message upon retrieval.
    - Logs any exceptions with full error detail.
    """
    logger.info("📦 Admin requested upload counts.")
    try:
        data = get_upload_counts()
        logger.info("✅ Successfully retrieved upload counts.")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to fetch upload counts: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving upload counts.")


@app.get("/admin/dashboard/upload-trend", dependencies=[Depends(admin_only)])
def upload_trend():
    """
    Get Upload Trend Over Time (Admin Only)

    This endpoint provides time-series data representing the trend of uploads over
    a specified period (e.g., daily, weekly, or monthly). It helps administrators 
    visualize content submission patterns and analyze activity levels over time.

    Authorization:
    - Restricted to admin users via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object containing date-wise or time-period-wise upload data.
      Example:
      {
        "trend": [
          { "date": "2025-06-25", "count": 5 },
          { "date": "2025-06-26", "count": 8 },
          { "date": "2025-06-27", "count": 3 }
        ]
      }

    Errors:
    - 500 Internal Server Error: If an error occurs while retrieving the upload trend.

    Logs:
    - Logs the admin request and success status.
    - Captures and logs any exceptions that occur during data retrieval.
    """
    logger.info("📈 Admin requested upload trend data.")
    try:
        data = get_upload_trend()
        logger.info("✅ Successfully retrieved upload trend data.")
        return data
    except Exception as e:
        logger.error(f"❌ Failed to fetch upload trend: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving upload trend data.")


@app.get("/admin/dashboard/chat-trend", dependencies=[Depends(admin_only)])
def chat_trend():
    """
    Get Chat Query Trend Over Time (Admin Only)

    This endpoint provides a time-based trend of chat queries made by users (e.g., nurses).
    It helps administrators monitor usage patterns and identify peak periods of user activity.

    Authorization:
    - Restricted to admin users via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object containing date-wise chat query counts.
      Example:
      {
        "trend": [
          { "date": "2025-06-25", "count": 10 },
          { "date": "2025-06-26", "count": 15 },
          { "date": "2025-06-27", "count": 9 }
        ]
      }

    Errors:
    - 500 Internal Server Error: If an error occurs during data retrieval.

    Logs:
    - Logs the admin's request for chat trends.
    - Logs a success message upon retrieval.
    - Logs any exceptions with detailed error information.
    """
    logger.info("📊 Admin requested chat trend data.")
    try:
        data = get_chat_trend()
        logger.info("✅ Successfully retrieved chat trend data.")
        return data
    except Exception as e:
        logger.error(f"❌ Error fetching chat trend: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving chat trend data.")

@app.get("/admin/dashboard/daily-upload-trend", dependencies=[Depends(admin_only)])
def daily_upload_trend():
    """
    Get Daily Upload Trend (Admin Only)

    This endpoint returns a day-by-day trend of uploads to the system.
    It enables admins to track how upload activity changes over time and 
    identify peak or low engagement periods.

    Authorization:
    - Access restricted to admin users via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object representing daily upload counts.
      Example:
      {
        "trend": [
          { "date": "2025-06-25", "count": 7 },
          { "date": "2025-06-26", "count": 12 },
          { "date": "2025-06-27", "count": 5 }
        ]
      }

    Errors:
    - 500 Internal Server Error: If an error occurs while retrieving the data.

    Logs:
    - Logs the request for daily upload trend.
    - Logs successful retrieval or captures detailed error info on failure.
    """
    logger.info("📅 Admin requested daily upload trend data.")
    try:
        data = get_daily_upload_trend()
        logger.info("✅ Successfully retrieved daily upload trend.")
        return data
    except Exception as e:
        logger.error(f"❌ Error fetching daily upload trend: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving daily upload trend data.")

@app.get("/admin/dashboard/inactive-nurses", dependencies=[Depends(admin_only)])
def inactive_nurses():
    logger.info("🛑 Admin requested list of inactive nurses.")
    try:
        nurses = get_inactive_nurses()
        logger.info("✅ Successfully retrieved inactive nurses data.")
        return {"inactive_nurses": nurses}
    except Exception as e:
        logger.error(f"❌ Error fetching inactive nurses: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving inactive nurses.")





@app.post("/admin/manage-content/upload-pdf", dependencies=[Depends(admin_only)])
async def upload_pdf(background_tasks: BackgroundTasks, org_id: int = Form(...),file: UploadFile = File(...)):
    """
    Upload and Process PDF File (Admin Only)

    This endpoint allows an admin to upload a PDF file. The file is temporarily saved 
    on the server, and a background task is triggered to process the PDF (e.g., extracting 
    text, indexing, storing metadata, etc.).

    Authorization:
    - Restricted to admin users via the `admin_only` dependency.

    Request:
    - multipart/form-data with a single `file` field (PDF format expected).

    Response:
    - 200 OK: Acknowledges that the file was received and background processing has started.
      Example:
      {
        "status": "processing",
        "message": "✅ File 'guidelines.pdf' uploaded. Processing started in background."
      }

    Errors:
    - 500 Internal Server Error: If the file cannot be saved or the background task fails to start.

    Notes:
    - The file is stored temporarily using Python’s `tempfile` module.
    - Processing is offloaded to a background task to keep the request non-blocking.

    Logs:
    - Logs include the file name, temporary path, and status of the background task or any errors.
    """
    logger.info(f"📤 Admin initiated PDF upload: {file.filename}")
    try:
        suffix = os.path.splitext(file.filename)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        logger.info(f"📁 Temporary file created at {tmp_path}")

        # Run background task
        processing_status[file.filename] = "processing" 
        #background_tasks.add_task(process_pdf_upload, tmp_path, file.filename)
        background_tasks.add_task(process_upload_task, "pdf", file.filename, tmp_path,org_id)
        logger.info(f"⚙️ Background task started for PDF: {file.filename}")

        return {
            "status": "processing",
            "message": f"✅ File '{file.filename}' uploaded. Processing started in background."
        }

    except Exception as e:
        logger.error(f"❌ Error uploading or processing PDF '{file.filename}': {e}")
        processing_status[file.filename] = "failed" 
        raise HTTPException(status_code=500, detail="Failed to process uploaded PDF.")


@app.post("/admin/manage-content/upload-url", dependencies=[Depends(admin_only)])
async def upload_url(background_tasks: BackgroundTasks, org_id: int = Form(...),url: str = Form(...)):
    """
    Submit URL for Background Processing (Admin Only)

    This endpoint allows an admin to submit a URL that points to an external resource 
    (e.g., a PDF or web page) for processing. The processing task is offloaded to a 
    background worker to avoid blocking the request.

    Authorization:
    - Restricted to admin users via the `admin_only` dependency.

    Request:
    - Form data containing a `url` field (string) that should be processed.

    Response:
    - 200 OK: Indicates that the URL was received and the background task has been initiated.
      Example:
      {
        "status": "processing",
        "message": "✅ URL submitted. Processing started in background."
      }

    Errors:
    - 500 Internal Server Error: If the background task cannot be started due to an exception.

    Notes:
    - The background task (`process_url_upload`) may download and process the file or extract data.
    - Ideal for uploading from cloud storage links or external document repositories.

    Logs:
    - Logs the URL submission, success of background task initiation, and any exceptions.
    """
    logger.info(f"🌐 Admin submitted URL for upload: {url}")
    try:
        processing_status[url] = "processing"
        #background_tasks.add_task(process_url_upload,"url", url)
        background_tasks.add_task(process_upload_task, "url", url,None, org_id)
        logger.info(f"⚙️ Background task started for URL: {url}")

        return {
            "status": "processing",
            "message": f"✅ URL submitted. Processing started in background."
        }

    except Exception as e:
        logger.error(f"❌ Error processing submitted URL '{url}': {e}")
        processing_status[url] = "failed"
        raise HTTPException(status_code=500, detail="Failed to process submitted URL.")




@app.get("/admin/manage-content/status", dependencies=[Depends(admin_only)])
async def get_status(id: str):
    """
    ✅ Check Processing Status of Uploaded Content (Admin Only)

    This endpoint allows an admin to check the background processing status of an uploaded
    PDF or a submitted URL. It returns whether the file or URL is still being processed,
    has completed successfully, or failed.

    Authorization:
    - Restricted to admin users via the `admin_only` dependency.

    Query Parameters:
    - `id` (str): The unique identifier for the content you want to check the status for.
      - For PDFs: This is usually the filename (e.g., `myfile.pdf`)
      - For URLs: This is the original URL submitted.

    Response:
    - 200 OK: Returns the processing status of the requested item.
      Example:
      ```json
      {
        "id": "myfile.pdf",
        "status": "processing"
      }
      ```

    Possible Status Values:
    - "processing": Background task is still running
    - "completed": Processing finished successfully
    - "failed": There was an error during processing
    - "not_found": No status entry found for the given ID

    Notes:
    - Make sure to use the exact `id` returned or used when uploading the PDF or submitting the URL.
    - This endpoint does not trigger any processing—it only checks status.
    """
    return {
        "id": id,
        "status": processing_status.get(id, "not_found")
    }


# ✅ Recent Uploads Endpoint
# @app.get("/admin/manage-content/recent-uploads", dependencies=[Depends(admin_only)])
# def recent_uploads():
#     """
#     Get List of Recently Uploaded Content (Admin Only)

#     This endpoint returns a list of the most recent content items uploaded to the system 
#     by the admin. It includes the name, type (e.g., PDF, URL), and timestamp of each upload.

#     Authorization:
#     - Access restricted to admin users via the `admin_only` dependency.

#     Response:
#     - 200 OK: Returns a JSON object with a list of recent uploads.
#       Example:
#       {
#         "recent_uploads": [
#           {
#             "name": "guidelines.pdf",
#             "type": "pdf",
#             "timestamp": "2025-06-29T14:45:00"
#           },
#           {
#             "name": "https://example.com/info",
#             "type": "url",
#             "timestamp": "2025-06-29T13:10:00"
#           }
#         ]
#       }

#     Errors:
#     - 500 Internal Server Error: If there is a failure during data retrieval.

#     Notes:
#     - This is useful for auditing and quick access to the latest uploads.
#     - Results are typically ordered by timestamp (most recent first).

#     Logs:
#     - Logs the request initiation, number of items returned, and any error encountered.
#     """
#     logger.info("📥 Admin requested recent uploaded items.")
#     try:
#         items = get_recent_uploaded_items()
#         logger.info(f"✅ Retrieved {len(items)} recent uploads.")
#         return {
#             "recent_uploads": [
#                 {"name": name, "type": item_type, "timestamp": timestamp}
#                 for name, item_type, timestamp in items
#             ]
#         }
#     except Exception as e:
#         logger.error(f"❌ Error retrieving recent uploads: {e}")
#         raise HTTPException(status_code=500, detail="Failed to retrieve recent uploads.")




@app.get("/admin/manage-content/recent-uploads", dependencies=[Depends(admin_only)])
def recent_uploads():
    """
    Get List of Recently Uploaded Content (Admin Only)

    This endpoint returns a list of the most recent content items uploaded to the system,
    including the organisation that uploaded each item.

    Authorization:
    - Access restricted to admin users via the `admin_only` dependency.

    Response:
    - 200 OK: Returns a JSON object with a list of recent uploads.
      Example:
      {
        "recent_uploads": [
          {
            "name": "guidelines.pdf",
            "type": "pdf",
            "timestamp": "2025-06-29T14:45:00",
            "organisation_name": "Health Department"
          },
          {
            "name": "https://example.com/info",
            "type": "url",
            "timestamp": "2025-06-29T13:10:00",
            "organisation_name": "Education Board"
          }
        ]
      }

    Errors:
    - 500 Internal Server Error: If there is a failure during data retrieval.

    Notes:
    - Results are ordered by timestamp (most recent first).
    - Useful for auditing and quick access to the latest uploads.

    Logs:
    - Logs the request initiation, number of items returned, and any errors.
    """
    logger.info("📥 Admin requested recent uploaded items (with organisation info).")
    try:
        items = get_recent_uploaded_items()
        logger.info(f"✅ Retrieved {len(items)} recent uploads.")
        return {
            "recent_uploads": [
                {
                    "name": name,
                    "type": item_type,
                    "timestamp": timestamp,
                    "organisation_name": org_name if org_name else "Unknown"
                }
                for name, item_type, timestamp, org_name in items
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error retrieving recent uploads: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent uploads.")





@app.post("/admin/manage-users/register-nurse", dependencies=[Depends(admin_only)])
def register_nurse(data: RegisterNurseRequest):
    """
    Register a New Nurse Account (Admin Only)

    This endpoint allows an admin to create a new nurse user account by providing 
    a username and password. It ensures that only authorized administrators can 
    register nurses into the system.

    Authorization:
    - Access is restricted to admin users via the `admin_only` dependency.

    Request Body:
    - `username` (str): The desired username for the nurse.
    - `password` (str): The password for the nurse account.
    = `org_id`  (int) : organisation id

    Example:
    ```json
    {
      "username": "nurse.anne",
      "password": "securePass123",
      "org_id": 1
    }
    ```

    Response:
    - 200 OK: Nurse successfully registered.
      ```json
      {
        "status": "success",
        "message": "Nurse account created successfully."
      }
      ```

    - 409 Conflict: Username already exists or registration criteria not met.
    - 500 Internal Server Error: Unhandled exceptions during processing.

    Notes:
    - Internally calls `register_user()` to handle user creation logic.
    - Logs both successful and failed registration attempts for auditing.

    Logs:
    - Records username attempted, result, and any errors encountered.
    """
    logger.info(f"📝 Admin attempting to register nurse: {data.username} for org_id={data.org_id}")
    try:
        success, message = register_user(data.username, data.password, data.org_id)
        if success:
            logger.info(f"✅ Nurse registered successfully: {data.username} (Org ID: {data.org_id})")
            return {"status": "success", "message": "Nurse registered successfully"}
        else:
            logger.warning(f"⚠️ Nurse registration failed for {data.username}: {message}")
            raise HTTPException(status_code=409, detail="User Already Exists")
    except HTTPException as http_exc:
        # ✅ re-raise HTTPExceptions so FastAPI handles them
        raise http_exc
    except Exception as e:
        logger.error(f"❌ Unexpected error during nurse registration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get("/admin/manage-users/list", dependencies=[Depends(admin_only)])
def list_users():
    """
    Get List of All Users with Organisation Info (Admin Only)

    This endpoint returns all registered users along with the organisation they belong to.

    Response Example:
    {
      "users": [
        {
          "username": "nurse.anne",
          "organisation_name": "Health Department"
        },
        {
          "username": "doctor.john",
          "organisation_name": "City Hospital"
        }
      ]
    }

    Errors:
    - 500 Internal Server Error: If there is a failure during data retrieval.
    """
    logger.info("📋 Admin requested list of all users with organisation info.")
    try:
        users = get_all_users_with_org()
        logger.info(f"✅ Retrieved {len(users)} users.")
        return {"users": users}
    except Exception as e:
        logger.error(f"❌ Error retrieving users list: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users list.")



@app.put("/admin/manage-users/reset-password", dependencies=[Depends(admin_only)])
def reset_user_password(data: ResetPasswordRequest):
    logger.info(f"🔐 Admin attempting to reset password for user: {data.username} in organisation: {data.organisation_name}")
    try:
        success, message = update_user_password(data.username, data.new_password, data.organisation_name)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        logger.info(f"✅ Password updated for user: {data.username} in {data.organisation_name}")
        return {"status": "success", "message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resetting password for {data.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")


@app.post("/admin/patient/upsert", dependencies=[Depends(admin_only)])
def upsert_patient(data: PatientUpsertRequest):
    """
    Create or update patient + treatments in the same user_queries.sqlite database.
    """
    try:
        payload = data.model_dump()
        treatments = payload.pop("treatments", None)
        if treatments is not None:
            payload["treatments"] = [item.model_dump() for item in treatments]

        patient_id = upsert_patient_record(**payload)
        return {
            "status": "success",
            "message": "Patient data saved successfully.",
            "patient_id": patient_id,
            "patient_code": data.patient_code,
            "department": data.department,
        }
    except Exception as e:
        logger.error(f"❌ Error while upserting patient '{data.patient_code}': {e}")
        raise HTTPException(status_code=500, detail="Failed to save patient data.")


@app.get("/admin/patient/list")
def list_patients(department: Optional[str] = Query(None)):
    """
    List patients by org and optional department.
    """
    try:
        patients = list_patients_by_org(org_id=None, department=department)
        return {"patients": patients, "count": len(patients)}
    except Exception as e:
        logger.error(f"❌ Error while fetching patient list: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch patient list.")


@app.get("/admin/department/list")
def list_departments():
    """
    List departments for a given organisation.
    """
    try:
        departments = list_departments_by_org(org_id=None)
        return {"departments": departments, "count": len(departments)}
    except Exception as e:
        logger.error(f"❌ Error while fetching departments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch departments.")


@app.get("/admin/patient/details")
def patient_details(patient_id: int = Query(...)):
    """
    Fetch single patient details + treatments using patient_id.
    """
    try:
        data = get_patient_details_by_id(patient_id=patient_id, org_id=None)
        if not data:
            raise HTTPException(status_code=404, detail="Patient not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error while fetching patient details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch patient details.")


@app.post("/admin/manage-organisation/create", dependencies=[Depends(admin_only)])
async def create_organisation(
    organisation_name: str = Body(...),
    system_prompt: str = Body(...),
    faqs: Optional[Any] = Body(None, description="FAQ JSON data (question + answer)")
):
    """
    Create a New Organisation with optional FAQs (Admin Only)
    Admin can provide FAQ JSON in the body (dict, list, or single FAQ object).
    Only create organisation if FAQs are valid.
    """

    logger.info(f"📝 Admin attempting to create organisation: {organisation_name}")

    try:
        # 1️⃣ Validate FAQs manually (no DB insertion yet)
        if faqs:
            try:
                # Validate structure
                if isinstance(faqs, dict):
                    first_value = next(iter(faqs.values()), None)
                    if isinstance(first_value, list):
                        # Category dict
                        for category, items in faqs.items():
                            for faq in items:
                                if "question" not in faq or "answer" not in faq:
                                    raise InvalidFAQFormatError(f"Missing 'question' or 'answer' in category '{category}'")
                    else:
                        # Flat dict
                        for question, answer in faqs.items():
                            if not isinstance(question, str) or not isinstance(answer, str):
                                raise InvalidFAQFormatError("Questions and answers must be strings")
                elif isinstance(faqs, list):
                    for faq in faqs:
                        if "question" not in faq or "answer" not in faq:
                            raise InvalidFAQFormatError("Each FAQ must have 'question' and 'answer'")
                else:
                    raise InvalidFAQFormatError("FAQs must be dict or list")
            except InvalidFAQFormatError as e:
                raise HTTPException(status_code=400, detail=f"Invalid FAQs: {str(e)}")

        # 2️⃣ Create organisation (safe, FAQs already validated)
        success, message = add_organisation(organisation_name, system_prompt)
        if not success:
            raise HTTPException(status_code=409, detail=message)

        # 3️⃣ Get org_id
        try:
            org_id = get_org_id(organisation_name)
        except OrganisationNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

        # 4️⃣ Insert FAQs using existing utility
        if faqs:
            add_faqs(org_id=org_id, faqs=faqs)

        logger.info(f"✅ Organisation + FAQs created: {organisation_name}")
        return {"status": "success", "message": "Organisation and FAQs created successfully."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating organisation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")







# @app.get("/admin/manage-organisation/list", dependencies=[Depends(admin_only)])
# def list_organisations():
#     logger.info("📋 Admin requested list of organisations.")
#     try:
#         organisations = get_organisations()
#         logger.info("✅ Successfully retrieved organisations.")
#         return {"organisations": organisations}
#     except Exception as e:
#         logger.error(f"❌ Error fetching organisations: {e}")
#         raise HTTPException(status_code=500, detail="Error retrieving organisations.")

@app.get("/admin/manage-organisation/list", dependencies=[Depends(admin_only)])
def list_organisations():
    """
    Get list of organisations for admin UI.
    Returns organisation_name and editable flag only.
    """
    logger.info("📋 Admin requested list of organisations.")
    try:
        organisations = get_organisations()
        # Only expose organisation_name + editable flag to frontend
        organisations_with_flag = [
            {"organisation_name": org["organisation_name"], "editable": True}
            for org in organisations
        ]
        logger.info("✅ Successfully retrieved organisations.")
        return {"organisations": organisations_with_flag}
    except Exception as e:
        logger.error(f"❌ Error fetching organisations: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving organisations.")




# @app.put("/admin/manage-organisation/edit", dependencies=[Depends(admin_only)])
# def edit_organisation(data: EditOrganisationRequest):
#     logger.info(f"📝 Admin editing organisation: {data.organisation_name}")

#     try:
#         # Treat empty strings as None
#         if data.system_prompt == "":
#             data.system_prompt = None
#         if data.faqs == "":
#             data.faqs = None

#         # Ensure at least one field is provided
#         if data.system_prompt is None and data.faqs is None:
#             raise HTTPException(
#                 status_code=400,
#                 detail="At least one of 'system_prompt' or 'faqs' must be provided."
#             )

#         # Get org_id from organisation name
#         try:
#             org_id = get_org_id(data.organisation_name)
#         except OrganisationNotFoundError:
#             raise HTTPException(status_code=404, detail=f"Organisation '{data.organisation_name}' not found")

#         # Update system prompt if provided
#         if data.system_prompt is not None:
#             from backend import DB_PATH
#             import sqlite3
#             conn = sqlite3.connect(DB_PATH)
#             cursor = conn.cursor()
#             try:
#                 cursor.execute(
#                     "UPDATE organisation SET system_prompt = ? WHERE org_id = ?",
#                     (data.system_prompt, org_id)
#                 )
#                 conn.commit()
#             finally:
#                 cursor.close()
#                 conn.close()
#             logger.info(f"✅ Updated system prompt for {data.organisation_name}")

#         # Update FAQs if provided
#         if data.faqs is not None:
#             validate_faqs(data.faqs)
#             replace_faqs(org_id, data.faqs)
#             logger.info(f"✅ Updated FAQs for {data.organisation_name}")

#         return {"status": "success", "message": "Organisation updated successfully."}

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"❌ Error editing organisation {data.organisation_name}: {e}")
#         raise HTTPException(status_code=500, detail="Failed to edit organisation.")


@app.put("/admin/manage-organisation/edit", dependencies=[Depends(admin_only)])
def edit_organisation(data: EditOrganisationRequest):
    logger.info(f"📝 Admin editing organisation: {data.organisation_name}")

    # Treat empty strings as None
    system_prompt = data.system_prompt if data.system_prompt != "" else None
    faqs = data.faqs if data.faqs != "" else None

    if system_prompt is None and faqs is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'system_prompt' or 'faqs' must be provided."
        )

    try:
        update_organisation(
            org_name=data.organisation_name,
            system_prompt=system_prompt,
            faqs=faqs
        )
        logger.info(f"✅ Organisation updated successfully: {data.organisation_name}")
        return {"status": "success", "message": "Organisation faq and system prompt updated successfully."}
    except OrganisationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Organisation '{data.organisation_name}' not found")
    except Exception as e:
        logger.error(f"❌ Error editing organisation {data.organisation_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to edit organisation.")

@app.get("/nurse/faqs", dependencies=[Depends(nurse_only)])
def get_faqs():
    """
    Get Top Frequently Asked Questions (Nurse Only)

    This endpoint provides the top 3 most frequently asked questions and their corresponding 
    answers. It is designed to assist nurses with quick access to common queries and solutions.

    Authorization:
    - Access is restricted to authenticated nurse users via the `nurse_only` dependency.

    Response:
    - 200 OK: Returns a list of the top FAQs with their answers.
      Example:
      {
        "faqs": [
          {
            "question": "How do I access the patient's chart?",
            "answer": "You can access it via the Records tab in the dashboard."
          },
          {
            "question": "What do I do if the chatbot stops responding?",
            "answer": "Try refreshing the page or logging out and back in."
          },
          ...
        ]
      }

    Errors:
    - 500 Internal Server Error: If the server fails to retrieve the FAQ data.

    Notes:
    - Internally calls `get_most_frequent(top_n=3)` to fetch the FAQs.
    - This feature supports nurses in resolving issues quickly without escalating to admins or support.

    Logs:
    - Logs the request initiation, success, and any exceptions encountered.
    """
    logger.info("🧾 Nurse requested top FAQs")
    try:
        faq_list = get_most_frequent(top_n=3)
        logger.info("✅ FAQs fetched successfully")
        return {
            "faqs": [{"question": q, "answer": a} for q, a in faq_list]
        }
    except Exception as e:
        logger.error(f"❌ Error fetching FAQs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching FAQs: {str(e)}")



@app.post("/nurse/submit-feedback", dependencies=[Depends(nurse_only)])
def submit_feedback(
    rating: int = Form(...),
    suggestion: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        username = current_user["username"]  # Corrected from "sub" to "username"
        logger.info(f"📝 Nurse '{username}' submitted feedback with rating {rating}")
        insert_feedback(username, rating, suggestion)
        logger.info("✅ Feedback submission successful")
        return {"status": "success", "message": "✅ Thank you for your feedback!"}
    except Exception as e:
        logger.error(f"❌ Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")




@app.websocket("/ws/nurse/chat")
async def websocket_nurse_chat(websocket: WebSocket):
    """
    WebSocket endpoint for authenticated nurses to interact with a medical assistant AI.
    System prompt is always organisation-specific.
    """
    await websocket.accept()

    # Step 1: Get token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_text("❌ Token is missing. Please log in.")
        await websocket.close()
        return

    # Step 2: Validate token
    try:
        current_user = get_current_user_from_token(token)
    except JWTError:
        await websocket.send_text("❌ Invalid or expired token.")
        await websocket.close()
        return

    # Step 3: Role check
    if not nurse_only(current_user):
        await websocket.send_text("❌ Access denied. Only nurses are allowed.")
        await websocket.close()
        return

    username = current_user.get("sub")
    org_id = current_user.get("org_id")
    organisation_name = current_user.get("organisation_name")
    nurse_department = current_user.get("department")
    logger.info(f"🧠 Mem0 configured: {'yes' if mem0_is_configured() else 'no'}")
   

    # ✅ Fetch org-specific system prompt from backend.py
    try:
        system_prompt = get_org_system_prompt(org_id)
        logger.info(f"📌 Loaded system prompt for org '{organisation_name}' (id={org_id})")
    except Exception as e:
        logger.error(f"❌ Could not load system prompt for org_id={org_id}: {e}")
        await websocket.send_text("❌ Internal error loading system settings.")
        await websocket.close()
        return

    try:
        while True:
            raw_payload = await websocket.receive_text()
            query = raw_payload
            try:
                parsed_payload = json.loads(raw_payload)
                if isinstance(parsed_payload, dict) and isinstance(parsed_payload.get("query"), str):
                    query = parsed_payload["query"].strip()
            except Exception:
                query = raw_payload.strip()

            print("query", query)

            try:
                logger.info(f"📩 Nurse '{username}' from '{organisation_name}' submitted query: {query}")

                session_id = f"org-{org_id}:{username}"
                trace_metadata = {
                    "channel": "websocket",
                    "organisation_name": organisation_name,
                    "org_id": org_id,
                    "langfuse": langfuse_status(),
                }

                with langfuse_trace_context(
                    user_id=username,
                    session_id=session_id,
                    metadata=trace_metadata,
                ):
                    with start_langfuse_observation(
                        name="nurse-chat-request",
                        as_type="span",
                        input_data={"query": query},
                        metadata=trace_metadata,
                    ) as chat_trace:
                        # ✅ Input validation
                        input_guard = get_input_guard()
                        with start_langfuse_observation(
                            name="validate-user-input",
                            as_type="guardrail",
                            input_data={"query": query},
                            metadata={"username": username},
                        ) as validation_observation:
                            try:
                                input_guard.validate(query)
                                validation_observation.update(output={"valid": True})
                            except ValueError as ve:
                                logger.warning(f"⚠️ Invalid input from user '{username}': {ve}")
                                validation_observation.update(
                                    output={"valid": False},
                                    level="WARNING",
                                    status_message=str(ve),
                                )
                                await websocket.send_text(f"❌ Invalid input: {ve}")
                                continue

                            if not re.match(r'^[\x00-\x7F\s]+$', query):
                                logger.warning(f"❌ Non-English query rejected for '{username}'")
                                validation_observation.update(
                                    output={"valid": False},
                                    level="WARNING",
                                    status_message="Non-English query rejected",
                                )
                                await websocket.send_text("❌ Please submit your query in English only.")
                                continue

                        # ✅ History query handling
                        if re.search(r'\b(previous|past|history|asked about|my queries|queries|earlier)\b', query, re.IGNORECASE):
                            logger.info(f"📖 Fetching query history for '{username}'")
                            with start_langfuse_observation(
                                name="fetch-user-history",
                                as_type="retriever",
                                input_data={"query": query, "username": username},
                                metadata={"history_limit": 10},
                            ) as history_observation:
                                response_en = get_user_queries(username, query)
                                history_observation.update(
                                    output={"history_answer_generated": True},
                                )
                            print("response_en",response_en)
                        else:
                            logger.info(f"📚 Retrieving docs for query by '{username}'")
                            memory_update_result = apply_patient_memory_updates(
                                query=query,
                                org_id=org_id,
                                department=nurse_department,
                            )
                            mem0_lines = get_mem0_context(
                                query=query,
                                user_id=username,
                                org_id=org_id,
                                department=nurse_department,
                                limit=5,
                            )
                            mem0_context_text = "\n".join([f"- {line}" for line in mem0_lines]) if mem0_lines else ""
                            recent_user_messages = get_recent_user_messages(username=username, limit=8)
                            recent_user_context_text = "\n".join(
                                [f"- {item}" for item in recent_user_messages if item.strip()]
                            )

                            patient_context_data = get_patient_context_for_query(
                                query=query,
                                org_id=org_id,
                                department=nurse_department,
                            )
                            patient_context_text = format_patient_context(patient_context_data)
                            has_patient_context = patient_context_data is not None

                            with start_langfuse_observation(
                                name="retrieve-relevant-docs",
                                as_type="retriever",
                                input_data={"query": query, "k": 3},
                                metadata={"org_id": org_id},
                            ) as retrieval_observation:
                                relevant_docs, detected_lang = get_relevant_docs(query, org_id=org_id)
                                retrieval_observation.update(
                                    output={
                                        "document_count": len(relevant_docs),
                                        "detected_lang": detected_lang,
                                        "sources": [source for _, source in relevant_docs],
                                    }
                                )
                            print("relevant_docs",relevant_docs)
                            context = format_docs_with_links(relevant_docs)
                            has_rag_context = bool(relevant_docs)

                            mem0_block = (
                                f"Mem0 Conversation Context:\n{mem0_context_text}\n\n"
                                if mem0_context_text
                                else ""
                            )
                            recent_user_block = (
                                f"Recent Nurse Conversation Context:\n{recent_user_context_text}\n\n"
                                if recent_user_context_text
                                else ""
                            )
                            memory_update_block = (
                                "Patient Profile Update Applied:\n"
                                f"- Updated patient {memory_update_result.get('patient_code')}: "
                                f"{memory_update_result.get('old_name')} -> {memory_update_result.get('new_name')}\n\n"
                                if memory_update_result.get("updated")
                                else ""
                            )
                            patient_block = (
                                f"Patient Data Context:\n{patient_context_text}\n\n"
                                if has_patient_context
                                else ""
                            )
                            rag_block = (
                                f"Treatment RAG Context:\n{context}\n\n"
                                if has_rag_context
                                else ""
                            )

                            # ✅ Use org-specific system prompt
                            prompt = (
                                f"Organisation ID: {org_id}\n\n"
                                f"Department: {nurse_department or 'Not specified'}\n\n"
                                f"{mem0_block}"
                                f"{recent_user_block}"
                                f"{memory_update_block}"
                                f"{patient_block}"
                                f"{rag_block}"
                                f"If the information is irrelevant or unknown, respond with:\n"
                                f"First, extract and list only the relevant source links (URLs, PDF files) that are directly related to the user's question.\n"
                                f"Format all links as clickable Markdown hyperlinks, e.g.,(URL).\n"
                                f"Only include links if they provide direct value or reference to the question.\n\n"
                                f"Then, provide a detailed and well-structured response that includes:\n"
                                f"- Scientific insights or background information,\n"
                                f"- Practical step-by-step instructions or procedures,\n"
                                f"- Helpful tips or recommendations,\n"
                                f"- And clear, concise explanations that address the user's query thoroughly.\n"
                                f"- If Mem0 context conflicts with patient DB data, prioritize patient DB data.\n"
                                f"- If the question asks patient list/count for a department, answer directly from Patient Data Context with exact count and names.\n"
                                f"- Use Recent Nurse Conversation Context as short-term memory for follow-up questions like medication given earlier in this chat.\n"
                                f"- If a patient profile update was applied, acknowledge briefly and continue with updated patient identity.\n"
                                f"- Never expose internal retrieval/system status to the user.\n"
                                f"- Do NOT say phrases like: 'No relevant memory found', 'No specific patient record matched', or 'no RAG context'.\n"
                                f"- If no patient-specific data applies, continue with a normal clinical guidance answer without mentioning backend context checks.\n"
                                f"- Always separate the answer into two sections: `Patient Information` and `Treatment Guidance`.\n\n"
                                f"Make sure the answer is engaging, informative, and easy to understand, rather than just a brief reply.\n\n"
                                f"Question: {query}"
                            )

                            logger.info(f"🤖 Sending prompt to Gemini model for '{username}' (org={organisation_name})")
                            full_prompt = system_prompt + "\n\n" + prompt
                            logger.info(f"🤖 Sending prompt to Gemini model for user '{username}'")
                            response_en = query_gemini(full_prompt)

                        # ✅ Store query + response
                        store_user_query(username, query, response_en)
                        save_mem0_interaction(
                            user_id=username,
                            query=query,
                            response=response_en,
                            org_id=org_id,
                            department=nurse_department,
                            metadata={
                                "channel": "nurse_websocket",
                                "organisation_name": organisation_name,
                            },
                        )
                        chat_trace.update(output={"response": response_en})
                        logger.info(f"✅ Query stored for '{username}' ({organisation_name})")

                        await websocket.send_text(response_en)

            except Exception as e:
                logger.error(f"❌ Error handling query for '{username}' ({organisation_name}): {e}")
                await websocket.send_text(f"❌ Internal error: {str(e)}")

    except WebSocketDisconnect as disconnect:
        logger.info(f"🔌 WebSocket closed for '{username}' ({organisation_name})")
        logger.error(
            f"❌ WebSocketDisconnect for '{username}' ({organisation_name}): "
            f"Code={disconnect.code}, Reason={disconnect.reason or 'No reason'}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"WebSocket disconnected (code: {disconnect.code}, reason: {disconnect.reason or 'none'})"
        )







if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
