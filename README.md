# Architecture & Agent Documentation

## Overview

MainAgent is a research assistant that intelligently combines web search and Retrieval-Augmented Generation (RAG) to answer user questions. Built with **PocketFlow** for orchestration, **FastAPI** for the backend, and **Next.js** for the frontend, it provides a seamless conversational experience.

---

## System Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Next.js UI<br/>Port 3000]
    end
    
    subgraph "Backend Layer"
        API[FastAPI Server<br/>Port 8000]
        Orchestration[Orchestration Engine]
    end
    
    subgraph "Agent Nodes"
        RetrieveMem[🧠 RetrieveMemoryNode]
        Decide[🤔 DecideActionNode]
        Search[🔍 SearchWebNode]
        Embed[🧮 EmbedQueryNode]
        Retrieve[📚 RetrieveRAGNode]
        ExecuteTool[🛠️ ExecuteMCPToolNode]
        Answer[✍️ AnswerNode]
        ArchiveMem[💾 ArchiveMemoryNode]
    end
    
    subgraph "External Services"
        OpenAI[OpenAI API<br/>LLM & Embeddings]
        DuckDuckGo[DuckDuckGo<br/>Web Search]
    end
    
    subgraph "Pinecone Cloud"
        PineconeRAG[RAG Index<br/>mainagent-rag]
        PineconeMemory[Memory Index<br/>mainagent-memory]
    end
    
    subgraph "MCP Servers"
        Weather[Apify Weather<br/>HTTP/SSE]
        Langfuse[Langfuse Prompts<br/>HTTP/SSE]
    end
    
    UI -->|POST /api/chat| API
    API -->|Run Orchestration| Orchestration
    Orchestration --> RetrieveMem
    RetrieveMem --> Decide
    
    Decide --> Search
    Decide --> Embed
    Decide --> ExecuteTool
    Decide --> Answer
    
    Search --> DuckDuckGo
    Embed --> Retrieve
    Retrieve --> PineconeRAG
    Retrieve --> Answer
    ExecuteTool --> Weather
    ExecuteTool --> Langfuse
    Answer --> OpenAI
    Answer --> ArchiveMem
    
    RetrieveMem -->|Query past conversations| PineconeMemory
    ArchiveMem -->|Store old conversations| PineconeMemory
    
    API -->|Response| UI
```

---

## Agent Graph 

The MainAgent uses a **decision-based routing system** with **conversation memory**. The flow starts by retrieving relevant past conversations, then routes through decision-making, and archives old conversations when needed.

```mermaid
flowchart TD
    Start([User Question]) --> RetrieveMem[🧠 RetrieveMemoryNode<br/>Fetch relevant past conversations]
    RetrieveMem --> Decide{🤔 DecideActionNode<br/>With memory context}
    
    Decide -->|Need weather| Tool[🛠️ ExecuteMCPToolNode]
    Decide -->|Need prompts| Tool
    Decide -->|Need search| Search[🔍 SearchWebNode]
    Decide -->|Need RAG| Embed[🧮 EmbedQueryNode]
    Decide -->|Can answer| Answer[✍️ AnswerNode]
    
    Tool -->|Add context| Decide
    Search -->|Add context| Decide
    Embed --> Retrieve[📚 RetrieveRAGNode]
    Retrieve --> Answer
    
    Answer --> Archive{Messages > 6?}
    Archive -->|Yes| ArchiveMem[💾 ArchiveMemoryNode<br/>Store to long-term memory]
    Archive -->|No| End([Return Answer])
    ArchiveMem --> End
```

---

## Node Descriptions

### 🤔 DecideActionNode
**Purpose**: Intelligent routing and decision-making

**Actions**:
- Analyzes the user's question
- Evaluates existing context and RAG results
- Discovers available MCP tools
- Decides next action: `search`, `rag`, `tool`, or `answer`

**Returns**:
- `search`: Needs web search for current information
- `rag`: Should query the knowledge base
- `tool`: Should use an external MCP tool
- `answer`: Has enough information to respond

**Key Logic**:
```python
# Evaluates:
- Question complexity
- Available context
- RAG results quality
- Available MCP tools
- Need for external data or specialized tools
```

---

### 🔍 SearchWebNode
**Purpose**: Gather real-time information from the web

**Process**:
1. Receives search query from DecideActionNode
2. Executes DuckDuckGo search
3. Extracts titles, URLs, and snippets
4. Appends results to shared context
5. Returns to DecideActionNode for re-evaluation

**Metrics Tracked**:
- `search_count`: Number of searches performed

---

### 🧮 EmbedQueryNode
**Purpose**: Convert text to vector embeddings

**Process**:
1. Receives user question
2. Calls OpenAI embeddings API
3. Generates vector representation
4. Stores embedding in shared state

**Used For**:
- Semantic similarity search in FAISS
- Finding relevant documents in knowledge base

---

### 📚 RetrieveRAGNode
**Purpose**: Query cloud-based knowledge base

**Process**:
1. Receives query embedding
2. Searches Pinecone vector index
3. Retrieves top-k (default: 3) most similar documents
4. Returns document chunks with sources

**Metrics Tracked**:
- `rag_hits`: Number of documents retrieved

---

### 🛠️ ExecuteMCPToolNode
**Purpose**: Execute external tools via Model Context Protocol

**Process**:
1. Receives tool name and arguments from DecideActionNode
2. Routes request to appropriate MCP server (Weather, Langfuse, etc.)
3. Executes tool via HTTP/SSE connection
4. Returns result to shared context
5. Returns to DecideActionNode for re-evaluation

**Supported MCP Servers**:
- **Apify Weather**: Weather data, timezone information
- **Langfuse**: Prompt management, observability data

**Tool Naming Convention**:
- Tools are prefixed with server name: `weather_get_weather`, `langfuse_list_prompts`
- Automatic routing based on prefix

**Example Tools**:
```python
# Weather tools
weather_get_weather(city="Paris")
weather_get_current_datetime(timezone="Europe/Paris")

# Langfuse tools
langfuse_list_prompts()
langfuse_get_prompt(name="greeting")
```

---

### ✍️ AnswerNode
**Purpose**: Synthesize final answer using LLM

**Process**:
1. Receives question, context, and RAG results
2. Constructs comprehensive prompt
3. Calls OpenAI LLM
4. Generates answer with source citations
5. Returns final response to user

**Output Format**:
- Concise answer
- Inline source citations
- Acknowledgment of uncertainty when applicable

---
### MCP Integration 

```mermaid
graph TB
    subgraph "MCP Integration"
        Client[MCP Client]
        Weather[Apify Weather Server]
        Langfuse[Langfuse MCP Server]
    end
    
    subgraph "Agent Flow"
        Decide[DecideActionNode]
        Execute[ExecuteMCPToolNode]
    end
    
    Decide -->|Discovers tools| Client
    Client -->|HTTP/SSE| Weather
    Client -->|HTTP/SSE| Langfuse
    Decide -->|action: tool| Execute
    Execute -->|Calls tool| Client
    Execute -->|Returns result| Decide
```


### Supported MCP Servers

#### 1. Apify Weather Server
**URL**: `https://jiri-spilka--weather-mcp-server.apify.actor/mcp`

**Tools**:
- `weather_get_weather` - Current weather for any city
- `weather_get_weather_by_datetime_range` - Historical weather data
- `weather_get_current_datetime` - Current time for any timezone

**Configuration**:
```bash
APIFY_API_TOKEN=apify_api_your_token_here
```

#### 2. Langfuse MCP Server
**URL**: `{LANGFUSE_HOST}/api/public/mcp`

**Tools** (Prompt Management & Observability):
- `langfuse_list_prompts` - List all prompts
- `langfuse_get_prompt` - Get a specific prompt
- `langfuse_compile_prompt` - Compile prompt with variables
- `langfuse_create_prompt` - Create new prompt
- And more...

### How It Works

1. **Tool Discovery**: On startup, `DecideActionNode` queries all configured MCP servers
2. **Tool Naming**: Tools are prefixed with server name (e.g., `weather_get_weather`)
3. **Routing**: `ExecuteMCPToolNode` routes tool calls to the appropriate server
4. **Dynamic**: Servers can be enabled/disabled by adding/removing credentials

### Example Questions

With MCP servers configured:
- "What's the weather in Paris?" → Uses `weather_get_weather`
- "What time is it in Tokyo?" → Uses `weather_get_current_datetime`
- "List my prompts" → Uses `langfuse_list_prompts`
- "Get the customer_greeting prompt" → Uses `langfuse_get_prompt`

---

## Session Memory

Throughout the flow execution, collect user inputs and on going context in the **Session Memory**:

```python
shared = {
    "question": str,           # Original user question
    "context": str,            # Accumulated web search context
    "search_history": list,    # History of search results
    "search_query": str,       # Current search query
    "query_embedding": list,   # Vector embedding of question
    "rag_results": list,       # Retrieved documents from Pinecone
    "tool_name": str,          # MCP tool to execute
    "tool_args": dict,         # Arguments for MCP tool
    "answer": str,             # Final answer
    "metrics": {
        "search_count": int,   # Number of searches performed
        "rag_hits": int,       # Number of RAG documents retrieved
        "tool_calls": int      # Number of MCP tool calls
    }
}
```

---

## Conversation Memory System

MainAgent implements a **two-tier memory system** for maintaining conversation context:

### 🔄 Short-Term Memory (Sliding Window)

**Purpose**: Immediate conversation context

**How it Works**:
- Maintains the **last 3 conversation pairs** (6 messages total) in active memory
- Provides immediate context for ongoing conversation
- Automatically slides forward as new messages arrive

**Storage**: `shared["messages"]` - List of recent message dicts

**Example**:
```python
[
    {"role": "user", "content": "What's the weather in Paris?"},
    {"role": "assistant", "content": "It's currently 18°C and sunny in Paris."},
    {"role": "user", "content": "And in London?"},
    {"role": "assistant", "content": "London is 15°C with light rain."},
    {"role": "user", "content": "Which is warmer?"},
    {"role": "assistant", "content": "Paris is warmer at 18°C vs London's 15°C."}
]
```

### 🧠 Long-Term Memory (Pinecone Vector Index)

**Purpose**: Retrieve relevant past conversations

**How it Works**:
1. When short-term memory exceeds 6 messages, the **oldest pair is archived**
2. Each archived conversation is **embedded** using OpenAI embeddings
3. Embeddings are stored in **Pinecone** (same database as RAG) with session metadata
4. When a new question arrives, the system **retrieves the most relevant** past conversation
5. Retrieved memory is **injected into context** for the LLM

**Storage**:
- **Pinecone Index**: `mainagent-memory` (or configured via `PINECONE_MEMORY_INDEX`)
- **Metadata**: Each memory includes `session_id`, `user_message`, `assistant_message`, `timestamp`
- **Filtering**: Memories are filtered by session to ensure privacy

**Why Pinecone for Memory?**:
✅ **Unified Infrastructure**: Same database for RAG and memory  
✅ **Cloud-Native**: Persists across server restarts  
✅ **Multi-User**: Each session has isolated memory via metadata filtering  
✅ **Scalable**: Handles unlimited conversation history  
✅ **Fast**: Sub-millisecond similarity search  

**Architecture**:

```mermaid
graph LR
    subgraph "Short-Term Memory"
        Recent[Last 3 Pairs<br/>6 Messages]
    end
    
    subgraph "Long-Term Memory (Pinecone)"
        Archive[Archived Conversations]
        Pinecone[Pinecone Vector Index]
        Embeddings[Conversation Embeddings]
    end
    
    Recent -->|Exceeds 6 messages| Archive
    Archive -->|Generate embedding| Embeddings
    Embeddings -->|Store with session_id| Pinecone
    
    Query[New Question] -->|Search by session| Pinecone
    Pinecone -->|Retrieve| Relevant[Relevant Past Conversation]
    Relevant -->|Inject into context| LLM[Answer Generation]
    Recent -->|Provide| LLM
```

### Memory Flow Example

```
Conversation 1:
User: "My cat's name is Whiskers"
Assistant: "Got it! Whiskers is your cat's name."
→ Stored in short-term memory

Conversation 2:
User: "I have a peanut allergy"
Assistant: "Understood, you have a peanut allergy."
→ Stored in short-term memory

Conversation 3:
User: "My anniversary is June 17th"
Assistant: "Noted! Your anniversary is June 17th."
→ Stored in short-term memory

Conversation 4:
User: "I lived in Portugal for 3 years"
Assistant: "Great to know you lived in Portugal!"
→ Conversation 1 archived to long-term memory (embedded)
→ Conversations 2, 3, 4 remain in short-term

Later...
User: "What's my cat's name?"
→ System searches long-term memory
→ Retrieves Conversation 1 (high similarity)
→ Combines with recent context
Assistant: "Your cat's name is Whiskers."
```

### Memory Retrieval Process

1. **Query Embedding**: New question is converted to vector
2. **Similarity Search**: Pinecone finds most similar past conversation (filtered by session_id)
3. **Context Injection**: Retrieved conversation is added to prompt:
   ```
   System: The following is a relevant past conversation:
   User: My cat's name is Whiskers
   Assistant: Got it! Whiskers is your cat's name.
   
   System: Now continue the current conversation:
   User: What's my cat's name?
   ```
4. **Answer Generation**: LLM uses both recent + retrieved context

### Benefits

✅ **Scalable**: Can handle unlimited conversation history  
✅ **Efficient**: Only keeps recent messages in active memory  
✅ **Contextual**: Retrieves relevant past information automatically  
✅ **Fast**: Pinecone provides sub-millisecond similarity search  
✅ **Semantic**: Finds conversations by meaning, not keywords  
✅ **Persistent**: Memory survives server restarts  
✅ **Multi-User**: Isolated memory per session via metadata filtering

### Configuration

```python
# Memory settings (in agent/memory.py)
WINDOW_SIZE = 6                    # Messages to keep in short-term memory
EMBEDDING_DIMENSION = 1536         # OpenAI embedding dimension
RETRIEVAL_K = 1                    # Number of past conversations to retrieve

# Environment variables
PINECONE_API_KEY=your_key          # Required: Pinecone API key
PINECONE_MEMORY_INDEX=mainagent-memory  # Optional: Memory index name (default: mainagent-memory)
```

### Session Management

Each user session maintains its own memory:
- Sessions are identified by `session_id` in API requests
- Each session has independent short-term and long-term memory
- Memory persists for the duration of the session
- Sessions can be cleared or archived as needed


---

## Request Flow Sequence

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Flow
    participant Decide
    participant Search
    participant Embed
    participant Retrieve
    participant ExecuteTool
    participant Answer
    participant OpenAI
    participant DuckDuckGo
    participant Pinecone
    participant MCPServers

    User->>Frontend: Ask question
    Frontend->>API: POST /api/chat
    API->>Flow: Run with shared state
    
    Flow->>Decide: Execute
    Decide->>OpenAI: Analyze question
    OpenAI-->>Decide: Decision
    
    alt Search needed
        Decide->>Search: search_query
        Search->>DuckDuckGo: Web search
        DuckDuckGo-->>Search: Results
        Search->>Decide: Re-evaluate with context
    end
    
    alt MCP Tool needed
        Decide->>ExecuteTool: tool_name, tool_args
        ExecuteTool->>MCPServers: HTTP/SSE request
        MCPServers-->>ExecuteTool: Tool result
        ExecuteTool->>Decide: Re-evaluate with result
    end
    
    alt RAG needed
        Decide->>Embed: question
        Embed->>OpenAI: Generate embedding
        OpenAI-->>Embed: Vector
        Embed->>Retrieve: embedding
        Retrieve->>Pinecone: Similarity search
        Pinecone-->>Retrieve: Top documents
        Retrieve->>Answer: rag_results
    end
    
    alt Direct answer
        Decide->>Answer: answer
    end
    
    Answer->>OpenAI: Synthesize response
    OpenAI-->>Answer: Final answer
    Answer-->>Flow: Complete
    Flow-->>API: Result
    API-->>Frontend: JSON response
    Frontend-->>User: Display answer
```

---

## API Endpoints

### `POST /api/chat`
**Request**:
```json
{
  "message": "What is machine learning?",
  "session_id": "optional-session-id"
}
```

**Response**:
```json
{
  "answer": "Machine learning is...",
  "sources": ["source1.txt", "source2.pdf"],
  "trace_id": "uuid-v4"
}
```

### `GET /api/evals`
**Response**:
```json
{
  "recent": [
    {
      "session_id": "user-123",
      "latency_ms": 1234.56,
      "searches": 2,
      "rag_hits": 3
    }
  ]
}
```

### `GET /health`
**Response**:
```json
{
  "status": "ok"
}
```

---


## Running the Application

### Backend
**Note**: Python 3.10+ is required for MCP support

```bash
cd backend
pip3 install -r requirements.txt

# For MCP support, use Python 3.10+
/opt/homebrew/bin/python3.10 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or with default Python 3
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Access Points
- **Frontend UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Monitoring & Debugging

### Terminal Output
Each node prints emoji-decorated logs showing execution flow:
```
🤔 DecideActionNode: Analyzing question and deciding next action (search/RAG/answer)
🔍 SearchWebNode: Performing web search for query: 'latest AI news'
🧮 EmbedQueryNode: Generating embedding vector for question
📚 RetrieveRAGNode: Searching FAISS index for relevant document chunks
✍️ AnswerNode: Synthesizing final answer using LLM with context and RAG results
```

### Metrics Collection
The `/api/evals` endpoint provides real-time metrics:
- Request latency
- Search count per request
- RAG hits per request
- Session tracking

---


