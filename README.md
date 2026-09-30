# OpenAI API Learning Ladder

A project-first path from a simple OpenAI CLI call to RAG, MCP, multi-agent workflows, and evals. One Python/`uv` monorepo. Stages stay independently runnable.

Planning lives in **`Temp/`** (gitignored): the ladder spec and progress tracker stay there until each stage has its own project files and README.

Teaching write-ups live in **`Docs/`** (gitignored until we choose to publish): line-by-line *why*, diagrams, and walkthroughs created when a stage is implemented.

## Stages (planned)

| # | Project |
|---|---------|
| 1 | LLM CLI Assistant |
| 2 | Structured Data Extractor |
| 3 | FastAPI Foundations (no OpenAI) |
| 4 | FastAPI AI Service |
| 5 | Small Chatbot |
| 6 | Telegram AI Bot |
| 7 | Document Q&A — Simple RAG |
| 8 | Document Intelligence — Medium RAG |
| 9 | PostgreSQL AI Agent via MCP |
| 10 | Multi-Tool Agent |
| 11 | Multi-Agent Workflow |
| 12 | Capstone — RAG + MCP + Agent |
| 13 | Evals, Optimization, and Best Practices |

Implemented so far:

- Stage 1: [LLM CLI Assistant](projects/01_llm_cli_assistant/README.md)
- Stage 2: [Structured Data Extractor](projects/02_structured_data_extractor/README.md)
- Stage 3: [FastAPI Foundations](projects/03_fastapi_foundations/README.md)

Later stage folders appear as each project is implemented.

## Public repo notes

- **License:** [MIT](LICENSE)
- **Crawlers:** [robots.txt](robots.txt) and [ai.txt](ai.txt) ask AI/training scrapers not to ingest this tree. Ordinary search indexing is allowed.

Copy `.env.example` to `.env` locally. Do not commit secrets.

## New chat bootstrap (maintainers)

Open this folder as the workspace. Agents should read `AGENTS.md` and `.cursor/rules/`. Local plan (not published): `Temp/openai_api_learning_project_ladder.md`.
