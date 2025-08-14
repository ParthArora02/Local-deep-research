Deep Research Assistant
A privacy-friendly research tool that performs multi-step analysis with local or cloud LLMs and integrated search. Run it fully offline or connect to services like Claude/GPT for more capability.

Highlights
In-depth research: multi-iteration reasoning, follow-up questioning, full-page parsing, citation tracking.

Flexible models: Ollama locally; Claude/GPT via API; works with LangChain models; configurable per task.

Output formats: detailed reports with citations, concise summaries, source logs.

Privacy-first: local-only mode, configurable search behavior, transparent data use.

Powerful search: smart engine auto-pick; Wikipedia, arXiv, DuckDuckGo, SerpAPI, The Guardian; local RAG; full-page retrieval; source filtering.

Quick Start
Clone and install

bash
git clone https://github.com/yourusername/local-deep-research.git
cd local-deep-research
pip install -r requirements.txt
Optional: local models with Ollama

bash
# install from https://ollama.ai
ollama pull mistral
Configure environment

bash
cp .env.template .env
# then edit:
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GUARDIAN_API_KEY=...
Run
CLI:

bash
python main.py
Web app:

bash
python app.py
Opens at http://127.0.0.1:5000

Web UI includes a dashboard, live status, history, PDF export, and run management.

Configuration (config.py)
python
DEFAULT_MODEL = "mistral"
DEFAULT_TEMPERATURE = 0.7
MAX_TOKENS = 8000

MAX_SEARCH_RESULTS = 40
SEARCH_REGION = "us-en"
TIME_PERIOD = "y"
SAFE_SEARCH = True
SEARCH_SNIPPETS_ONLY = False

search_tool = "auto"  # auto-picks best engine
Local RAG Search
Create collections in local_collections.py:

python
LOCAL_COLLECTIONS = {
  "research_papers": {
    "paths": ["<abs>/local_search_files/research_papers"],
    "embedding_model": "all-MiniLM-L6-v2",
    "chunk_size": 800, "chunk_overlap": 150, "enabled": True
  },
  "personal_notes": {
    "paths": ["<abs>/local_search_files/personal_notes"],
    "embedding_model": "all-MiniLM-L6-v2",
    "chunk_size": 500, "chunk_overlap": 100, "enabled": True
  }
}
Prepare folders:

bash
mkdir -p local_search_files/research_papers
mkdir -p local_search_files/personal_notes
Use RAG:

Smart: set search_tool="auto"

Specific: search_tool="research_papers"

All local: search_tool="local_all"

Inline targeting: collection:research_papers your query

Search Backends
auto (intelligent routing)

wiki (encyclopedic)

arxiv (academic)

duckduckgo (general, no API)

guardian (news, API)

serp (Google via API)

any defined local collection

Tip: Auto mode routes to the most relevant source (e.g., arXiv for papers, news engines for current events).

License
MIT. See LICENSE.

Credits
Ollama, Wikipedia, arXiv, DuckDuckGo, The Guardian, SerpAPI, LangChain, jusText, Playwright, FAISS, sentence-transformers.

Contributing
Fork 2) Branch 3) Commit 4) Push 5) Open PR
