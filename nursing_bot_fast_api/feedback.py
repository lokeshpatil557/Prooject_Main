# import streamlit as st
import sqlite3

DB_PATH = "user_queries.sqlite"
from datetime import datetime

def insert_feedback(name, rating, suggestion):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        INSERT INTO feedback (username, rating, suggestion, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (name, rating, suggestion, timestamp))

    conn.commit()
    conn.close()



# #Work with streamlit session state to track feedback submission
# def get_feedback():
#     st.subheader("📝 Chatbot Feedback")

#     st.write("Please rate your experience and share any suggestions you may have:")

#     rating = st.radio("1. How would you rate your chatbot experience?", [1, 2, 3, 4, 5], key="rating", index=None)
#     suggestion = st.text_area("2. Any suggestions or comments?", key="suggestion")

#     if st.button("Submit Feedback"):
#         username = st.session_state.get("username", "anonymous")  # fallback if session missing
#         insert_feedback(username, rating, suggestion)
#         st.success("✅ Thank you for your feedback!")
#         st.session_state["feedback_given"] = True

