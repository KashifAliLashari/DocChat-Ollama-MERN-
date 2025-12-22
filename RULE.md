---
alwaysApply: true
---
This is a substantial project. I have rewritten the project rules based on the provided project description and your detailed answers, fitting them into your provided template.

Here is the master blueprint for your offline PDF RAG chatbot.

# 🚀 PROJECT MASTER BLUEPRINT: Ollama Offline PDF Chatbot

## 1. TECH STACK & ARCHITECTURE (Context Layering)
- **Core Backend:** **Python 3.11+**, **FastAPI** (with `uvicorn`, SSE via `StreamingResponse`; WebSockets optional)
- **RAG/AI:** **Ollama** (via Python SDK) with **LlamaIndex** for RAG orchestration
- **Vector DB:** **ChromaDB** (embedded, persistent) or **Qdrant** (local/single binary)
- **Embeddings:** **Ollama embeddings** (e.g., `nomic-embed-text`, `mxbai-embed-large`)
- **Traditional DB:** **SQLite** (via `sqlite3` or `better-sqlite3`) for metadata/history
- **PDF Parsing:** **PyMuPDF (fitz)** for fast extraction with page-level metadata
- **Frontend Framework:** **React** with **Vite** (TypeScript mandatory)
- **State Management:** **Zustand** for UI state + **TanStack Query** for server state/cache
- **UI/UX:** **shadcn/ui** (primary), **react-markdown**
- **Role:** Act as **Full-Stack AI Engineer** prioritizing offline capability and performance.

## 2. THE VIBE (Aesthetic & Persona)
- **Objective:** **Provide a fast, reliable, context-aware, GPT-like chat experience completely offline based on user-uploaded PDFs.**
- **Visual Style:** Clean, minimalist, modern chat interface (similar to ChatGPT or Linear) with focus on readability. Dark mode preferable.
- **Persona:** Professional, local, secure, and focused on knowledge extraction.
- **Inspiration:** ChatGPT's core UI/UX for chat and context management.

## 3. CORE FEATURES & USER STORIES (MVP)
- **MVP Requirement 1:** User can **upload one or more PDFs** and see them listed.
- **MVP Requirement 2:** The system must process and **embed documents immediately** using **local Ollama embeddings**.
- **MVP Requirement 3:** User can start a **multi-turn chat** and receive responses streamed token-by-token from Ollama (prefer **SSE**; WebSocket optional).
- **MVP Requirement 4:** Responses must include **citations** (document name and page number) from the retrieved context chunks.
- **MVP Requirement 5:** All **chat history and sessions must be saved** persistently to SQLite and displayed in a sidebar.

## 4. CONSTRAINTS & CODING STANDARDS (Offline & RAG Focus)
- **Offline First:** Absolutely **no external API calls** (except for the local Ollama instance).
- **RAG Integrity:** **Embeddings are CRITICAL.** Use **LlamaIndex + Ollama embeddings + ChromaDB/Qdrant**; raw keyword search is forbidden.
- **Stream Processing:** All large I/O (PDF upload, Ollama responses) **must be streamed/async** (prefer **SSE** for chat streaming).
- **Strict Typing:** Mandatory TypeScript/Python type hints (`typing` module) across the entire stack.
- **Security:** Sanitize user inputs before passing to Ollama. Manage PDF files securely on the local filesystem. Parse PDFs via **PyMuPDF** with controlled paths.

## 5. ARCHITECTURAL DECISIONS
- **Core Pattern:** **Retrieval Augmented Generation (RAG)** pipeline.
- **Communication:** Prefer **FastAPI SSE** (`StreamingResponse`) for real-time chat streaming; **FastAPI REST** for document management/history; WebSockets optional if bidirectional needed.
- **Data Flow:** **[User Query] $\rightarrow$ [Vector DB Search via ChromaDB/Qdrant] $\rightarrow$ [Ollama Prompt with Context from LlamaIndex] $\rightarrow$ [Streamed Response (SSE)]**.
- **State Management (Frontend):** **Zustand** for UI state + **TanStack Query** for server data (sessions, docs, messages).

## 6. PROJECT PATTERNS (CRITICAL)
- **Backend (Python):** Utilize **LlamaIndex** for all RAG steps (loading, chunking, embedding via Ollama, retrieval via ChromaDB/Qdrant).
- **Vector Store:** Default to **ChromaDB** for persistence and metadata filtering; support **Qdrant** as an alternative local binary.
- **Embeddings:** Use **Ollama embeddings** to keep dependencies minimal and consistent.
- **PDF Ingestion:** Use **PyMuPDF** for fast text extraction with page-level metadata for citations.
- **Database Schema:** **Strict adherence** to the proposed SQLite schema (Conversations, Messages, Documents) to support all GPT-like features.
- **Frontend (React):** Create a dedicated `ChatStreamer` component to manage and render token-by-token responses from **SSE** (WebSocket fallback optional).
- **Error Handling:** Gracefully handle Ollama connection errors, I/O errors during PDF parsing, "No relevant context found" scenarios, and SSE disconnect/retry.

## 7. FIRST ACTION ITEM
Set up the foundational backend structure: **FastAPI server, SQLite connection, ChromaDB local store setup, and a simple endpoint for Ollama health/embeddings check (SSE-ready response).**
Explain the initial FastAPI, SQLite, ChromaDB, and SSE configuration reasoning (Chain-of-Thought) before writing any code.