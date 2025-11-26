![PocketFlow Logo](https://github.com/the-pocket/.github/raw/main/assets/abstraction.png)

# MainAgent

PocketFlow-based research assistant with:
- FastAPI backend hosting the PocketFlow flow, web search, and FAISS-backed RAG.
- Next.js frontend that exposes a chat widget plus an evaluation panel.
- Vercel-friendly deployment (frontend + Python serverless backend).

## Repo Layout

```
frontend/   # Next.js UI (chat widget + eval panel)
backend/    # FastAPI PocketFlow agent + FAISS index + scripts
.env        # Runtime secrets (ignored) – copy from .env.example
```

## Quick Start

1. **Install dependencies**
   ```bash
   # frontend (requires Node 18+)
   cd frontend && npm install

   # backend (Python 3.9+)
   cd backend && pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # fill OPENAI_API_KEY, SEARCH_API_KEY, etc.
   ```

3. **Build RAG index (FAISS)**
   ```bash
   cd backend
   python scripts/build_index.py
   ```

4. **Run locally**
   ```bash
   # terminal 1 – backend
   cd backend
   uvicorn main:app --reload

   # terminal 2 – frontend (with proxy to backend)
   cd frontend
   npm run dev
   ```

## Deployment (Vercel)

1. Build the FAISS assets and commit/push them or upload to object storage:
   ```bash
   cd backend
   python scripts/build_index.py
   ```
2. Set project-level secrets in Vercel:
   - `OPENAI_API_KEY`
   - `SEARCH_API_KEY` (optional)
   - `NEXT_PUBLIC_BACKEND_URL` (frontend) pointing at the deployed backend URL
3. Deploy the frontend:
   ```bash
   vercel --cwd frontend --prod
   ```
4. Deploy the backend FastAPI function:
   ```bash
   vercel --cwd backend --prod
   ```
   The file `backend/api/index.py` exposes the FastAPI `app`, and `backend/vercel.json` pins the Python runtime.
5. Update `NEXT_PUBLIC_BACKEND_URL` to the backend HTTPS endpoint and redeploy the frontend if needed.

See `main.plan.md` for the detailed implementation roadmap.

See `main.plan.md` for the detailed implementation roadmap.
