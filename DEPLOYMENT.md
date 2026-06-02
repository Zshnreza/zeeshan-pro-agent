# Deployment Guide

## Public Safety

Before publishing:

- Rotate any API key that was pasted into a terminal or chat.
- Do not commit `.env`.
- Do not commit `.streamlit/secrets.toml`.
- Do not commit private profile files, memory files, approval queues, trackers, run reports, passport files, CVs, payslips, transcripts, or screenshots.
- Public users should bring their own Groq API key in the sidebar, or you can set a deployment secret if you intentionally want to pay for usage.

## Deploy On Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Open Streamlit Community Cloud.
3. Create a new app from the repository.
4. Set the main file path:

```text
src/chat_app.py
```

5. Add secrets only if you want server-managed keys:

```toml
GROQ_API_KEY = "..."
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
TAVILY_API_KEY = ""
SERPAPI_API_KEY = ""
```

6. Deploy.

## Deploy On Render

Use these settings:

- Environment: Python
- Build command:

```bash
pip install -r requirements.txt
```

- Start command:

```bash
streamlit run src/chat_app.py --server.port $PORT --server.address 0.0.0.0
```

Add environment variables in Render's dashboard if needed.

## Local Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run src/chat_app.py
```
