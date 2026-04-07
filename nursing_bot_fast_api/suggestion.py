import sqlite3
from collections import Counter

DB_PATH = "user_queries.sqlite"

def get_most_frequent(top_n=3):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Step 1: Fetch all queries
    cursor.execute("SELECT query FROM user_chat")
    queries = [row[0] for row in cursor.fetchall()]

    # Step 2: Count top N questions
    top_questions = Counter(queries).most_common(top_n)

    # Step 3: For each question, fetch one response
    results = []
    for question, _ in top_questions:
        cursor.execute("SELECT response FROM user_chat WHERE query = ? LIMIT 1", (question,))
        response = cursor.fetchone()
        if response:
            results.append((question, response[0]))  # (question, answer)

    conn.close()
    return results
