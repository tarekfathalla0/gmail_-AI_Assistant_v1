# AI Gmail Assistant

An AI-powered Gmail Assistant built with **FastAPI**, **LangGraph**, **MCP (Model Context Protocol)**, **Google Gmail API**, and **OpenRouter**.

The assistant can authenticate with Gmail using OAuth 2.0, interact with the Gmail API through MCP tools, and answer natural language requests such as:

- "Show me my latest 5 emails."
- "Find emails from Google."
- "Send an email to John."
- "Create a draft."
- "Archive this email."
- "Reply to the latest message."

---

# Features

## Authentication

- Google OAuth 2.0
- Offline Access (Refresh Token)
- Automatic Access Token Refresh
- Persistent Token Storage

---

## Gmail Operations

- List latest emails
- Search emails
- Read email details
- Send emails
- Reply to emails
- Delete emails
- Archive emails
- Trash / Restore emails
- Mark as Read / Unread
- Star / Unstar emails
- Create drafts
- List drafts
- Send drafts
- Delete drafts

---

## AI Agent

Built using **LangGraph ReAct Agent**.

The agent can:

- Understand natural language
- Decide when to use Gmail tools
- Execute MCP tools automatically
- Return a human-friendly response

Example:

> Show me the latest email from tarek@gmail.com

The agent automatically:

1. Searches Gmail
2. Finds the correct email
3. Reads the email
4. Returns the result

---

## Conversation Memory

The assistant supports conversation memory using **LangGraph MemorySaver**.

Example:

User:

```
My name is Tarek.
```

Later:

```
Who am I?
```

Assistant:

```
You are Tarek.
```

Conversation state is maintained using a configurable `thread_id`.

---

## LangSmith

The project is fully integrated with **LangSmith** for:

- Trace visualization
- Agent debugging
- Tool execution history
- Prompt inspection
- Token usage
- Performance monitoring

---

# Tech Stack

- Python 3.13
- FastAPI
- LangGraph
- LangChain
- OpenRouter
- Gmail API
- Google OAuth 2.0
- MCP (Model Context Protocol)
- FastMCP
- httpx
- Pydantic
- uv
- LangSmith

---

# Project Structure

```
.
├── app.py
├── config.py
├── auth.py
├── gmail_client.py
├── token_manager.py
├── mcp_server.py
├── mcp_client.py
├── agent.py
├── routers/
│   ├── auth_router.py
│   ├── gmail_router.py
│   └── agent_router.py
├── schemas/
├── .env
└── README.md
```

---

# API Endpoints

## Authentication

| Method | Endpoint |
|----------|----------------|
| GET | `/auth/login` |
| POST | `/auth/exchange` |
| GET | `/auth/me` |
| POST | `/auth/logout` |

---

## Gmail

| Method | Endpoint |
|----------|----------------|
| GET | `/gmail/messages` |
| GET | `/gmail/messages/{id}` |
| POST | `/gmail/send` |
| POST | `/gmail/reply` |
| POST | `/gmail/draft` |
| GET | `/gmail/drafts` |

---

## AI Agent

```
POST /agent/run
```

Example Request

```json
{
    "thread_id":"tarek",
    "message":"Show me my latest 5 emails."
}
```

Example Response

```json
{
    "response":"Here are your latest five emails..."
}
```

---

# MCP Tools

The agent communicates with Gmail through MCP tools.

Available tools include:

- list_emails
- search_emails
- get_email
- send_email
- reply_email
- create_draft
- list_drafts
- send_draft
- delete_draft
- delete_email
- archive_message
- trash_message
- untrash_message
- mark_read
- mark_unread
- star_message
- unstar_message

---

# Running the Project

Clone the repository

```bash
git clone <repository-url>
```

Install dependencies

```bash
uv sync
```

Run the FastAPI server

```bash
uv run uvicorn app:app --reload
```

Open Swagger

```
http://127.0.0.1:8000/docs
```

---

# Environment Variables

```env
CLIENT_ID=
CLIENT_SECRET=
REDIRECT_URI=

OPENROUTER_API_KEY=

LANGSMITH_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=AI-Gmail-Agent
```

---

# Example Workflow

1. Authenticate with Google OAuth.
2. Store access and refresh tokens.
3. Start the FastAPI server.
4. Send a request to `/agent/run`.
5. The AI agent decides which Gmail tool to use.
6. The MCP server executes the Gmail API request.
7. The agent summarizes the result and returns a natural language response.

---

# Future Improvements

- Streaming responses (SSE/WebSocket)
- Persistent conversation memory (PostgreSQL/Redis)
- RAG over emails
- Email summarization
- Attachment support
- Calendar integration
- Multi-agent workflow
- Background task processing
- Docker deployment
- CI/CD pipeline

---

# Author

**Tarek Fathalla**

Agentic AI & Automation Engineer

Built with ❤️ using FastAPI, LangGraph, MCP, Gmail API, and OpenRouter.
