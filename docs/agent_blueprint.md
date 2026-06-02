# Agent Blueprint

## Mission

Build a personal autonomous work system that can execute one-instruction tasks while keeping sensitive actions behind approval.

Example instruction:

> Find AI/data science master's programs in Europe where I am eligible, prepare my application documents, and show me what to approve.

## Agents

### 1. Orchestrator Agent

- Reads the user's instruction.
- Breaks it into a plan.
- Chooses which specialist agents should act.
- Stops when the task is complete or requires approval.

### 2. Europe University Agent

- Searches official university and admissions pages.
- Checks tuition, eligibility, language requirements, deadlines, intake, application portal, and scholarship options.
- Produces a ranked shortlist.
- Never invents eligibility or deadlines.

### 3. Europe Jobs Agent

- Searches jobs aligned to profile.
- Prioritizes roles with visa sponsorship, relocation support, English-language fit, or global hiring.
- Drafts tailored CV bullets and cover letters.
- Flags likely blockers.

### 4. Document Agent

- Drafts SOPs, motivation letters, CV variants, cover letters, emails, and checklists.
- Uses the redacted profile and asks for missing details.
- Never fabricates grades, work dates, passport details, salary, or certifications.

### 5. Verification Agent

- Checks facts against sources and documents.
- Detects missing eligibility proof.
- Produces a confidence score and citations for researched opportunities.

### 6. Approval Agent

- Creates a final approval package.
- Requires explicit user approval before submission, uploading identity documents, sending emails, paying fees, or accepting terms.

### 7. Self-Improvement Agent

- Saves outcomes, rejections, feedback, and successful documents.
- Updates preference memory.
- Creates eval cases from failures.
- Suggests prompt/tool improvements.

## Workflow

1. Receive instruction.
2. Load redacted profile and memories.
3. Build a plan.
4. Research opportunities.
5. Verify facts from official/current sources.
6. Rank options.
7. Draft documents.
8. Run quality and safety checks.
9. Present approval package.
10. After approval, execute allowed action.
11. Save outcome and learning notes.

## Hosting Pattern

- App: Streamlit or FastAPI hosted on Render, Railway, Fly.io, AWS, or Hugging Face Spaces.
- LLM inference: Groq or Hugging Face hosted APIs.
- Vector memory: Qdrant Cloud.
- Documents: encrypted cloud storage or private repository storage.
- CI/evals: GitHub Actions with DeepEval.

## Non-Negotiable Rules

- Do not submit applications without approval.
- Do not upload passport, tax, payslip, or identity documents without approval.
- Do not claim language scores, grades, job titles, salary, or work dates unless verified.
- Prefer official sources for university requirements.
- For immigration/legal/visa requirements, cite official government or university sources and treat the result as guidance, not legal advice.
- Keep sensitive details redacted in logs and chat summaries.
