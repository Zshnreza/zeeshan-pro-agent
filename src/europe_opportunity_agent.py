from __future__ import annotations

import os
import argparse
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph


load_dotenv()


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PROFILE_PATH = ROOT / "data" / "profile_redacted.md"
PROFILE_TEMPLATE_PATH = ROOT / "data" / "profile_template.md"
PROFILE_PATH = PRIVATE_PROFILE_PATH if PRIVATE_PROFILE_PATH.exists() else PROFILE_TEMPLATE_PATH


class AgentState(TypedDict, total=False):
    user_instruction: str
    profile: str
    plan: str
    university_research: str
    job_research: str
    drafts: str
    verification: str
    approval_package: str
    approved: bool
    next_step: Literal["research", "draft", "verify", "approval", "done"]


def llm(
    api_key: str | None = None,
    base_url: str | None = None,
    model_name: str | None = None,
    temperature: float = 0.2,
) -> ChatOpenAI:
    """Use hosted inference. Groq exposes an OpenAI-compatible API."""
    return ChatOpenAI(
        api_key=api_key or os.environ.get("GROQ_API_KEY"),
        base_url=base_url or os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        model=model_name or os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=temperature,
    )


def load_profile(state: AgentState) -> AgentState:
    profile = PROFILE_PATH.read_text(encoding="utf-8")
    return {"profile": profile, "next_step": "research"}


def plan_work(state: AgentState) -> AgentState:
    model = llm()
    prompt = f"""
You are the Orchestrator Agent for a personal Europe opportunity automation system.

User instruction:
{state["user_instruction"]}

Redacted profile:
{state["profile"]}

Create a concise task plan. Include what must be researched, drafted, verified, and approved.
Do not include sensitive identity numbers.
"""
    return {"plan": model.invoke(prompt).content, "next_step": "research"}


def research_opportunities(state: AgentState) -> AgentState:
    model = llm()
    prompt = f"""
You are a Europe University and Jobs Research Agent.

Use this profile and plan to define search tasks for official public university pages and reputable job boards.
Because live web tools are not wired in this starter file, produce a structured research checklist and search queries.

Profile:
{state["profile"]}

Plan:
{state["plan"]}

Return:
1. University search strategy
2. Job search strategy
3. Eligibility filters
4. Data fields to capture
"""
    content = model.invoke(prompt).content
    return {"university_research": content, "job_research": content, "next_step": "draft"}


def draft_documents(state: AgentState) -> AgentState:
    model = llm()
    prompt = f"""
You are the Document Agent.

Create first-draft templates for:
- University motivation letter
- Job cover letter
- Email to admissions office
- Missing information checklist

Use only verified profile facts below. Mark unknowns as [TO CONFIRM].

Profile:
{state["profile"]}

Plan:
{state["plan"]}
"""
    return {"drafts": model.invoke(prompt).content, "next_step": "verify"}


def verify_package(state: AgentState) -> AgentState:
    model = llm()
    prompt = f"""
You are the Verification Agent.

Review the plan, research checklist, and drafts. Flag:
- unsupported claims
- missing documents
- facts requiring official source verification
- actions that require user approval

Profile:
{state["profile"]}

Plan:
{state["plan"]}

Research:
{state["university_research"]}

Drafts:
{state["drafts"]}
"""
    return {"verification": model.invoke(prompt).content, "next_step": "approval"}


def create_approval_package(state: AgentState) -> AgentState:
    package = f"""
# Approval Package

## Instruction
{state["user_instruction"]}

## Plan
{state["plan"]}

## Research Tasks
{state["university_research"]}

## Drafts
{state["drafts"]}

## Verification
{state["verification"]}

## Approval Needed

No application, email, upload, payment, or account submission should happen until the user explicitly approves.
"""
    return {"approval_package": package, "next_step": "done"}


def route(state: AgentState) -> str:
    return state.get("next_step", "done")


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_profile", load_profile)
    graph.add_node("plan", plan_work)
    graph.add_node("research", research_opportunities)
    graph.add_node("draft", draft_documents)
    graph.add_node("verify", verify_package)
    graph.add_node("approval", create_approval_package)

    graph.set_entry_point("load_profile")
    graph.add_edge("load_profile", "plan")
    graph.add_conditional_edges(
        "plan",
        route,
        {"research": "research", "draft": "draft", "verify": "verify", "approval": "approval", "done": END},
    )
    graph.add_conditional_edges(
        "research",
        route,
        {"draft": "draft", "verify": "verify", "approval": "approval", "done": END},
    )
    graph.add_conditional_edges(
        "draft",
        route,
        {"verify": "verify", "approval": "approval", "done": END},
    )
    graph.add_conditional_edges(
        "verify",
        route,
        {"approval": "approval", "done": END},
    )
    graph.add_edge("approval", END)
    return graph.compile()


def run(instruction: str) -> AgentState:
    app = build_graph()
    return app.invoke({"user_instruction": instruction})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Europe opportunity agent.")
    parser.add_argument(
        "instruction",
        nargs="?",
        default="Find free or low-tuition AI/data science master's programs and Europe jobs matching my profile. Prepare what I need to approve.",
        help="The work instruction for the agent.",
    )
    args = parser.parse_args()

    result = run(args.instruction)
    print(result["approval_package"])
