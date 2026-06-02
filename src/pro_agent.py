from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from europe_opportunity_agent import PROFILE_PATH, llm


load_dotenv()


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RUN_DIR = ROOT / "runs"
MEMORY_PATH = DATA_DIR / "pro_memory.json"
APPROVALS_PATH = DATA_DIR / "approval_queue.json"
TRACKER_PATH = DATA_DIR / "opportunity_tracker.json"

RUN_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


PRO_SYSTEM = """
You are Zeeshan Pro Agent, a production-minded personal AI operating system.

Core behavior:
- Work like a planner, researcher, writer, verifier, and approval manager.
- Be specific, operational, and honest about uncertainty.
- Prefer official sources for university, visa, and application facts.
- Never fabricate identity details, grades, IELTS scores, salary, work dates, admissions requirements, or job sponsorship.
- Do not claim that an application was submitted, an email was sent, a file was uploaded, or a fee was paid unless the user explicitly approved and the action truly happened.
- Any external action involving applications, emails, uploads, payments, accounts, or sensitive documents must be placed in the approval queue first.
- Keep sensitive personal data minimized and redacted in summaries.
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_profile() -> str:
    if PROFILE_PATH.exists():
        return PROFILE_PATH.read_text(encoding="utf-8")
    return ""


def get_memory() -> list[dict[str, Any]]:
    return read_json(MEMORY_PATH, [])


def save_memory(entry: dict[str, Any]) -> None:
    memory = get_memory()
    memory.insert(0, {"created_at": now_iso(), **entry})
    write_json(MEMORY_PATH, memory[:200])


def get_approvals() -> list[dict[str, Any]]:
    return read_json(APPROVALS_PATH, [])


def add_approval(title: str, action: str, risk: str, payload: str) -> dict[str, Any]:
    approvals = get_approvals()
    item = {
        "id": f"appr_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(approvals) + 1}",
        "created_at": now_iso(),
        "status": "PENDING",
        "title": title,
        "action": action,
        "risk": risk,
        "payload": payload,
    }
    approvals.insert(0, item)
    write_json(APPROVALS_PATH, approvals)
    return item


def update_approval(approval_id: str, status: str) -> None:
    approvals = get_approvals()
    for item in approvals:
        if item["id"] == approval_id:
            item["status"] = status
            item["updated_at"] = now_iso()
            break
    write_json(APPROVALS_PATH, approvals)


def get_tracker() -> list[dict[str, Any]]:
    return read_json(TRACKER_PATH, [])


def add_tracker_row(row: dict[str, Any]) -> None:
    rows = get_tracker()
    rows.insert(0, {"created_at": now_iso(), **row})
    write_json(TRACKER_PATH, rows[:500])


def tavily_search(query: str, max_results: int) -> list[dict[str, str]]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    response = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "search_depth": "basic", "max_results": max_results},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "source": "tavily",
        }
        for item in data.get("results", [])
    ]


def serpapi_search(query: str, max_results: int) -> list[dict[str, str]]:
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        return []
    response = httpx.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": api_key, "num": max_results},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "source": "serpapi",
        }
        for item in data.get("organic_results", [])[:max_results]
    ]


def duckduckgo_html_search(query: str, max_results: int) -> list[dict[str, str]]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": "Mozilla/5.0 ZeeshanProAgent/1.0"}
    response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    response.raise_for_status()
    html = response.text
    blocks = re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', html, flags=re.S)
    snippets = re.findall(r'<a class="result__snippet".*?>(.*?)</a>', html, flags=re.S)
    results = []
    for index, (href, title_html) in enumerate(blocks[:max_results]):
        title = re.sub("<.*?>", "", title_html)
        snippet = re.sub("<.*?>", "", snippets[index]) if index < len(snippets) else ""
        results.append(
            {
                "title": html_unescape(title),
                "url": html_unescape(href),
                "snippet": html_unescape(snippet),
                "source": "duckduckgo-html",
            }
        )
    return results


def html_unescape(value: str) -> str:
    replacements = {
        "&amp;": "&",
        "&quot;": '"',
        "&#x27;": "'",
        "&#39;": "'",
        "&lt;": "<",
        "&gt;": ">",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return re.sub(r"\s+", " ", value).strip()


def live_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    for provider in (tavily_search, serpapi_search, duckduckgo_html_search):
        try:
            results = provider(query, max_results)
            if results:
                return results
        except Exception:
            continue
    return []


def generate_queries(instruction: str, task_type: str) -> list[str]:
    profile = read_profile()
    model = llm()
    prompt = f"""
Create 4 high-signal web search queries for this task.
Return only a JSON array of strings.

Task type: {task_type}
Instruction: {instruction}

Redacted profile:
{profile[:5000]}
"""
    try:
        content = model.invoke([SystemMessage(content=PRO_SYSTEM), HumanMessage(content=prompt)]).content
        match = re.search(r"\[.*\]", content, flags=re.S)
        if match:
            parsed = json.loads(match.group(0))
            return [str(item) for item in parsed][:4]
    except Exception:
        pass

    if task_type == "University":
        return [
            "site:daad.de international programmes AI data science master tuition Germany public university",
            "site:study.eu public university data science master low tuition Europe",
            "site:mastersportal.com AI data science master Europe tuition IELTS 6.0",
            "site:universityadmissions.se data science master's English tuition non EU",
        ]
    if task_type == "Jobs":
        return [
            "Europe junior AI engineer visa sponsorship Python SQL",
            "Europe ML data associate data analyst jobs English visa sponsorship",
            "Germany data analyst machine learning junior jobs English relocation",
            "Netherlands junior data scientist English visa sponsorship",
        ]
    return [instruction]


def research_sources(instruction: str, task_type: str, max_results: int = 5) -> tuple[list[str], list[dict[str, str]]]:
    queries = generate_queries(instruction, task_type)
    sources: list[dict[str, str]] = []
    seen = set()
    for query in queries:
        for item in live_search(query, max_results=max_results):
            url = item.get("url", "")
            if url and url not in seen:
                seen.add(url)
                item["query"] = query
                sources.append(item)
    return queries, sources[:20]


def source_digest(sources: list[dict[str, str]]) -> str:
    if not sources:
        return "No live sources were found. Ask the user to add Tavily or SerpAPI for stronger live research."
    lines = []
    for idx, source in enumerate(sources, start=1):
        lines.append(
            f"{idx}. {source.get('title', 'Untitled')}\n"
            f"   URL: {source.get('url', '')}\n"
            f"   Snippet: {source.get('snippet', '')}\n"
            f"   Search: {source.get('query', '')}"
        )
    return "\n".join(lines)


def run_pro_task(
    instruction: str,
    task_type: str = "Auto",
    live_research: bool = True,
    max_results: int = 5,
) -> dict[str, Any]:
    profile = read_profile()
    memory = get_memory()[:12]
    queries: list[str] = []
    sources: list[dict[str, str]] = []
    if live_research:
        queries, sources = research_sources(instruction, task_type, max_results=max_results)

    prompt = f"""
Run a pro agent task.

Instruction:
{instruction}

Task type:
{task_type}

Redacted profile:
{profile}

Recent durable memory:
{json.dumps(memory, indent=2)[:7000]}

Live web sources:
{source_digest(sources)}

Produce a professional run report with these sections:
1. Executive decision
2. Work plan
3. Findings or output
4. Best opportunities or actions, in a table when useful
5. Eligibility/fit analysis
6. Risks and unknowns
7. Approval queue items
8. Next 7 actions

If sources are weak or missing, say so. Do not pretend a source proves more than it proves.
"""
    model = llm()
    report = model.invoke([SystemMessage(content=PRO_SYSTEM), HumanMessage(content=prompt)]).content

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_path = RUN_DIR / f"{run_id}.md"
    run_path.write_text(report, encoding="utf-8")

    save_memory(
        {
            "type": "pro_run",
            "task_type": task_type,
            "instruction": instruction,
            "run_id": run_id,
            "summary": report[:1200],
            "source_count": len(sources),
        }
    )
    add_tracker_row(
        {
            "kind": task_type,
            "title": instruction[:120],
            "status": "RESEARCHED",
            "source_count": len(sources),
            "run_id": run_id,
        }
    )
    approval = add_approval(
        title=f"Review next actions for {task_type}",
        action="Approve selected emails, applications, uploads, or submissions only after reviewing the run report.",
        risk="External submissions may transmit personal data or create binding application records.",
        payload=report[:5000],
    )

    return {
        "run_id": run_id,
        "run_path": str(run_path),
        "report": report,
        "queries": queries,
        "sources": sources,
        "approval": approval,
    }


def pro_chat(prompt: str, mode: str, document_context: str = "", use_profile: bool = True) -> str:
    profile = read_profile() if use_profile else ""
    memory = get_memory()[:8]
    system = f"{PRO_SYSTEM}\nCurrent mode: {mode}"
    user = f"""
User prompt:
{prompt}

Redacted profile:
{profile}

Recent durable memory:
{json.dumps(memory, indent=2)[:5000]}

Temporary document context:
{document_context[:12000]}
"""
    model = llm()
    return model.invoke([SystemMessage(content=system), HumanMessage(content=user)]).content
