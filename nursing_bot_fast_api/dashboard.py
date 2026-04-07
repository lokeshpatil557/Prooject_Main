import sqlite3
from collections import Counter
from datetime import datetime
import pandas as pd

DB_PATH = "user_queries.sqlite"
def get_total_nurses():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_most_frequent_questions(top_n=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT query FROM user_chat")
    queries = [row[0] for row in cursor.fetchall()]
    conn.close()
    return Counter(queries).most_common(top_n)

def get_document_upload_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT type FROM uploaded_items")
    types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return Counter(types)

def get_recent_active_nurses(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, MAX(timestamp)
        FROM user_chat
        GROUP BY username
        ORDER BY MAX(timestamp) DESC
        LIMIT ?
    """, (limit,))
    recent = cursor.fetchall()
    conn.close()
    return recent

def get_upload_counts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT type, COUNT(*) FROM uploaded_items GROUP BY type")
    rows = cursor.fetchall()
    conn.close()

    counts = {"pdf": 0, "url": 0}
    for t, count in rows:
        counts[t] = count
    return counts

def get_total_uploads():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM uploaded_items")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_chat_query_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_chat")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_top_users_by_queries(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, COUNT(*) as query_count
        FROM user_chat
        GROUP BY username
        ORDER BY query_count DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    return pd.DataFrame(rows, columns=["Username", "Query Count"])

def get_upload_trend():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp FROM uploaded_items")
    rows = cursor.fetchall()
    conn.close()

    dates = []
    for ts in rows:
        raw_ts = ts[0]
        if raw_ts:
            try:
                parsed = datetime.fromisoformat(str(raw_ts))
                dates.append(parsed.strftime("%Y-%m"))
            except ValueError:
                pass  # Skip bad timestamps

    return pd.Series(dates).value_counts().sort_index()


def get_avg_queries_per_user():
    total_users = get_total_nurses()
    total_queries = get_chat_query_count()
    return total_queries / total_users if total_users else 0


def get_most_active_nurse():
    df = get_top_users_by_queries(limit=1)
    return df.iloc[0]["Username"], df.iloc[0]["Query Count"] if not df.empty else ("N/A", 0)

# def get_most_active_nurse():
#     df = get_top_users_by_queries(limit=1)
#     if not df.empty:
#         return df.iloc[0]["Username"], df.iloc[0]["Query Count"]
#     else:
#         return "N/A", 0

def get_top_uploaded_items(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, COUNT(*) as count
        FROM uploaded_items
        GROUP BY name
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))
    data = cursor.fetchall()
    conn.close()
    return data





def get_daily_upload_trend(days=7):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT DATE(timestamp) as day, COUNT(*) 
        FROM uploaded_items
        WHERE timestamp >= DATE('now', '-{days} days')
        GROUP BY day
        ORDER BY day ASC
    """)
    data = cursor.fetchall()
    conn.close()
    return pd.DataFrame(data, columns=["Date", "Upload Count"]).set_index("Date")



def get_chat_trend():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp FROM user_chat")
    rows = cursor.fetchall()
    conn.close()

    dates = []
    for ts in rows:
        raw_ts = ts[0]
        if raw_ts:
            try:
                parsed = datetime.fromisoformat(str(raw_ts))
                dates.append(parsed.strftime("%Y-%m"))
            except ValueError:
                continue
    return pd.Series(dates).value_counts().sort_index()




def get_inactive_nurses():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username FROM users
        WHERE username NOT IN (
            SELECT DISTINCT username FROM user_chat
        )
    """)
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users





