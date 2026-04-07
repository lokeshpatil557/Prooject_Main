# import sqlite3

# DB_PATH = "user_queries.sqlite"



# conn = sqlite3.connect(DB_PATH)
# cursor = conn.cursor()


# # # Delete the existing table
# # cursor.execute("DROP TABLE IF EXISTS feedback")
# # print("✅ Existing feedback table dropped.")

# # Create users table
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS users (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     username TEXT UNIQUE NOT NULL,
#     password TEXT NOT NULL
# )
# """)

##Create uploaded_items table main code
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS uploaded_items (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL,                -- Name of the file or URL
#     type TEXT CHECK(type IN ('pdf', 'url')) NOT NULL,  -- Either 'pdf' or 'url'
#     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP       -- Upload timestamp
# )
# """)

# ##For all documents
# # cursor.execute("""
# # CREATE TABLE IF NOT EXISTS uploaded_items (
# #     id INTEGER PRIMARY KEY AUTOINCREMENT,
# #     name TEXT NOT NULL,                -- Name of the file or URL
# #     type TEXT CHECK(type IN ('document', 'url')) NOT NULL,  -- 'document' instead of 'pdf'
# #     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP            -- Upload timestamp
# # )
# # """)




# # Modify user_queries table to use username instead of email
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS user_chat (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     username TEXT NOT NULL,
#     query TEXT NOT NULL,
#     response TEXT NOT NULL,
#     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (username) REFERENCES users(username)
# )
# """)

# conn.commit()
# conn.close()

# print("✅ users and user_queries tables created.")





# cursor.execute('''
#     CREATE TABLE IF NOT EXISTS feedback (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         username TEXT,
#         suggestion TEXT,
#         rating INTEGER,
#         timestamp TEXT DEFAULT CURRENT_TIMESTAMP
#     )
# ''')

# conn.commit()
# conn.close()


# print("✅ users and user_queries tables created.")





# # import sqlite3
# # import pandas as pd

# # conn = sqlite3.connect(DB_PATH)
# # df = pd.read_sql_query("SELECT * FROM users", conn)
# # conn.close()

# # print(df)



# import sqlite3

# # Connect to (or create) the database file
# conn = sqlite3.connect("user_queries.sqlite")

# # Create a cursor object to execute SQL commands
# cursor = conn.cursor()

# # Create the 'admins' table if it doesn't already exist
# cursor.execute('''
#     CREATE TABLE IF NOT EXISTS admins (
#         username TEXT PRIMARY KEY,
#         password TEXT NOT NULL
#     )
# ''')

# # Insert a default admin user (username: 'admin', password: 'admin123')
# cursor.execute('''
#     INSERT OR IGNORE INTO admins (username, password)
#     VALUES (?, ?)
# ''', ("admin", "admin123"))

# # Commit changes and close the connection
# conn.commit()
# conn.close()

# print("Database and admin user created successfully.")


# ##For deleting
# # import sqlite3

# # # Connect to the database
# # conn = sqlite3.connect(DB_PATH)
# # cursor = conn.cursor()

# # # Delete user where username is 'susan'
# # cursor.execute("DELETE FROM users WHERE username = ?", ("susan",))

# # # Commit changes and close connection
# # conn.commit()
# # conn.close()

# # print("User 'susan' deleted successfully.")



# import sqlite3

# DB_PATH = "user_queries.sqlite"
# TABLE_NAME = "sql_vect"

# conn = sqlite3.connect(DB_PATH)
# cursor = conn.cursor()

# # Delete all records from the table
# cursor.execute(f"DELETE FROM {TABLE_NAME}")
# conn.commit()

# # Check how many rows are left
# cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
# row_count = cursor.fetchone()[0]
# print(f"Number of records remaining in {TABLE_NAME}: {row_count}")
# cursor.close()
# conn.close()

# if row_count == 0:
#     print("✅ Successfully deleted all records from the table.")
# else:
#     print(f"⚠️ {row_count} records still remain in the table.")


# import sqlite3

# DB_PATH = "user_queries.sqlite"

# def create_table():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
    
#     # Create organisation table if not exists
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS organisation (
#         org_id INTEGER PRIMARY KEY AUTOINCREMENT,
#         organisation_name TEXT UNIQUE NOT NULL,
#         system_prompt TEXT NOT NULL
#     )
#     """)
    
#     conn.commit()
#     cursor.close()
#     conn.close()
#     print("✅ organisation table created (if not already present).")

# if __name__ == "__main__":
#     create_table()

# import sqlite3

# # Path to your SQLite database
# db_path = 'user_queries.sqlite'

# # Connect to the database
# conn = sqlite3.connect(db_path)
# cursor = conn.cursor()

# # Get the table structure (columns)
# cursor.execute("PRAGMA table_info(organisations);")
# columns = cursor.fetchall()
# print("Table Columns:")
# for col in columns:
#     print(col)

# # Fetch all data from the table
# cursor.execute("SELECT * FROM organisation")
# rows = cursor.fetchall()

# print("\nTable Data:")
# for row in rows:
#     print(row)

# # Close the connection
# conn.close()




# import sqlite3

# DB_PATH = "user_queries.sqlite"

# conn = sqlite3.connect(DB_PATH)
# cursor = conn.cursor()

# # Create users table with org_id
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS users (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     username TEXT UNIQUE NOT NULL,
#     password TEXT NOT NULL,
#     org_id INTEGER DEFAULT 1, 
#     FOREIGN KEY (org_id) REFERENCES organisation(org_id)
# )
# """)

# conn.commit()
# cursor.close()
# conn.close()
# print("✅ Users table created/updated with org_id column.")




# import sqlite3

# DB_PATH = "user_queries.sqlite"

# def show_users():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     cursor.execute("SELECT * FROM users")
#     rows = cursor.fetchall()

#     print("👥 Users Table Data:")
#     for row in rows:
#         print(row)

#     cursor.close()
#     conn.close()

# if __name__ == "__main__":
#     show_users()


# import sqlite3

# DB_PATH = "user_queries.sqlite"

# def migrate_users_table():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     # 1. Add org_id column if not exists
#     cursor.execute("PRAGMA table_info(users)")
#     columns = [col[1] for col in cursor.fetchall()]

#     if "org_id" not in columns:
#         cursor.execute("ALTER TABLE users ADD COLUMN org_id INTEGER DEFAULT 1")
#         print("✅ Added org_id column to users table.")

#     # 2. Update existing users -> set org_id = 1
#     cursor.execute("UPDATE users SET org_id = 1 WHERE org_id IS NULL")
#     conn.commit()

#     cursor.close()
#     conn.close()
#     print("✅ Migration completed. All existing users assigned org_id = 1.")

# if __name__ == "__main__":
#     migrate_users_table()


# import sqlite3

# DB_PATH = "user_queries.sqlite"

# conn = sqlite3.connect(DB_PATH)
# cursor = conn.cursor()

# # Step 1: Check if org_id already exists
# cursor.execute("PRAGMA table_info(uploaded_items)")
# columns = [col[1] for col in cursor.fetchall()]

# if "org_id" not in columns:
#     # Step 2: Add org_id column with default 1
#     cursor.execute("ALTER TABLE uploaded_items ADD COLUMN org_id INTEGER DEFAULT 1")

#     # Step 3: Update existing rows to have org_id = 1
#     cursor.execute("UPDATE uploaded_items SET org_id = 1 WHERE org_id IS NULL")

#     conn.commit()
#     print("✅ org_id column added to uploaded_items with default value 1")
# else:
#     print("ℹ️ org_id column already exists")

# cursor.close()
# conn.close()




# import sqlite3

# # Path to your SQLite database
# db_path = 'user_queries.sqlite'

# # Connect to the database
# conn = sqlite3.connect(db_path)
# cursor = conn.cursor()

# # 🔎 List all tables in DB
# cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
# tables = cursor.fetchall()
# print("Tables in database:")
# for t in tables:
#     print(" -", t[0])

# print("\n--- Organisation Table Structure ---")
# # 🔎 Show columns for organisation table
# cursor.execute("PRAGMA table_info(organisation);")
# columns = cursor.fetchall()
# for col in columns:
#     print(col)

# print("\n--- Organisation Table Data ---")
# # 🔎 Fetch all rows from organisation table
# cursor.execute("SELECT * FROM organisation;")
# rows = cursor.fetchall()
# for row in rows:
#     print(row)

# # Close connection
# conn.close()


# import sqlite3

# DB_PATH = "user_queries.sqlite"

# def create_faq_table():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     # Create faq table if not exists
#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS faq (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         org_id INTEGER NOT NULL,
#         category TEXT,
#         question TEXT NOT NULL,
#         answer TEXT NOT NULL,
#         FOREIGN KEY (org_id) REFERENCES organisation(org_id) ON DELETE CASCADE
#     )
#     """)

#     conn.commit()
#     cursor.close()
#     conn.close()
#     print("✅ faq table created (if not already present).")

# if __name__ == "__main__":
#     create_faq_table()




# import sqlite3

# DB_PATH = "user_queries.sqlite"

# def show_tables():
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()

#     # 🔍 Show organisation table
#     print("\n---- Organisation Table ----")
#     try:
#         cursor.execute("SELECT * FROM organisation;")
#         rows = cursor.fetchall()
#         col_names = [desc[0] for desc in cursor.description]
#         print(" | ".join(col_names))
#         for row in rows:
#             print(row)
#     except Exception as e:
#         print("Organisation table missing or empty:", e)

#     # 🔍 Show faq table
#     print("\n---- FAQ Table ----")
#     try:
#         cursor.execute("SELECT * FROM faq;")
#         rows = cursor.fetchall()
#         col_names = [desc[0] for desc in cursor.description]
#         print(" | ".join(col_names))
#         for row in rows:
#             print(row)
#     except Exception as e:
#         print("FAQ table missing or empty:", e)

#     # 🔍 Join query to see FAQs grouped by organisation
#     print("\n---- Organisation with FAQs ----")
#     try:
#         cursor.execute("""
#             SELECT 
#                 o.org_id,
#                 o.organisation_name,
#                 f.id AS faq_id,
#                 f.category,
#                 f.question,
#                 f.answer
#             FROM organisation o
#             LEFT JOIN faq f ON o.org_id = f.org_id;
#         """)
#         rows = cursor.fetchall()
#         col_names = [desc[0] for desc in cursor.description]
#         print(" | ".join(col_names))
#         for row in rows:
#             print(row)
#     except Exception as e:
#         print("Join query failed:", e)

#     cursor.close()
#     conn.close()

# if __name__ == "__main__":
#     show_tables()



# import sqlite3
# import json

# DB_PATH = "user_queries.sqlite"

# # JSON data (your FAQ dump)
# faq_data = {
#   "faq": [
#     {
#       "category": "Policies and Procedures",
#       "question": "Where can I find the most up-to-date version of a specific hospital policy?",
#       "answer": "Our hospital maintains an online repository for all active policies and procedures, accessible through the intranet. Look for the 'Policy and Procedure Manual' or 'Clinical Resources' section. You can search by keyword, policy number, or department. If you can't find what you're looking for, contact your department manager or the Policy Committee."
#     },
#     {
#       "category": "Policies and Procedures",
#       "question": "What is the procedure for reporting a deviation from a policy or procedure?",
#       "answer": "If you witness or become aware of a deviation from a policy or procedure that could potentially compromise patient safety or quality of care, you are required to report it. The preferred method is through our incident reporting system (e.g., RL Solutions, Quantros), accessible through the intranet. You can also report it directly to your supervisor or the Risk Management department. We have a non-punitive reporting culture, so you will not be penalized for reporting in good faith."
#     },
#     {
#       "category": "Policies and Procedures",
#       "question": "If a policy seems outdated or impractical, what's the process for suggesting a revision?",
#       "answer": "We encourage staff to provide feedback on policies. There is a dedicated form on the intranet's Policy and Procedure page to submit suggested revisions. Your suggestion will be reviewed by the relevant policy committee. You will receive feedback on the status of your suggestion."
#     },
#     {
#       "category": "Policies and Procedures",
#       "question": "What are the key policies I need to know regarding patient privacy and HIPAA?",
#       "answer": "The most important policies to review are the 'Confidentiality and Privacy of Patient Information' policy, the 'Social Media Use' policy, and the 'Electronic Health Record (EHR) Access and Security' policy. These outline how to protect patient information and comply with HIPAA regulations. Annual HIPAA training is mandatory."
#     },
#     {
#       "category": "Policies and Procedures",
#       "question": "What's the hospital's policy on mandatory overtime and call schedules?",
#       "answer": "The 'Staffing and Scheduling' policy addresses staffing ratios, on-call requirements, fair distribution of overtime, and procedures for declining overtime. This aligns with state regulations and any collective bargaining agreements."
#     },
#     {
#       "category": "Policies and Procedures",
#       "question": "What is the policy on patient identification and medication administration verification?",
#       "answer": "Always adhere to the Two-Patient-Identifier policy. Confirm both the patient’s full name and date of birth before any medication is administered. Verify against the ID band, medical record, or EMR to prevent errors."
#     },
#     {
#       "category": "Medication Interaction",
#       "question": "The electronic prescribing system flagged a potential interaction, but I don't think it's clinically significant. What should I do?",
#       "answer": "Never disregard an alert completely. If you believe the interaction is not clinically significant, consult with the prescribing physician and clinical pharmacist. Document the discussion and rationale in the patient record."
#     },
#     {
#       "category": "Medication Interaction",
#       "question": "What resources can I use to quickly check for medication interactions outside of the electronic prescribing system?",
#       "answer": "Use the hospital-approved references like Lexicomp or Micromedex available on nursing units. You may also contact the on-call pharmacist. Do NOT use unverified online sources."
#     },
#     {
#       "category": "Medication Interaction",
#       "question": "What is the hospital's policy on administering medications brought in by patients from home?",
#       "answer": "Use of patient-supplied medications must be authorized by the prescribing physician. These medications must be labeled, verified by pharmacy, securely stored, and documented in the patient’s profile according to the 'Medication Management' policy."
#     },
#     {
#       "category": "Medication Interaction",
#       "question": "What are the procedures for administering high-alert medications (e.g., insulin, heparin, opioids)?",
#       "answer": "High-alert medications require independent double-checks by two qualified nurses. This includes confirming the drug, dose, route, timing, and patient identification prior to administration."
#     },
#     {
#       "category": "Medication Interaction",
#       "question": "How do I document medication administration, including any reactions or interactions?",
#       "answer": "Document drug name, dose, route, time, and site in the EHR promptly. For adverse reactions, include detailed symptoms, vital signs, interventions, and notify the physician and pharmacy immediately."
#     },
#     {
#       "category": "Medication Interaction",
#       "question": "What action needs to be taken if the doctor has given an incorrect dose for a specific patient?",
#       "answer": "Contact the doctor immediately upon identifying the error. Escalate to the charge nurse or higher authority if necessary to ensure correction."
#     },
#     {
#       "category": "Clinical Pathways",
#       "question": "How do I access the clinical pathway for a specific condition?",
#       "answer": "Clinical pathways are available in the EHR under the 'Clinical Pathway' section. You can search by condition name or ICD-10 code. Paper copies may be available in select units, but EHR is the primary source."
#     },
#     {
#       "category": "Clinical Pathways",
#       "question": "What if a patient on a clinical pathway refuses a specific intervention (e.g., physical therapy)?",
#       "answer": "Respect patient autonomy. Document the refusal, the reason, and any education provided. Notify the physician and discuss alternative options."
#     },
#     {
#       "category": "Clinical Pathways",
#       "question": "The clinical pathway doesn't seem to address a specific co-morbidity the patient has. Should I deviate from the pathway?",
#       "answer": "Yes, when clinically justified. Consult with the physician or specialist. Document the deviation and rationale clearly in the patient chart."
#     },
#     {
#       "category": "Clinical Pathways",
#       "question": "How often are clinical pathways reviewed and updated?",
#       "answer": "They are reviewed at least annually or sooner if prompted by changes in evidence-based guidelines. The Clinical Practice Committee oversees this process."
#     },
#     {
#       "category": "Clinical Pathways",
#       "question": "What are the benefits of using clinical pathways in my daily practice?",
#       "answer": "They promote evidence-based care, reduce complications, improve outcomes, and enhance team coordination. Clinical pathways also streamline workflow and documentation."
#     },
#     {
#       "category": "Clinical Pathways",
#       "question": "What is the hospital policy if a clinical pathway is not followed?",
#       "answer": "Deviations must be justified with valid clinical reasoning and documented. Unexplained deviations may be subject to review or audit by clinical leadership."
#     }
#   ]
# }

# # Insert into DB
# conn = sqlite3.connect(DB_PATH)
# cursor = conn.cursor()

# for item in faq_data["faq"]:
#     cursor.execute("""
#         INSERT INTO faq (org_id, category, question, answer)
#         VALUES (?, ?, ?, ?)
#     """, (1, item["category"], item["question"], item["answer"]))

# conn.commit()
# cursor.close()
# conn.close()

# print("✅ FAQs inserted for org_id=1")


# import sqlite3

# # Connect to your SQLite database
# conn = sqlite3.connect("user_queries.sqlite")
# cursor = conn.cursor()

# # Table to check
# table_name = "organisation"

# # --- Get column information ---
# cursor.execute(f"PRAGMA table_info({table_name});")
# columns = cursor.fetchall()

# print("Columns in table:", table_name)
# for col in columns:
#     print(f"{col[1]} (Type: {col[2]})")

# # --- Get all organisations with their system prompts ---
# cursor.execute(f"SELECT organisation_name, system_prompt FROM {table_name};")
# rows = cursor.fetchall()

# if rows:
#     print("\nOrganisation name and system prompt:")
#     for org_name, system_prompt in rows:
#         print(f"Organisation: {org_name}")
#         print(f"System Prompt: {system_prompt}\n")
# else:
#     print("\nNo data found in the organisation table.")

# # --- Optionally, check only 'tript' organisation ---
# cursor.execute("SELECT organisation_name, system_prompt FROM organisation WHERE organisation_name = 'tript';")
# tript_row = cursor.fetchone()
# if tript_row:
#     print("Specific check for 'tript':")
#     print(f"Organisation: {tript_row[0]}")
#     print(f"System Prompt: {tript_row[1]}")
# else:
#     print("Organisation 'tript' not found.")

# # Close the connection
# conn.close()


# import sqlite3

# # Connect to SQLite database
# conn = sqlite3.connect("user_queries.sqlite")
# cursor = conn.cursor()

# # Fetch all data from the 'faq' table
# cursor.execute("SELECT * FROM faq;")
# rows = cursor.fetchall()

# # Get column names
# cursor.execute("PRAGMA table_info(faq);")
# columns = [col[1] for col in cursor.fetchall()]

# # Print all rows with column names
# if rows:
#     print("All rows in 'faq' table:\n")
#     for row in rows:
#         for col_name, value in zip(columns, row):
#             print(f"{col_name}: {value}")
#         print("-" * 40)
# else:
#     print("No data found in 'faq' table.")

# # Close connection
# conn.close()



# import sqlite3

# db_path = "user_queries.sqlite"  # <-- your DB file

# conn = sqlite3.connect(db_path)
# cursor = conn.cursor()

# # Show all tables including vector-related or hidden ones
# cursor.execute("""
# SELECT name, type 
# FROM sqlite_master 
# WHERE type IN ('table', 'view') 
# ORDER BY type, name;
# """)

# rows = cursor.fetchall()

# print("\nObjects in database:")
# for name, obj_type in rows:
#     print(f"{obj_type}: {name}")

# conn.close()



# import sqlite3

# db_path = "user_queries.sqlite"  # your DB file

# conn = sqlite3.connect(db_path)
# cursor = conn.cursor()

# # Tables that should not be cleared
# protected_tables = [
#     "admins",
#     "sql_vect",
#     "sql_vect_vec",
#     "sql_vect_vec_chunks",
#     "sql_vect_vec_info",
#     "sql_vect_vec_rowids",
#     "sql_vect_vec_vector_chunks00",
# ]

# cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
# tables = [t[0] for t in cursor.fetchall()]

# cursor.execute("PRAGMA foreign_keys = OFF;")

# for table in tables:
#     if table not in protected_tables:
#         cursor.execute(f'DELETE FROM "{table}";')
#         print(f"Cleared data from: {table}")
#     else:
#         print(f"SKIPPED (protected or vector): {table}")

# # Reset autoincrement counters
# cursor.execute("DELETE FROM sqlite_sequence;")

# conn.commit()
# cursor.execute("PRAGMA foreign_keys = ON;")
# conn.close()

# print("\n✔ All user data cleared successfully!")




# import sqlite3

# conn = sqlite3.connect("user_queries.sqlite")
# cursor = conn.cursor()

# cursor.execute("PRAGMA table_info(sql_vect);")
# columns = cursor.fetchall()

# for col in columns:
#     print(col)

# conn.close()



# import sqlite3

# db_path = "user_queries.sqlite"
# conn = sqlite3.connect(db_path)
# cursor = conn.cursor()

# cursor.execute("UPDATE sql_vect SET text = NULL;")
# conn.commit()
# conn.close()

# print("Content cleared from sql_vect!")


import sqlite3

DB_FILE = "user_queries.sqlite"
TABLE_NAME = "sql_vect"

def clean_vector_data():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Deletes ONLY the stored data
        cursor.execute(f"DELETE FROM {TABLE_NAME};")

        conn.commit()
        conn.close()

        print("🧹 All stored vector data removed from sql_vect table! (DB + table structure is safe)")
    except Exception as e:
        print(f"❌ Error cleaning vector data: {e}")

clean_vector_data()


