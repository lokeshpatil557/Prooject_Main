AI Chatbot Project with Multilingual Support

This project is an AI-powered chatbot interface that uses Langchain, sqlitevec, and other advanced libraries. It also supports multilingual capabilities including English, Spanish, and Chinese, with translation handled via googletrans.

Langfuse tracing is now wired into the nurse chat flow so you can inspect each request end-to-end in a local Langfuse instance.

🛠️ Setup Instructions

1. Clone the repository

git clone https://github.com/your-username/your-repo.git
cd your-repo

2. Create a Virtual Environment

python -m venv venv

3. Activate the Virtual Environment

Windows

venv\Scripts\activate.bat

macOS/Linux

source venv/bin/activate.bat

📦 Install Dependencies

Step 1: Install all packages from requirements.txt **excluding **``

Ensure your requirements.txt does **not include **`` to avoid conflicts.

pip install --no-cache-dir -r requirements.txt

Step 2: Install guardrails-ai hub  Separately

guardrails hub install hub://guardrails/toxic_language

This avoids version conflicts with guardrail.

✅ Verifying Installation

To check that everything is installed correctly:

pip list

🚀 Running the Application

After installation, you can run the chatbot app using:

uvicorn new_fast_api:app --reload --port 8080
uvicorn fast_api:app --reload

📝 Notes

If you encounter dependency issues, try deleting the venv folder and repeating the installation process.

Local Langfuse setup

1. Install the Python SDK dependency from `requirement.txt`.

2. Point the app to your local Langfuse instance in `.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
# optional, same purpose as LANGFUSE_HOST
# LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_TRACING_ENVIRONMENT=local
```

3. Start the API as usual:

```bash
uvicorn new_fast_api:app --reload --port 8080
```

How Langfuse is used in this code

- Each nurse WebSocket message creates one root trace called `nurse-chat-request`.
- Input validation is logged as a guardrail observation named `validate-user-input`.
- Document retrieval is logged as a retriever observation named `retrieve-relevant-docs`.
- Gemini calls are logged in `gemini_api.py` as a generation observation named `gemini-generate-content`.
- The final assistant response is attached back to the root trace so you can see the whole lifecycle in one place.

Files involved

- `new_fast_api.py`: starts the trace around each incoming chat message.
- `gemini_api.py`: records the actual Gemini generation, parameters, output, and token usage when available.
- `langfuse_helper.py`: keeps Langfuse optional and safe, so the app still runs when Langfuse is not configured.

