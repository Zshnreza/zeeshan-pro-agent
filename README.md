# Zeeshan Pro Agent

An open-source, ChatGPT-style personal agent workspace for hosted LLM workflows.

It can help with:

- Europe public university discovery and application preparation
- Europe job search and application preparation
- CV/SOP/cover-letter drafting
- Document checklist tracking
- Human approval before submissions or external actions
- Self-improvement through saved outcomes and evaluation notes

The system is designed to use hosted inference APIs such as Groq or Hugging Face Inference Providers, plus managed vector storage such as Qdrant Cloud. It does not require local GPU/CPU model hosting for LLM inference.

Public users can enter their own Groq API key in the app sidebar. For a hosted deployment, you can also set API keys as deployment secrets.

## Core Stack

- Python
- LangGraph
- LangChain
- FastAPI or Streamlit for the interface
- Qdrant Cloud for long-term memory/RAG
- Groq or Hugging Face for hosted open-source LLM inference
- DeepEval, Guardrails AI, and Microsoft Presidio for evaluation and safety

## Safety Rule

The agents can research, draft, rank, and prepare applications automatically. They must ask for explicit user approval before:

- Submitting university/job applications
- Sending email or messages
- Uploading identity documents
- Paying fees
- Accepting terms
- Making claims about experience, grades, finances, or immigration status

## Files

- `data/profile_redacted.md`: redacted career/education profile inferred from your files
- `data/profile_template.md`: public-safe profile template
- `docs/agent_blueprint.md`: architecture and operating rules
- `src/europe_opportunity_agent.py`: LangGraph starter workflow
- `src/pro_agent.py`: pro task runner with memory, live search, tracker, and approval queue
- `src/chat_app.py`: ChatGPT-style Streamlit app and pro-agent control panel
- `.env.example`: cloud API settings
- `DEPLOYMENT.md`: GitHub and deployment guide

Private local files such as `.env`, `data/profile_redacted.md`, memory JSON files, approval queues, trackers, and run reports are ignored by git.

## Next Build Steps

1. Add cloud API keys in a local `.env`.
2. Add source documents into a private document store.
3. Connect Qdrant Cloud for memory and RAG.
4. Add search tools for official university pages and job boards.
5. Add a Streamlit dashboard for approvals and trackers.

## Local MVP Install

Use Python 3.12 for the basic agent:

```bash
python -m pip install -r requirements.txt
python src/europe_opportunity_agent.py
```

Run the ChatGPT-style app:

```bash
streamlit run src/chat_app.py
```

For stronger live research, add either `TAVILY_API_KEY` or `SERPAPI_API_KEY` to `.env`.
Without those keys, the app attempts a lightweight web search fallback.

## Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md).

Install the optional production safety/evaluation stack separately:

```bash
python -m pip install -r requirements-safety.txt
```

If the optional safety stack fails on Python 3.12, use a Python 3.11 virtual environment for that part.
