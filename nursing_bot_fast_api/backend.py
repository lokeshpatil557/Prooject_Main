import os
import re
import json
import sqlite3
import hashlib
from langchain_core.documents import Document
from langdetect import detect
#from langchain_community.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
# from langchain.agents import Tool, initialize_agent
# from langchain.agents.agent_types import AgentType
#from langchain_google_genai import generativeAI
from langchain.tools import tool
from translator_utils import translate_text
from langchain_community.vectorstores import SQLiteVec
from gemini_api import query_gemini
from datetime import datetime
from typing import Any



os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

DB_PATH = "user_queries.sqlite"
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
#nursing_vectorstore = Chroma(persist_directory="./pdf_docs_db", embedding_function=embedding_model)
# connection = SQLiteVec.create_connection(db_file=DB_PATH)
#connection = sqlite3.connect(DB_PATH, check_same_thread=False)
# nursing_vectorstore = SQLiteVec(
#     table="sql_vect" , embedding=embedding_model, connection=connection)

class OrganisationNotFoundError(Exception):
    pass

class InvalidFAQFormatError(Exception):
    pass


def get_nursing_vectorstore():
    connection = SQLiteVec.create_connection(db_file=DB_PATH)
    return SQLiteVec(
        table="sql_vect",
        embedding=embedding_model,
        connection=connection
        
    )


def _similarity_search_for_org(query: str, org_id: Any, k: int = 3):
    connection = SQLiteVec.create_connection(db_file=DB_PATH)
    try:
        query_embedding = embedding_model.embed_query(query)
        serialized_embedding = connection.execute(
            "SELECT vec_f32(?) AS embedding_blob",
            (json.dumps(query_embedding),),
        ).fetchone()["embedding_blob"]

        sql_query = """
            SELECT
                e.text,
                e.metadata,
                v.distance
            FROM sql_vect AS e
            INNER JOIN sql_vect_vec AS v ON v.rowid = e.rowid
            WHERE
                v.text_embedding MATCH ?
                AND k = ?
                AND CAST(json_extract(e.metadata, '$.org_id') AS TEXT) = CAST(? AS TEXT)
            ORDER BY v.distance
        """

        cursor = connection.cursor()
        cursor.execute(sql_query, (serialized_embedding, k, org_id))
        results = cursor.fetchall()

        documents = []
        for row in results:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            documents.append(Document(page_content=row["text"], metadata=metadata))

        return documents
    finally:
        connection.close()
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# def register_user(username, password):
#     username = username.strip().lower()
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     try:
#         cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
#         conn.commit()
#         return True, "User registered successfully."
#     except sqlite3.IntegrityError:
#         return False, "Username already exists."
#     except Exception:
#         return False, "Registration failed due to an error."
#     finally:
#         conn.close()


def register_user(username, password, org_id):
    username = username.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, org_id) VALUES (?, ?, ?)",
            (username, hash_password(password), org_id),
        )
        conn.commit()
        return True, "User registered successfully."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    except Exception:
        return False, "Registration failed due to an error."
    finally:
        conn.close()


def get_all_users_with_org():
    """
    Fetch all users along with their organisation name.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.username, o.organisation_name
            FROM users u
            LEFT JOIN organisation o ON u.org_id = o.org_id
            ORDER BY u.username ASC
        """)
        rows = cursor.fetchall()
        return [
            {
                "username": row[0],
                "organisation_name": row[1] if row[1] else "Unknown"
            }
            for row in rows
        ]
    finally:
        cursor.close()
        conn.close()


def add_organisation(org_name, system_prompt):
    org_name = org_name.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO organisation (organisation_name, system_prompt) VALUES (?, ?)",
            (org_name, system_prompt),
        )
        conn.commit()
        return True, "Organisation created successfully."
    except sqlite3.IntegrityError:
        return False, "Organisation already exists."
    except Exception:
        return False, "Organisation creation failed due to an error."
    finally:
        conn.close()


def get_org_id(org_name: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT org_id FROM organisation WHERE organisation_name = ?",
        (org_name.strip().lower(),)
    )
    result = cursor.fetchone()
    conn.close()
    if not result:
        raise OrganisationNotFoundError(f"Organisation '{org_name}' not found")
    return result[0]

# ---------------- Add FAQs ----------------
def add_faqs(org_id: int, faqs: Any):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if isinstance(faqs, dict):
            # Could be categories or flat dict
            first_value = next(iter(faqs.values()), None)
            if isinstance(first_value, list):
                # Category dict (current logic)
                for category, items in faqs.items():
                    for faq in items:
                        if "question" not in faq or "answer" not in faq:
                            continue
                        cursor.execute(
                            "INSERT INTO faq (org_id, category, question, answer) VALUES (?, ?, ?, ?)",
                            (org_id, category, faq["question"], faq["answer"])
                        )
            else:
                # Flat dict: key=question, value=answer
                for question, answer in faqs.items():
                    cursor.execute(
                        "INSERT INTO faq (org_id, category, question, answer) VALUES (?, ?, ?, ?)",
                        (org_id, None, question, answer)
                    )
        elif isinstance(faqs, list):
            # Flat list of question/answer objects
            for faq in faqs:
                if "question" not in faq or "answer" not in faq:
                    continue
                cursor.execute(
                    "INSERT INTO faq (org_id, category, question, answer) VALUES (?, ?, ?, ?)",
                    (org_id, None, faq["question"], faq["answer"])
                )
        else:
            raise InvalidFAQFormatError("Invalid FAQ format")
        conn.commit()
    finally:
        conn.close()


import sqlite3
from typing import Dict, Any

DB_PATH = "user_queries.sqlite"

def get_all_faqs_by_org(org_id: int) -> Dict[str, Any]:
    """
    Fetch all FAQs for the given organisation ID,
    grouped by category.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT category, question, answer FROM faq WHERE org_id = ? ORDER BY category, rowid",
            (org_id,),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    faqs_by_category: Dict[str, list] = {}
    for category, question, answer in rows:
        key = category if category else "uncategorized"
        faqs_by_category.setdefault(key, []).append(
            {"question": question, "answer": answer}
        )

    return faqs_by_category


def verify_user(username: str, password: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password, org_id FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row and row[2] == hash_password(password):
        user_id, username, _, org_id = row

        # fetch organisation name
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT organisation_name FROM organisation WHERE org_id = ?", (org_id,))
        org_row = cursor.fetchone()
        conn.close()

        org_name = org_row[0] if org_row else "Unknown Organisation"

        return {
            "id": user_id,
            "username": username,
            "org_id": org_id,
            "organisation_name": org_name
        }
    return None



def is_valid_username(username):
    username = username.strip()
    username_regex = r"^[a-zA-Z][a-zA-Z0-9_]{2,29}$"
    return bool(re.match(username_regex, username))
# @tool
# def search_nursing_pdf(query: str) -> str:
#     """Searches nursing documents for relevant content."""
#     vectorstore = get_nursing_vectorstore()
#     results = vectorstore.similarity_search(query, k=3)
#     return "\n".join([doc.page_content for doc in results])
    
# llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3)

# tools = [
#     Tool(
#         name="Nursing PDF Retriever",
#         func=search_nursing_pdf,
#         description="Useful for answering questions from nursing manuals or documents and related refernce urls."
#     )
# ]

# agent = initialize_agent(
#     tools=tools,
#     llm=llm,
#     agent_type=AgentType.OPENAI_FUNCTIONS,
#     verbose=False,
#     handle_parsing_errors=True 
# )

# def query_gemini_agent(prompt: str):
#     try:
#         return agent.run(prompt)
#     except Exception as e:
#         return f"❌ Error: {str(e)}"

def get_relevant_docs(query, org_id=None, k=3):
    detected_lang = detect(query)
    translated_query = translate_text(query, target_lang='en') if detected_lang != 'en' else query
    if org_id is not None:
        results = _similarity_search_for_org(translated_query, org_id=org_id, k=k)
    else:
        vectorstore = get_nursing_vectorstore()
        results = vectorstore.similarity_search(translated_query, k=k)
    docs_with_source = [(doc.page_content, doc.metadata.get("source", "Unknown source")) for doc in results]
    #return [doc.page_content for doc in results], detected_lang
    return docs_with_source, detected_lang


def ensure_patient_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                department_id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                department_name TEXT NOT NULL,
                department_code TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(org_id, department_name)
            )
            """
        )
        cursor.execute("PRAGMA table_info(departments)")
        dept_columns = {row[1] for row in cursor.fetchall()}
        if "department_code" not in dept_columns:
            cursor.execute("ALTER TABLE departments ADD COLUMN department_code TEXT")
        if "created_at" not in dept_columns:
            cursor.execute("ALTER TABLE departments ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                patient_code TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT,
                age INTEGER,
                gender TEXT,
                diagnosis TEXT,
                department TEXT,
                ward TEXT,
                bed_no TEXT,
                primary_doctor TEXT,
                status TEXT DEFAULT 'admitted',
                summary TEXT,
                alias_names TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(org_id, patient_code)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patient_treatments (
                treatment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                treatment_name TEXT NOT NULL,
                dose TEXT,
                frequency TEXT,
                route TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_departments_org_name ON departments(org_id, department_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_patients_org_department ON patients(org_id, department)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_patient_treatments_patient ON patient_treatments(patient_id)"
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def upsert_patient_record(
    *,
    org_id: int,
    patient_code: str,
    first_name: str,
    last_name: str = None,
    age: int = None,
    gender: str = None,
    diagnosis: str = None,
    department: str = None,
    ward: str = None,
    bed_no: str = None,
    primary_doctor: str = None,
    status: str = "admitted",
    summary: str = None,
    alias_names: str = None,
    treatments: Any = None,
    department_code: str = None,
):
    ensure_patient_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if department:
            cursor.execute(
                """
                INSERT INTO departments (org_id, department_name, department_code, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(org_id, department_name) DO UPDATE SET
                    department_code = COALESCE(excluded.department_code, departments.department_code)
                """,
                (
                    org_id,
                    department.strip(),
                    (department_code or "").strip().upper() or None,
                    now_str,
                ),
            )
        cursor.execute(
            """
            INSERT INTO patients (
                org_id, patient_code, first_name, last_name, age, gender, diagnosis,
                department, ward, bed_no, primary_doctor, status, summary, alias_names, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(org_id, patient_code) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                age = excluded.age,
                gender = excluded.gender,
                diagnosis = excluded.diagnosis,
                department = excluded.department,
                ward = excluded.ward,
                bed_no = excluded.bed_no,
                primary_doctor = excluded.primary_doctor,
                status = excluded.status,
                summary = excluded.summary,
                alias_names = excluded.alias_names,
                updated_at = excluded.updated_at
            """,
            (
                org_id,
                patient_code.strip().upper(),
                first_name.strip(),
                (last_name or "").strip() or None,
                age,
                (gender or "").strip() or None,
                (diagnosis or "").strip() or None,
                (department or "").strip() or None,
                (ward or "").strip() or None,
                (bed_no or "").strip() or None,
                (primary_doctor or "").strip() or None,
                (status or "admitted").strip(),
                (summary or "").strip() or None,
                (alias_names or "").strip() or None,
                now_str,
            ),
        )
        cursor.execute(
            "SELECT patient_id FROM patients WHERE org_id = ? AND patient_code = ?",
            (org_id, patient_code.strip().upper()),
        )
        patient_row = cursor.fetchone()
        patient_id = patient_row[0]

        if treatments is not None:
            cursor.execute("DELETE FROM patient_treatments WHERE patient_id = ?", (patient_id,))
            for treatment in treatments:
                cursor.execute(
                    """
                    INSERT INTO patient_treatments (
                        patient_id, treatment_name, dose, frequency, route, notes, is_active, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        patient_id,
                        treatment.get("treatment_name"),
                        treatment.get("dose"),
                        treatment.get("frequency"),
                        treatment.get("route"),
                        treatment.get("notes"),
                        1 if treatment.get("is_active", True) else 0,
                        now_str,
                    ),
                )

        conn.commit()
        return patient_id
    finally:
        cursor.close()
        conn.close()


def list_patients_by_org(org_id: int = None, department: str = None):
    ensure_patient_tables()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        if department and org_id is not None:
            cursor.execute(
                """
                SELECT patient_id, patient_code, first_name, last_name, age, gender, diagnosis,
                       department, ward, bed_no, primary_doctor, status, summary, alias_names, updated_at
                FROM patients
                WHERE org_id = ? AND lower(department) = lower(?)
                ORDER BY first_name, last_name
                """,
                (org_id, department.strip()),
            )
        elif department:
            cursor.execute(
                """
                SELECT patient_id, patient_code, first_name, last_name, age, gender, diagnosis,
                       department, ward, bed_no, primary_doctor, status, summary, alias_names, updated_at
                FROM patients
                WHERE lower(department) = lower(?)
                ORDER BY first_name, last_name
                """,
                (department.strip(),),
            )
        elif org_id is not None:
            cursor.execute(
                """
                SELECT patient_id, patient_code, first_name, last_name, age, gender, diagnosis,
                       department, ward, bed_no, primary_doctor, status, summary, alias_names, updated_at
                FROM patients
                WHERE org_id = ?
                ORDER BY first_name, last_name
                """,
                (org_id,),
            )
        else:
            cursor.execute(
                """
                SELECT patient_id, patient_code, first_name, last_name, age, gender, diagnosis,
                       department, ward, bed_no, primary_doctor, status, summary, alias_names, updated_at
                FROM patients
                ORDER BY first_name, last_name
                """
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def list_departments_by_org(org_id: int = None):
    ensure_patient_tables()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        if org_id is not None:
            cursor.execute(
                """
                SELECT department_id, department_name, department_code, created_at
                FROM departments
                WHERE org_id = ?
                ORDER BY department_name ASC
                """,
                (org_id,),
            )
        else:
            cursor.execute(
                """
                SELECT department_id, department_name, department_code, created_at
                FROM departments
                ORDER BY department_name ASC
                """
            )
        return [
            {
                "id": row["department_id"],
                "name": row["department_name"],
                "code": row["department_code"] or "",
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()
        conn.close()


def list_patients_by_department(org_id: int = None, department_id: int = None, department_name: str = None):
    ensure_patient_tables()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        resolved_department_name = None
        if department_id is not None and org_id is not None:
            cursor.execute(
                """
                SELECT department_name
                FROM departments
                WHERE org_id = ? AND department_id = ?
                """,
                (org_id, department_id),
            )
            row = cursor.fetchone()
            if not row:
                return []
            resolved_department_name = row["department_name"]
        elif department_id is not None:
            cursor.execute(
                """
                SELECT department_name
                FROM departments
                WHERE department_id = ?
                """,
                (department_id,),
            )
            row = cursor.fetchone()
            if not row:
                return []
            resolved_department_name = row["department_name"]
        elif department_name:
            resolved_department_name = department_name.strip()
        else:
            return []

        if org_id is not None:
            cursor.execute(
                """
                SELECT
                    patient_id,
                    patient_code,
                    first_name,
                    last_name,
                    department,
                    ward,
                    bed_no,
                    status
                FROM patients
                WHERE org_id = ? AND lower(department) = lower(?)
                ORDER BY first_name, last_name
                """,
                (org_id, resolved_department_name),
            )
        else:
            cursor.execute(
                """
                SELECT
                    patient_id,
                    patient_code,
                    first_name,
                    last_name,
                    department,
                    ward,
                    bed_no,
                    status
                FROM patients
                WHERE lower(department) = lower(?)
                ORDER BY first_name, last_name
                """,
                (resolved_department_name,),
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def get_patient_details_by_id(patient_id: int, org_id: int = None):
    ensure_patient_tables()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        if org_id is not None:
            cursor.execute(
                "SELECT * FROM patients WHERE patient_id = ? AND org_id = ?",
                (patient_id, org_id),
            )
        else:
            cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
        row = cursor.fetchone()
        if not row:
            return None

        cursor.execute(
            """
            SELECT treatment_id, treatment_name, dose, frequency, route, notes, is_active, updated_at
            FROM patient_treatments
            WHERE patient_id = ?
            ORDER BY treatment_id ASC
            """,
            (patient_id,),
        )
        treatments = [dict(t) for t in cursor.fetchall()]
        return {"patient": dict(row), "treatments": treatments}
    finally:
        cursor.close()
        conn.close()


def _query_mentions_candidate(query: str, candidates: list) -> bool:
    lowered_query = f" {query.lower()} "
    for candidate in candidates:
        if candidate and f" {candidate.lower()} " in lowered_query:
            return True
    return False


def _clean_text(value: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", (value or "").lower()).strip()


def _row_value(row: Any, key: str, default: str = ""):
    try:
        value = row[key]
    except Exception:
        value = None
    return value if value is not None else default


def _patient_match_score(query: str, row: Any) -> int:
    q = _clean_text(query)
    q_padded = f" {q} "
    first = _clean_text(_row_value(row, "first_name", ""))
    last = _clean_text(_row_value(row, "last_name", ""))
    full = " ".join([p for p in [first, last] if p]).strip()
    code = _clean_text(_row_value(row, "patient_code", ""))

    score = 0
    if code and f" {code} " in q_padded:
        score = max(score, 100)
    if full and f" {full} " in q_padded:
        score = max(score, 90)

    # partial full-name match to tolerate minor typos like "sing" for "singh"
    if full and first and last and first in q and any(token and token in q for token in [last, last[: max(3, len(last)-1)]]):
        score = max(score, 80)

    if last and f" {last} " in q_padded and first and f" {first} " in q_padded:
        score = max(score, 75)
    if last and f" {last} " in q_padded:
        score = max(score, 60)
    if first and f" {first} " in q_padded:
        score = max(score, 40)

    aliases = _row_value(row, "alias_names", "")
    for alias in [a.strip() for a in aliases.split(",") if a.strip()]:
        alias_c = _clean_text(alias)
        if alias_c and f" {alias_c} " in q_padded:
            score = max(score, 70)

    return score


def get_patient_context_for_query(query: str, org_id: int, department: str = None):
    ensure_patient_tables()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM patients WHERE org_id = ?", (org_id,))
        all_patients = cursor.fetchall()
        if not all_patients:
            return None

        lowered_query = query.lower()
        department_names = sorted({(row["department"] or "").strip() for row in all_patients if row["department"]})

        mentioned_department = None
        for dep_name in department_names:
            dep_l = dep_name.lower()
            if dep_l and dep_l in lowered_query:
                mentioned_department = dep_name
                break

        if mentioned_department:
            patients = [
                row for row in all_patients
                if (row["department"] or "").strip().lower() == mentioned_department.lower()
            ]
        elif department:
            patients = [
                row for row in all_patients
                if (row["department"] or "").strip().lower() == department.strip().lower()
            ]
        else:
            patients = list(all_patients)

        list_intent = bool(
            re.search(
                r"\b(list|show|names?|patients?|count|how many|who all|all)\b",
                lowered_query,
            )
        )

        if mentioned_department and list_intent:
            dep_rows = [row for row in patients if (row["department"] or "").strip().lower() == mentioned_department.lower()]
            dep_rows_sorted = sorted(dep_rows, key=lambda r: ((r["first_name"] or "").lower(), (r["last_name"] or "").lower()))
            return {
                "mode": "department_list",
                "department": mentioned_department,
                "patient_count": len(dep_rows_sorted),
                "patients": [
                    {
                        "patient_id": row["patient_id"],
                        "patient_code": row["patient_code"],
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "ward": row["ward"],
                        "bed_no": row["bed_no"],
                        "status": row["status"],
                    }
                    for row in dep_rows_sorted
                ],
            }

        scored_patients = [(row, _patient_match_score(query, row)) for row in patients]
        scored_patients = [item for item in scored_patients if item[1] > 0]
        scored_patients.sort(key=lambda x: x[1], reverse=True)
        matched_patient = scored_patients[0][0] if scored_patients else None

        # avoid ambiguous first-name-only picks (e.g., many "Raj")
        if scored_patients and scored_patients[0][1] == 40:
            top_first = (matched_patient["first_name"] or "").lower()
            same_first_count = sum(1 for row, score in scored_patients if score == 40 and (row["first_name"] or "").lower() == top_first)
            if same_first_count > 1:
                matched_patient = None

        # Fallback: if nurse department filter was too narrow, search all org patients by explicit identity.
        if not matched_patient and patients is not all_patients:
            fallback_scored = [(row, _patient_match_score(query, row)) for row in all_patients]
            fallback_scored = [item for item in fallback_scored if item[1] >= 60]
            fallback_scored.sort(key=lambda x: x[1], reverse=True)
            if fallback_scored:
                matched_patient = fallback_scored[0][0]

        if not matched_patient:
            return None

        cursor.execute(
            """
            SELECT treatment_name, dose, frequency, route, notes, is_active
            FROM patient_treatments
            WHERE patient_id = ?
            ORDER BY treatment_id ASC
            """,
            (matched_patient["patient_id"],),
        )
        treatments = [dict(t_row) for t_row in cursor.fetchall()]
        return {"patient": dict(matched_patient), "treatments": treatments}
    finally:
        cursor.close()
        conn.close()


def format_patient_context(patient_context: Any) -> str:
    if not patient_context:
        return "No specific patient record matched this question."

    if patient_context.get("mode") == "department_list":
        dep_name = patient_context.get("department") or "Unknown Department"
        count = patient_context.get("patient_count") or 0
        dep_patients = patient_context.get("patients") or []
        lines = [
            "Department Patient Snapshot:",
            f"- Department: {dep_name}",
            f"- Total Patients: {count}",
        ]
        if dep_patients:
            lines.append("- Patient Names:")
            for p in dep_patients:
                full_name = " ".join([part for part in [p.get("first_name"), p.get("last_name")] if part]).strip()
                lines.append(
                    f"  - {full_name or p.get('patient_code') or 'Unknown'} "
                    f"(Code: {p.get('patient_code') or 'NA'}, Ward/Bed: {p.get('ward') or 'NA'}/{p.get('bed_no') or 'NA'}, Status: {p.get('status') or 'NA'})"
                )
        return "\n".join(lines)

    patient = patient_context["patient"]
    lines = [
        "Patient Snapshot:",
        f"- Patient Code: {patient.get('patient_code') or 'NA'}",
        f"- Name: {' '.join([part for part in [patient.get('first_name'), patient.get('last_name')] if part]) or 'NA'}",
        f"- Age/Gender: {patient.get('age') or 'NA'} / {patient.get('gender') or 'NA'}",
        f"- Department: {patient.get('department') or 'NA'}",
        f"- Ward/Bed: {patient.get('ward') or 'NA'} / {patient.get('bed_no') or 'NA'}",
        f"- Diagnosis: {patient.get('diagnosis') or 'NA'}",
        f"- Primary Doctor: {patient.get('primary_doctor') or 'NA'}",
        f"- Status: {patient.get('status') or 'NA'}",
        f"- Summary: {patient.get('summary') or 'NA'}",
    ]

    treatments = patient_context.get("treatments") or []
    if treatments:
        lines.append("Active/Recorded Treatments:")
        for item in treatments:
            active_text = "active" if item.get("is_active") else "inactive"
            lines.append(
                "- "
                + " | ".join(
                    [
                        item.get("treatment_name") or "NA",
                        f"dose: {item.get('dose') or 'NA'}",
                        f"frequency: {item.get('frequency') or 'NA'}",
                        f"route: {item.get('route') or 'NA'}",
                        f"notes: {item.get('notes') or 'NA'}",
                        active_text,
                    ]
                )
            )
    else:
        lines.append("Treatments: No treatments recorded.")

    return "\n".join(lines)


def _merge_aliases(existing_aliases: str, extra_aliases: list[str]) -> str:
    merged = []
    seen = set()
    for raw in (existing_aliases or "").split(","):
        item = raw.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            merged.append(item)
    for raw in extra_aliases:
        item = (raw or "").strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            merged.append(item)
    return ",".join(merged)


def apply_patient_memory_updates(query: str, org_id: int, department: str = None) -> dict:
    """
    Parse lightweight nurse correction statements from chat and persist to patient DB.
    Current supported intent:
    - "<old patient ref> name is <new full name>"
    """
    lowered = (query or "").strip().lower()
    if "name is" not in lowered:
        return {"updated": False}

    # Split around first occurrence to capture left (target ref) and right (new name)
    parts = re.split(r"\bname\s+is\b", query, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return {"updated": False}

    left_ref = parts[0].strip()
    right_name = re.sub(r"[^\w\s-]", " ", parts[1]).strip()
    right_name = re.sub(r"\s+", " ", right_name).strip()
    if not right_name:
        return {"updated": False}

    patient_context = get_patient_context_for_query(left_ref, org_id=org_id, department=department)
    if not patient_context or not patient_context.get("patient"):
        return {"updated": False}

    patient = patient_context["patient"]
    old_first = (patient.get("first_name") or "").strip()
    old_last = (patient.get("last_name") or "").strip()
    old_full = " ".join([p for p in [old_first, old_last] if p]).strip()

    new_tokens = right_name.split()
    new_first = new_tokens[0]
    new_last = " ".join(new_tokens[1:]) if len(new_tokens) > 1 else ""

    aliases = _merge_aliases(
        patient.get("alias_names") or "",
        [old_full, old_first, old_last, right_name, new_first, new_last],
    )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE patients
            SET first_name = ?, last_name = ?, alias_names = ?, updated_at = ?
            WHERE patient_id = ?
            """,
            (
                new_first,
                new_last if new_last else None,
                aliases,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                patient["patient_id"],
            ),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return {
        "updated": True,
        "patient_id": patient["patient_id"],
        "patient_code": patient.get("patient_code"),
        "old_name": old_full or old_first,
        "new_name": right_name,
    }


def seed_default_patients():
    ensure_patient_tables()
    department_specs = [
        ("ICU", "ICU"),
        ("Emergency", "EMR"),
        ("Ward 1", "WRD1"),
        ("Ward 2", "WRD2"),
        ("Ward 3", "WRD3"),
        ("Ward 4", "WRD4"),
    ]
    first_names = ["Raj", "Rahul", "Priya", "Anita", "Suresh"]
    last_names = ["Sharma", "Kumar", "Patel", "Singh", "Mehta"]
    diagnosis_by_department = {
        "ICU": "Critical care under close monitoring",
        "Emergency": "Acute presentation under emergency care",
        "Ward 1": "General inpatient treatment and observation",
        "Ward 2": "Post-procedure recovery and monitoring",
        "Ward 3": "Infection management and supportive care",
        "Ward 4": "Chronic condition stabilization",
    }
    treatment_by_department = {
        "ICU": [
            {"treatment_name": "Ventilator support", "dose": "NA", "frequency": "continuous", "route": "respiratory", "notes": "Critical care protocol", "is_active": True},
            {"treatment_name": "IV broad-spectrum antibiotic", "dose": "as per chart", "frequency": "every 12 hours", "route": "IV", "notes": "Review culture", "is_active": True},
        ],
        "Emergency": [
            {"treatment_name": "Immediate triage protocol", "dose": "NA", "frequency": "once", "route": "clinical", "notes": "Stabilize first", "is_active": True},
            {"treatment_name": "Pain management", "dose": "as required", "frequency": "every 8 hours", "route": "oral", "notes": "Reassess pain score", "is_active": True},
        ],
        "Ward 1": [
            {"treatment_name": "Oral antibiotics", "dose": "as per chart", "frequency": "twice daily", "route": "oral", "notes": "Continue 5 days", "is_active": True},
            {"treatment_name": "Vital monitoring", "dose": "NA", "frequency": "every 6 hours", "route": "nursing", "notes": "Record in chart", "is_active": True},
        ],
        "Ward 2": [
            {"treatment_name": "Post-op dressing care", "dose": "NA", "frequency": "once daily", "route": "nursing", "notes": "Aseptic technique", "is_active": True},
            {"treatment_name": "DVT prophylaxis", "dose": "as per chart", "frequency": "once daily", "route": "subcutaneous", "notes": "Monitor bleeding", "is_active": True},
        ],
        "Ward 3": [
            {"treatment_name": "Isolation protocol", "dose": "NA", "frequency": "continuous", "route": "infection-control", "notes": "PPE mandatory", "is_active": True},
            {"treatment_name": "Hydration support", "dose": "as per chart", "frequency": "continuous", "route": "IV", "notes": "Monitor input/output", "is_active": True},
        ],
        "Ward 4": [
            {"treatment_name": "Chronic medication adherence", "dose": "as per chart", "frequency": "daily", "route": "oral", "notes": "Medication education", "is_active": True},
            {"treatment_name": "Dietary management", "dose": "NA", "frequency": "daily", "route": "nutrition", "notes": "Condition-based diet", "is_active": True},
        ],
    }

    allowed_department_names = {name for name, _ in department_specs}
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM departments WHERE org_id = 1 AND department_name NOT IN (?, ?, ?, ?, ?, ?)",
            tuple(allowed_department_names),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    for dept_index, (department, department_code) in enumerate(department_specs, start=1):
        for patient_index in range(1, 6):
            first_name = first_names[patient_index - 1]
            last_name = last_names[(dept_index + patient_index - 2) % len(last_names)]
            patient_code = f"P-{dept_index:02d}-{patient_index:02d}"
            ward = f"Ward-{chr(64 + dept_index)}"
            bed_no = f"{chr(64 + dept_index)}-{10 + patient_index}"
            age = 28 + (dept_index * 4) + patient_index
            diagnosis = diagnosis_by_department[department]
            summary = f"{department} case under active nursing monitoring."
            alias_names = f"{first_name.lower()},patient {first_name.lower()},{first_name.lower()} {last_name.lower()}"

            upsert_patient_record(
                org_id=1,
                patient_code=patient_code,
                first_name=first_name,
                last_name=last_name,
                age=age,
                gender="Male" if patient_index % 2 else "Female",
                diagnosis=diagnosis,
                department=department,
                ward=ward,
                bed_no=bed_no,
                primary_doctor=f"Dr. Dept{dept_index}",
                status="admitted",
                summary=summary,
                alias_names=alias_names,
                treatments=treatment_by_department[department],
                department_code=department_code,
            )

def store_user_query(username, query, response):
    if not is_valid_username(username):
        return "⚠️ Invalid username format."
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_chat (username, query, response)
        VALUES (?, ?, ?)
    """, (username, query, str(response)))
    conn.commit()
    conn.close()
    return "✅ Query stored in database."


def get_recent_user_messages(username: str, limit: int = 8):
    if not is_valid_username(username):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT query
            FROM user_chat
            WHERE username = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (username, limit),
        )
        rows = cursor.fetchall()
        # oldest -> newest order for better conversational continuity
        return [row[0] for row in rows[::-1] if row and row[0]]
    finally:
        cursor.close()
        conn.close()

def get_user_queries(username, query, k=10):
    if not is_valid_username(username):
        return "⚠️ Invalid username format."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT query, response FROM user_chat
        WHERE username = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (username, k))

    past_queries = cursor.fetchall()
    conn.close()

    if past_queries:
        reversed_queries = past_queries[::-1]
        formatted_queries = "\n".join([f"User: {q}\nResponse: {r}" for q, r in reversed_queries])
        prompt = (
            f"You are a highly knowledgeable medical assistant with expertise in nursing domain expertise.\n"
            f"Based on the following medical data:\n{formatted_queries}\n\n"
            f"Based on user and response think the user {query} and answer from provided {formatted_queries} match both user and response.\n"
            f"Question: {query}"
        )
        return query_gemini(prompt)

    return "❌ No previous queries found for your username."







def store_uploaded_item(name, item_type, org_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get current time as ISO formatted string
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO uploaded_items (name, type, timestamp, org_id)
        VALUES (?, ?, ?, ?)
    """, (name, item_type, current_time, org_id))
    
    conn.commit()
    conn.close()


# def get_recent_uploaded_items():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT name, type, timestamp
#         FROM uploaded_items
#         ORDER BY timestamp DESC
#     """)
#     rows = cursor.fetchall()
#     conn.close()
#     return rows

def get_recent_uploaded_items():
    """
    Fetch recent uploaded items including organisation name.
    Joins `uploaded_items` and `organisation` tables on org_id.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                u.name, 
                u.type, 
                u.timestamp, 
                o.organisation_name
            FROM uploaded_items u
            LEFT JOIN organisation o ON u.org_id = o.org_id
            ORDER BY u.timestamp DESC
        """)
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()



def validate_admin_credentials(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
    result = cursor.fetchone()
    conn.close()
    return result is not None




def get_organisations():
    """Fetch all organisations (id + name only)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT org_id, organisation_name FROM organisation")
        rows = cursor.fetchall()
        return [{"org_id": row[0], "organisation_name": row[1]} for row in rows]
    finally:
        cursor.close()
        conn.close()







def get_org_system_prompt(org_id: int) -> str:
    import sqlite3
    conn = sqlite3.connect("user_queries.sqlite")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT system_prompt FROM organisation WHERE org_id = ?", (org_id,))
        row = cursor.fetchone()
        if row:
            return row[0]
        else:
            raise Exception(f"No system prompt found for org_id={org_id}")
    finally:
        conn.close()



def validate_faqs(faqs: Any):
    """Validate FAQ structure before inserting into DB."""
    if isinstance(faqs, dict):
        first_value = next(iter(faqs.values()), None)
        if isinstance(first_value, list):
            # Category dict
            for category, items in faqs.items():
                for faq in items:
                    if "question" not in faq or "answer" not in faq:
                        raise ValueError(f"Missing 'question' or 'answer' in category '{category}'")
        else:
            # Flat dict
            for question, answer in faqs.items():
                if not isinstance(question, str) or not isinstance(answer, str):
                    raise ValueError("Questions and answers must be strings")
    elif isinstance(faqs, list):
        for faq in faqs:
            if "question" not in faq or "answer" not in faq:
                raise ValueError("Each FAQ must have 'question' and 'answer'")
    else:
        raise ValueError("FAQs must be dict or list")


def replace_faqs(org_id: int, faqs: Any):
    """Delete old FAQs and insert new ones."""
    import sqlite3
    from backend import DB_PATH, add_faqs

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM faq WHERE org_id = ?", (org_id,))
        conn.commit()
        if faqs:
            add_faqs(org_id, faqs)
    finally:
        conn.close()


def update_system_prompt(org_id: int, system_prompt: str):
    """Update the system prompt for a given organisation."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE organisation SET system_prompt = ? WHERE org_id = ?",
            (system_prompt, org_id)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def update_organisation(org_name: str, system_prompt: str = None, faqs: Any = None):
    """Update system prompt and/or FAQs for an organisation."""
    # Get org_id
    org_id = get_org_id(org_name)

    # Update system prompt if provided
    if system_prompt is not None:
        update_system_prompt(org_id, system_prompt)

    # Update FAQs if provided
    if faqs is not None:
        validate_faqs(faqs)
        replace_faqs(org_id, faqs)


def update_user_password(username: str, new_password: str, organisation_name: str):
    """Admin resets a user's password, verifying organisation."""
    username = username.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Get org_id from organisation_name
        cursor.execute("SELECT org_id FROM organisation WHERE organisation_name = ?", (organisation_name.strip().lower(),))
        org_row = cursor.fetchone()
        if not org_row:
            return False, f"Organisation '{organisation_name}' not found."
        org_id = org_row[0]

        # Update password only if username matches org_id
        hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ? AND org_id = ?",
            (hashed_pw, username, org_id)
        )
        conn.commit()

        if cursor.rowcount == 0:
            return False, f"User '{username}' not found in organisation '{organisation_name}'."
        return True, "Password updated successfully."
    finally:
        cursor.close()
        conn.close()


ensure_patient_tables()
seed_default_patients()
