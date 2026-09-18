# 🔌 MCP AI System — Multi-Table Database + RAG + Real-Time Tool Execution

A complete **Model Context Protocol (MCP)** implementation demonstrating how to build production-grade AI systems that can query databases, search documentation, and execute tools with full observability.

![Demo](demo.gif)

## 🎯 What This Is

This project shows how to build an **agentic AI system** using the MCP protocol — the emerging standard for connecting AI models to external tools. Instead of custom integrations, MCP provides a universal interface that any compatible AI can use.

**Key capabilities:**
- 🔌 **7 MCP tools** for database queries and RAG search
- 🗄️ **4-table SQLite database** (users, products, orders, reviews)
- 📚 **RAG knowledge base** with Chroma vector DB
- ⚡ **Real-time tool execution** with SSE streaming
- 🤖 **Qwen 3.8 27B** via Groq with automatic retry/fallback
- 🎨 **React frontend** showing live tool-call trace

## 🏗️ Architecture
┌─────────────────────────────────────────────────────────────┐
│ React Frontend │
│ Chat UI + Live Tool Trace + Conversation History │
└─────────────────────────▲───────────────────────────────────┘
│ SSE streaming
┌─────────────────────────┴───────────────────────────────────┐
│ FastAPI Backend (MCP Client) │
│ │
│ User query → Qwen (tool-calling) → MCP Client → MCP Server │
│ ↑ │ │
│ └──── tool result ───┘ │
└─────────────────────────▲───────────────────────────────────┘
│ In-process
┌─────────────────────────┴───────────────────────────────────┐
│ MCP Server (Python) │
│ │
│ 🛠️ TOOLS (7) 📚 RESOURCES (3) 💬 PROMPTS (2) │
│ • list_users • db_schema • order_summary │
│ • get_user_orders • product_catalog • customer_report│
│ • search_products │
│ • get_product_reviews │
│ • search_docs (RAG) │
│ • get_revenue_stats │
│ • top_customers │
│ │
│ │ │ │
│ ▼ ▼ │
│ ┌──────────┐ ┌──────────┐ │
│ │ SQLite │ │ Chroma │ │
│ │ (4 tabs) │ │ VectorDB │ │
│ └──────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────┘

## ✨ Features

### 🔌 MCP Server
- **7 tools**: Database queries, RAG search, analytics
- **3 resources**: Schema info, stats summary, product catalog
- **2 prompts**: Reusable templates for common queries
- **In-process execution**: No subprocess fragility

### 🗄️ Database (SQLite)
- **users**: 8 sample users with metadata
- **products**: 10 products across 5 categories
- **orders**: 24 orders with line items
- **reviews**: 43 product reviews with ratings
- **relationships**: Full foreign key constraints

### 📚 RAG Knowledge Base
- **4 policy documents**: return, shipping, warranty, loyalty
- **Local embeddings**: `sentence-transformers/all-MiniLM-L6-v2`
- **Chroma vector DB**: Persistent storage with cosine similarity
- **Semantic search**: Find relevant docs by meaning, not keywords

### 🤖 AI Agent (Groq + Qwen 3.8 27B)
- **Native tool-calling**: OpenAI-compatible function calling
- **Multi-turn reasoning**: Agent can call tools in sequence
- **Automatic retry**: Exponential backoff on rate limits
- **Model fallback**: Tries 3 models if primary fails
- **Structured outputs**: JSON-validated tool calls

### 🎨 Frontend (React via CDN)
- **Live tool trace**: Watch every tool call in real-time
- **Expandable results**: See full tool arguments and responses
- **Suggestion chips**: Pre-built queries to try
- **Responsive design**: Works on mobile and desktop

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or 3.12 (mcp SDK has best support)
- Node.js 18+ (optional, for development)
- Free Groq API key from [console.groq.com](https://console.groq.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-ai-system.git
cd mcp-ai-system

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
Configuration
Create .env file:
GROQ_API_KEY=gsk_your_groq_key_here
LLM_MODEL=qwen/qwen3.8-27b
Seed the Database
python scripts/seed_all.py

✓ Database seeded: 8 users, 10 products, 24 orders, 43 reviews
✓ Indexed return_policy.md: 5 chunks
✓ Indexed shipping_policy.md: 2 chunks
✓ Indexed warranty.md: 4 chunks
✓ Indexed loyalty_program.md: 3 chunks

Run the Application
uvicorn app.main:app --reload --port 8000

Open http://localhost:8000 and try:
"Show me the top 3 customers by total spending"
"Which product has the lowest average rating?"
"What does the return policy say?"
"Give me a full customer report for user_id=3"

🧪 Example Queries
Query
Tools Called
What Happens
"Top 3 customers by spending"
top_customers
Returns ranked list with totals
"Lowest rated product"
search_products → get_product_reviews
Searches all products, finds lowest avg rating
"Return policy details"
search_docs
RAG search over policy documents
"Customer report for user_id=3"
get_user_orders
Fetches order history, synthesizes report
"Revenue by category"
get_revenue_stats
Aggregates revenue across product categories
🛠️ Tech Stack
Layer
Technology
Why
MCP Protocol
mcp==1.9.3
Emerging standard for AI-tool integration
Backend
FastAPI
Async, modern, great docs
LLM
Groq (Qwen 3.8 27B)
Fast inference on LPU hardware
Database
SQLite + SQLAlchemy
Zero-config, relational data
Vector DB
Chroma
Local, no vendor lock-in
Embeddings
sentence-transformers
Free, runs offline
Frontend
React 18 (CDN)
No build step needed
Streaming
SSE (Server-Sent Events)
Real-time updates