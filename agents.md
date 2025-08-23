FrankTheLocalLLM Agents – detailed specification
1. Introduction and scope
FrankTheLocalLLM is a self‑contained note‑taking and knowledge‑retrieval system. It consists of a Vue/Tailwind front‑end and a FastAPI back‑end, supported by Celery workers and a local vector database. All components are designed to run offline using Ollama models and local storage, making the system suitable for single‑user scenarios without external network access. The application can be launched in development mode via a browser at http://localhost:5173 (with the API at http://localhost:8001/api) or packaged as a desktop application via Tauri for Windows. Frontend assets are now built with ESBuild. Run `npm run dev` in `app/` to start the watch server on port 5173 or `npm run build` to emit a production bundle in `app/dist/`.
Scope: This document describes each “agent” – a logical unit that encapsulates a specific capability – together with their endpoints, underlying implementations and configuration. It assumes an offline‑first deployment and a single user (no multi‑tenant or RBAC considerations). Where appropriate, it highlights forward‑looking improvements such as schema caching, query rewriting and vector store lifecycle management.
________________________________________
2. Environment and configuration
The back‑end relies on a Settings class which exposes environment variables with sensible defaults[1]. Key variables include:
•	HOST / PORT – the bind address and port for the FastAPI server. On startup the application will probe for a free port and increment until available[2].
•	REDIS_URL – the Celery broker URL. Development defaults to redis://localhost:6379/0[3] but in a packaged build Celery can run in‑process.
•	DATABASE_URL – SQLAlchemy connection string. Defaults to an SQLite file ./app.db[4]. For vector embeddings, Chroma is used in this specification (see §5) instead of PGVector.
•	MODEL / EMBED_MODEL – names of the Ollama LLM (default llama3) and embedding model (default nomic-embed-text).
•	RETRIEVAL_K / CHUNK_SIZE – retrieval depth for QA chains and chunk size when splitting documents[5].
All data – including the SQLite database, embedded vectors and chat cache – is stored under a single application folder (e.g. %APPDATA%/Frank on Windows). No outbound HTTP calls are made in production.
________________________________________
3. Agent catalogue
The table below lists the agents and services available in the back‑end, the HTTP endpoints that expose them, and a summary of their responsibilities. Each endpoint is scoped under /api as configured in backend/app/__init__.py[6].
Agent/service	Endpoint(s) & method(s)	Request / response details	Implementation and notes
SQL agent	POST /api/agent/run — natural‑language command.<br>POST /api/agent/sql — question to SQL.	Accepts JSON body {"command": string} or {"question": string}. Returns {"response": str} or {"answer": str, "sql": str} respectively. The second endpoint returns both the answer and the generated SQL statement[7].
Instantiates a singleton Ollama model and SQLDatabase connection. Uses LangChain’s create_sql_agent to interpret commands and SQLDatabaseChain to answer questions with intermediate steps[8]. Errors raise HTTP 500.[7]

Chat agent	POST /api/chat	Accepts JSON body {"message": string}. Returns {"response": str, "cached": bool} indicating whether the reply came from cache[9].
Lazily loads an Ollama model. Responses are cached by hashing the exact prompt; the cache persists to data/chat_cache.json[10]. Caching uses an in‑memory dictionary or a functools.lru_cache inherited from CachedLLMService[11].

Retrieval‑QA agent	POST /api/qa/stream	Accepts JSON body {"question": string} and streams Server‑Sent Events. Events have type token with partial answer text, and a final end event[12].
Builds a RetrievalQA chain on demand. Embeddings are created via OllamaEmbeddings and stored in the local vector store; a retriever fetches the top‑k chunks (k from settings). A PromptTemplate instructs the LLM to answer using context and append markdown citations[13]. Streaming is implemented with AsyncIteratorCallbackHandler[12].

Trivia agent	GET /api/trivia?q=…	Query string parameter q containing a trivia question. Returns {"answer": string}[14].
On initialisation, loads data/trivia.md, splits it into 512‑character chunks with 50‑character overlap, embeds them with Ollama, and stores them in a Chroma vector store[15]. Uses a RetrievalQA chain to answer questions.[16]

Import agent	POST /api/import	Expects multipart/form‑data with a ZIP file. Returns {"status": "ok"} when queued[17].
Extracts the archive, reads each .md or .pdf file (PDF via PyPDF2), splits documents by headings, computes SHA‑256 of each chunk, deduplicates by hash, writes records to the database and schedules embedding jobs by calling tasks.embed_chunk.delay(id)[18].

Embedding agent	Celery task embed_chunk(chunk_id)	No direct endpoint. Reads the chunk content, embeds it via OllamaEmbeddings and inserts a vector row into embeddings table[19].
Runs asynchronously via Celery. Uses a new DB session each invocation[20]. Vectors are 1536‑dimensional[21].

Summarisation agent	Celery task summarize_entries scheduled every 60 s	No direct endpoint. Finds entries with summarized=False and writes a summary using the LLM[22].
Uses SummarizationService which inherits from CachedLLMService and calls llm_invoke(f"Summarize the following text:\n{entry.content}")[23]. After summarising, sets summarized=True and updates summary.
Daily digest agent	Celery task daily_digest scheduled once per day at midnight	No direct endpoint. Concatenates all chunks updated in the last 24 hours, produces a ≤200‑word summary and writes it to daily_summaries table. Also updates backlinks between chunks[24].
Uses summarisation service via llm_invoke. Computes token_count and inserts a DailySummary row[25]. Backlinks are created by finding wiki‑style [[Title]] links and resolving them to target chunks[26].

Entry service	POST /api/entries/ – create<br>GET /api/entries/ – list<br>PUT /api/entries/{id} – update<br>DELETE /api/entries/{id} – delete	Accepts and returns EntryCreate/EntryRead models. Filter by optional group and search query q in title or content[27].
Uses a UnitOfWork to stage additions and updates. Each operation commits at the end of the request[28].

User/auth service	POST /api/auth/register – register<br>POST /api/auth/login – login<br>GET /api/user/me – current user	Registration accepts {"username", "password"} and returns user details. Login returns a JWT access_token[29]. The /user/me endpoint requires a valid token and returns the current user[30].
Passwords are hashed using passlib and JWTs are signed with a secret key[31].

Status service	GET /status	Returns a dummy payload such as {"llm_loaded": true, "docs_indexed": 342}[32].
Placeholder endpoint; intended to be replaced by real health/metrics API in future.
Example service	GET /api/hello	Returns {"message": "Hello from FastAPI"}[33].
Illustrative stub for demonstration and testing.
Note on asynchronous tasks
Celery workers run the embedding, summarisation and digest agents in the background. In development, settings.redis_url is used as the broker; in a packaged build the worker can run in‑process to avoid Redis. The scheduling of tasks is defined in app/tasks.py via celery_app.conf.beat_schedule[34]. Each task opens its own database session and commits changes before closing[20]. Error handling is minimal; failed tasks currently log exceptions but do not retry.
________________________________________
4. Data model and persistence
The application uses SQLAlchemy models defined in models.py. Relevant tables include:
•	File – records uploaded files with path and display name[35].
•	Chunk – stores extracted document segments with references to the originating file (file_id), the text content, a SHA‑256 content_hash, start/end line numbers and timestamps[36]. The updated_at column is automatically refreshed on update.
•	Embedding – holds 1536‑dimensional vectors for each chunk[21]. Vectors are stored in a Chroma index for this spec; the original code uses PGVector.
•	Entry – user‑created notes with title, optional group, content, summary and a boolean summarized flag[37].
•	DailySummary – daily digest entries with timestamp, summary text and token count[38].
•	Backlink – mapping table linking chunks that reference each other via wiki‑style [[Title]] links[39].
In development the application defaults to SQLite; migrating to a production DB requires adjusting DATABASE_URL in .env.
________________________________________
5. Vector store lifecycle & index health
For this refined specification, the vector index uses Chroma as a file‑backed store for both development and packaged builds. This choice simplifies deployment (no external Postgres) and provides portable persistence. The embedding lifecycle is managed entirely asynchronously by the embed_chunk task; the front‑end never blocks on embedding.
Lifecycle
1.	Chunk creation – When a document is imported or an entry is updated, the text is split into chunks (see §3). Each chunk is assigned a content_hash. If the hash already exists the chunk is ignored; otherwise a new Chunk row is inserted and the chunk is enqueued for embedding[40].
2.	Embedding – The embed_chunk task retrieves the chunk, computes its embedding using the nomic-embed-text model via Ollama and writes a new vector to the Embedding table[41]. In Chroma, the vector and metadata are stored together; in PGVector the vector is stored separately.
3.	Updates and deletions – If a chunk’s text changes, a new hash will be generated. The new chunk will be considered distinct and the old vector will become stale. A maintenance routine (not yet implemented) should remove stale vectors. Deleting a chunk or file should trigger a purge of its vectors.
4.	Health metrics – A future /api/index/status endpoint will expose totals such as number of chunks, number of embedded vectors, number of stale vectors and queue depth. Maintenance endpoints like /api/index/rebuild and /api/index/vacuum can be added to re‑embed all content or remove orphans.
Staleness targets
Embedding is asynchronous; users should expect updated content to be searchable within ≤2 minutes (95th percentile). A worker loop that polls the embedding queue every 5 s and batches embeddings where possible should keep median latency below 30 s. The UI can display a “Re‑indexing” badge for items awaiting embedding.
________________________________________
6. Query rewriting & cross‑document reasoning
The current retrieval pipeline takes a user question and retrieves top‑k chunks directly. This can underperform when the question is ambiguous or uses synonyms not present in the text. A query rewriter module could preprocess questions, expanding acronyms and adding synonyms, and then aggregate results across multiple rewrites before sending them to the LLM. A simple “Broaden search” toggle in the UI can enable this behaviour.
For deeper cross‑document reasoning, a second‑pass chain can be run when the first pass yields few citations or low confidence. The chain would assemble context from several documents and prompt the LLM to synthesise an answer. This approach should be implemented carefully to stay within token limits and maintain determinism.
________________________________________
7. Streaming UI contract
The /qa/stream endpoint streams tokens via SSE. Clients must:
1.	Initiate a POST with JSON body {"question": …} and accept text/event-stream responses.
2.	Handle event: token messages by appending the data field to the answer display.
3.	Handle event: end by finalising the answer and showing citations. The server awaits the LLM call before sending end[12].
4.	Cancel a query by closing the SSE connection; the server cancels the underlying asyncio task.
A fallback mode can provide non‑streaming responses if the client or network does not support SSE.
________________________________________
8. Prompt customisation & SQL safety
Each agent should define an explicit system prompt. For example, the retrieval QA prompt in code tells the model to “Answer using the context. Append markdown citations…”[42]. Providing YAML files for prompts allows for easier editing and domain‑specific tuning.
For the SQL agent, safety measures are essential. The current implementation uses create_sql_agent and SQLDatabaseChain directly, which could permit harmful queries. A robust implementation should:
1.	Generate a candidate SQL query and a rationale.
2.	Validate it against a whitelist of tables/columns and disallow INSERT, UPDATE, DELETE, DROP and other mutations.
3.	Optionally run EXPLAIN first to detect full table scans or other inefficiencies.
4.	Ask the user for confirmation when a risky query is detected and provide a safe rewrite.
________________________________________
9. Schema awareness & caching
Currently the SQL agent introspects the database each time it runs. To improve performance, a schema snapshot can be built on startup: a JSON document listing tables, columns, primary/foreign keys and a few example rows. The snapshot is cached in memory and refreshed when the schema hash changes. The agent can then reference this document rather than performing live introspection.
When multiple databases are involved, namespacing snapshots by DSN and restricting queries to a specific namespace prevents accidental cross‑DB queries.
________________________________________
10. Admin panel (Tauri settings)
A built‑in admin view gives the user insight into background processes and offers maintenance actions:
•	Metrics display: Show number of files, chunks, embedded vectors, stale vectors, index p50/p95 latency and embedding queue depth.
•	Controls: Buttons to trigger a full rebuild of the index, vacuum stale vectors, refresh the schema snapshot and clear caches.
•	Log viewer: Tail the last N lines of back‑end and worker logs for troubleshooting.
•	Diagnostics export: Package logs and configuration into a bundle for support; remain offline.
Exposing these controls increases transparency (“why is my query missing recent notes?”) and helps recover from corruption without requiring CLI access.
________________________________________
11. Security & privacy
•	Single user: There is no multi‑tenant support. A basic registration endpoint stores usernames and hashed passwords in the database[43]. Logins return a JWT signed with a secret key[44]. A valid token is required for /user/me[30]. In production, disable registration and ship a pre‑created admin token.
•	No external calls: Outbound network requests are disabled by default. Embeddings and models run locally via Ollama. CORS is restricted to http://localhost:5173 in dev and tauri://localhost in production[45].
•	Data locality: All persistence (DB, vector store, caches) resides under a single folder. Users can back up or move this folder to preserve their data.
•	Secret management: The JWT secret key is hardcoded in the example code[46]. For production, load it from the environment and rotate as needed.
________________________________________
12. Conclusions and future work
The FrankTheLocalLLM project demonstrates how to build an offline, modular knowledge base driven by local LLMs. Each agent encapsulates a distinct capability, from conversational chat to SQL querying, retrieval‑augmented QA, trivia, import and summarisation. Background tasks extend functionality beyond the request–response cycle, enabling continuous embedding, summarisation and daily digest generation.
To evolve this system, consider:
•	Implementing the proposed query rewriter and cross‑document reasoning to improve retrieval recall on ambiguous questions.
•	Adding maintenance endpoints to manage the vector store lifecycle and expose index health.
•	Defining explicit YAML prompts per agent to encourage safe, domain‑aware responses.
•	Introducing a schema snapshot cache to reduce latency and improve SQL agent security.
•	Expanding the admin panel to provide actionable diagnostics and user control over background processes.
Maintaining comprehensive documentation of agent responsibilities and their underlying code is vital for onboarding contributors and ensuring the longevity of the project. This specification serves as a blueprint for current functionality and a roadmap for future enhancements.
