# AI Code Agent (VS Code Extension + FastAPI Agent + Qdrant)

An AI powered code assistant that works like a lightweight “agent” in VS Code. It can edit code, fix errors, apply multi file workspace changes, and generate repo aware tests by indexing your project into Qdrant for retrieval augmented generation.

---

## Table of Contents
- [What this project is](#what-this-project-is)
- [Why I built it (personal motivation)](#why-i-built-it-personal-motivation)
- [Key capabilities](#key-capabilities)
- [Tech stack](#tech-stack)
- [High level architecture](#high-level-architecture)
- [How it works (end to end flow)](#how-it-works-end-to-end-flow)
- [Backend API endpoints](#backend-api-endpoints)
- [Local setup and run](#local-setup-and-run)
- [Using the VS Code extension](#using-the-vs-code-extension)
- [Troubleshooting](#troubleshooting)
- [Future scope](#future-scope)
- [Contributors](#contributors)
- [License and rights](#license-and-rights)

---

## What this project is

AI Code Agent is a two part system:

1. **FastAPI Agent Service**
   - Exposes endpoints like `/edit`, `/workspace_edit`, `/workspace_edit_repo`, `/index/start`
   - Talks to OpenAI for reasoning and code generation
   - Uses Qdrant to store and retrieve embeddings for repo aware understanding

2. **VS Code Extension**
   - Adds commands in VS Code like “AI: Edit Selection”, “AI: Fix Error”, “AI: Workspace Edit”, “AI: Index Repo”
   - Sends the current file, user instruction, and repository context to the agent
   - Applies returned diffs to the workspace safely

The guiding principle is simple: the agent proposes edits, the extension applies them. This keeps the system safe and transparent.

---

## Why I built it (personal motivation)

I wanted a practical AI assistant that fits into my development workflow and doesn’t feel like a black box. My day to day work often involves switching between files, debugging errors, generating tests, and scaffolding new code. Existing tools can be either too heavy, too opaque, or not tuned for repo wide understanding.

This project was motivated by a few direct needs:

- I wanted a VS Code command that can make precise edits with a diff shown every time
- I wanted an error fixer that takes a traceback and patches code safely
- I wanted multi file edits because real engineering tasks rarely happen in a single file
- I wanted better test generation that understands the entire repository, not just one file
- I wanted an architecture where I can keep improving agent behaviors (indexing, retrieval, quality loops) without rewriting the extension

---

## Key capabilities

- **AI: Edit Selection**
  - Takes a natural language instruction and updates the current file
  - Prints unified diff and warnings
  - Applies edits and saves the document

- **AI: Fix Error**
  - Takes traceback or error output and patches code to resolve it
  - Includes selected snippet as additional context

- **AI: Workspace Edit**
  - Supports multi file create and modify operations
  - Can generate `tests/test_<module>.py` automatically if instruction implies tests
  - Applies file operations to the workspace and creates directories when needed

- **AI: Index Repo**
  - Indexes the repo into Qdrant (chunking and embeddings)
  - Enables repo aware retrieval for better test generation and code changes

- **Repo aware workspace edit (RAG)**
  - `/workspace_edit_repo` scans and summarizes repo
  - Uses Qdrant retrieval to pull the most relevant code chunks
  - Produces better, context aware outputs such as complete test suites

---

## Tech stack

### Backend
- Python
- FastAPI
- Uvicorn
- OpenAI API (chat completions and embeddings)
- Qdrant (vector database)
- qdrant-client
- httpx (used internally by qdrant-client)
- Pydantic (request and response models)

### Extension
- TypeScript
- VS Code Extension API
- Axios

---

## High level architecture

```text
+---------------------------+              +------------------------------+
|        VS Code UI         |              |        Qdrant Vector DB      |
|  Commands and Editors     |              |  repo_chunks collection      |
+-------------+-------------+              +---------------+--------------+
              |                                            ^
              | HTTP (axios)                               |
              v                                            |
+---------------------------+              +------------------------------+
|     FastAPI Agent         |  embeddings  |  Indexing + Retrieval Layer  |
| /edit /workspace_edit     +------------->|  chunking, embed, search     |
| /workspace_edit_repo      |              +------------------------------+
| /index/start /index/status|
+-------------+-------------+
              |
              | OpenAI API (chat + embeddings)
              v
+---------------------------+
|        OpenAI Models      |
+---------------------------+

## How It Works (End-to-End Flow)

### Editing and Patching Flow

1. You run a VS Code command such as "AI: Edit Selection"
2. The extension collects:
   - Current file path (repo relative)
   - Current file text
   - Selection (optional)
   - Instruction you typed
3. The extension calls the backend endpoint
4. Backend calls OpenAI and generates:
   - `updated_text`
   - `unified_diff`
   - `warnings` (if any)
5. Extension shows diff in Output Channel and applies the changes

### Repo Aware Flow with Embeddings

1. You run "AI: Index Repo"
2. Backend scans repo and chunks relevant files
3. Backend generates embeddings and stores them in Qdrant
4. Later, when you call `/workspace_edit_repo`:
   - Backend embeds your instruction
   - Searches Qdrant for top relevant chunks
   - Includes those chunks in the prompt context
   - Model outputs multi-file operations for better accuracy and coverage

## Backend API Endpoints

### Health

**GET** `/health`

**Purpose:** Basic service health check and key loading validation

**Example Response:**
```json
{
  "status": "ok",
  "openai_key_loaded": true
}
```

### Single File Edit

**POST** `/edit`

**Purpose:** Apply an instruction to a single file and return a diff and updated text

**Request:**
```json
{
  "instruction": "Add type hints and a docstring. Keep behavior identical.",
  "file_path": "sample.py",
  "original_text": "def add(a,b):\n  return a+b\n",
  "user_context": "User selected snippet..."
}
```

**Response:**
```json
{
  "file_path": "sample.py",
  "unified_diff": "--- a/sample.py\n+++ b/sample.py\n...",
  "updated_text": "def add(a: int, b: int) -> int:\n  ...",
  "warnings": []
}
```

### Multi-File Workspace Edit (Explicit File List)

**POST** `/workspace_edit`

**Purpose:** Create or modify multiple files, but only among the provided file list. This is safe and deterministic because the allow list is explicit.

**Request:**
```json
{
  "instruction": "Create pytest tests for add() and put them in tests/test_sample.py",
  "files": [
    {
      "file_path": "sample.py",
      "original_text": "..."
    },
    {
      "file_path": "tests/test_sample.py",
      "original_text": null
    }
  ],
  "user_context": "Use pytest style.",
  "max_files": 10
}
```

**Response:**
```json
{
  "operations": [
    {
      "file_path": "tests/test_sample.py",
      "action": "create",
      "updated_text": "...",
      "unified_diff": "",
      "warnings": []
    }
  ],
  "warnings": []
}
```

### Repo Aware Workspace Edit (RAG Powered)

**POST** `/workspace_edit_repo`

**Purpose:** Repo-aware edits using repo scanning and Qdrant retrieval. This is best for generating complete test suites and scaffolding tasks.

**Request:**
```json
{
  "instruction": "Generate pytest tests for key services and routes",
  "repo_root": "D:\\path\\to\\repo",
  "scope_paths": ["."],
  "allowed_root_dirs": ["tests"],
  "max_files": 200,
  "max_bytes": 2000000,
  "intent": "generate_tests",
  "user_context": "Follow project conventions."
}
```

**Response:** Same shape as `/workspace_edit`

### Indexing (Qdrant)

**POST** `/index/start`

**Purpose:** Start indexing repo into Qdrant in a background thread

**Request:**
```json
{
  "repo_root": "D:\\path\\to\\repo",
  "scope_paths": ["."],
  "max_files": 500,
  "max_bytes": 2000000
}
```

**Response:**
```json
{
  "job_id": "uuid..."
}
```

**GET** `/index/status/{job_id}`

**Purpose:** Poll indexing status

**Response:**
```json
{
  "job_id": "uuid...",
  "status": "done",
  "started_at": 123.45,
  "finished_at": 130.12,
  "result": {
    "indexed_chunks": 29,
    "indexed_files": 25
  },
  "error": null
}
```

## Local Setup and Run

### Prerequisites

- Python 3.10+ (recommended)
- Node.js 18+ (recommended)
- VS Code
- OpenAI API key
- Docker (recommended for Qdrant)

### 1) Backend Setup (FastAPI Agent)

**Create virtual environment (Windows PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Create `.env` file:**
```env
OPENAI_API_KEY=your_key_here
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=repo_chunks
EMBED_MODEL=text-embedding-3-small
```

**Run the API server:**
```bash
uvicorn agent.app.main:app --reload --port 8787
```

### 2) Run Qdrant

**Option A (recommended): Docker**
```bash
docker run -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant:latest
```

**Validate Qdrant:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:6333/collections" -Method Get
```

### 3) Index the Repo

**From PowerShell:**
```powershell
$body = @{
  repo_root = "D:\Abhishek\Syracuse\UpScale\ai-code-agent"
  scope_paths = @(".")
  max_files = 200
  max_bytes = 2000000
} | ConvertTo-Json -Depth 10

$start = Invoke-RestMethod -Uri "http://localhost:8787/index/start" -Method Post -ContentType "application/json" -Body $body
$job = $start.job_id

Invoke-RestMethod -Uri "http://localhost:8787/index/status/$job" -Method Get | ConvertTo-Json -Depth 10
```

## Using the VS Code Extension

### Build Extension

Inside `extension/` folder:
```bash
npm install
npm run compile
```

### Run Extension Host

1. Open VS Code
2. Press **F5** to launch Extension Development Host
3. Open a Python repo in the Extension Host window

### Available Commands

- **AI: Edit Selection** - Edit selected code with AI assistance
- **AI: Fix Error** - Fix runtime errors automatically
- **AI: Workspace Edit** - Multi-file edits and scaffolding
- **AI: Index Repo** - Index repository for RAG-powered operations

### Typical Flow

1. Run **AI: Index Repo** once per repo (or after major changes)
2. Use **AI: Workspace Edit** to generate tests or scaffold code
3. Use **AI: Fix Error** when you hit runtime issues
4. Use **AI: Edit Selection** for targeted refactors

## Troubleshooting

### Qdrant Errors: `getaddrinfo failed`

- Set `QDRANT_URL=http://127.0.0.1:6333` in `.env`
- Confirm Qdrant is running
- Confirm `http://127.0.0.1:6333/collections` responds

### Index Job Status Shows Error

Check `error` field in `/index/status/{job_id}`

**Most common issues:**
- Qdrant not reachable
- Missing dependencies
- Repo path incorrect

### Extension Can't Connect to Backend

- Confirm FastAPI runs on `http://localhost:8787`
- Confirm extension setting `aiCodeAgent.baseUrl` matches backend URL

## Future Scope

- Qdrant incremental indexing (only changed files)
- Multi-repo profiles and persistent workspace state
- Quality loop for tests: generate tests → run pytest → auto-fix failures and retry once
- Ruff and mypy loops for lint and typing improvements
- Inline autocompletion endpoint (`/complete`) for Copilot-like UX
- Better retrieval: embeddings + symbol graph + import graph
- Authentication and rate limiting for production deployment
- UI improvements: side panel previews, diff views inside VS Code

## Contributors

**Abhishek Umesh Gavali** (owner and primary developer)

If you want to contribute:
1. Fork the repo
2. Create a feature branch
3. Open a PR with a clear description of changes and test steps

## License and Rights

All rights reserved. This project and its source code are proprietary. You may not copy, modify, distribute, or use any part of this repository without explicit permission from the owner.

© 2026 Abhishek Umesh Gavali. All rights reserved.