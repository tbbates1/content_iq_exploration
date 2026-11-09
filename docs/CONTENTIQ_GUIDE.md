# ContentIQ (symplistic.ai): working guide

A practical guide to Symplistic's ContentIQ for running the demos in this repo. It combines three sources:

- the official docs at <https://contentiq.symplistic.ai/documentation/>;
- screenshots of a Starter tenant (`contentiq.symplistic.ai`, app **v2.0.0**) taken on 2026-11-09;
- the IBM watsonx Orchestrate ADK docs at <https://developer.watson-orchestrate.ibm.com/llms.txt>.

When this guide and the live docs disagree, the live docs win. To keep a local Markdown copy of the docs, run `python3 scripts/mirror_contentiq_docs.py`. It writes `docs/contentiq/`, which isn't committed.

---

## 1. What ContentIQ is

ContentIQ ingests content from websites, uploads and cloud drives, indexes it in a vector store, and serves it to **IBM watsonx Orchestrate (wxO) agents** that answer with source citations. You can create a new wxO agent from ContentIQ or attach knowledge to an existing one. Every ContentIQ agent is a wxO agent, so the agent ID you use in the ContentIQ API is the **wxO agent ID**.

```
 sources ──► ContentIQ ingest ──► vector store (Milvus) ──► wxO agent ──► Chat / widget / API / MCP
 (web, upload, CAD,   (parse, chunk,     + object store            (grounded,
  OneDrive, SharePoint, embed, dedupe)                              cited answers)
  Box, GDrive, COS, FileNet)
```

## 2. The tenant we tested on (2026-11-09)

| Item | Value |
|---|---|
| App URL | <https://contentiq.symplistic.ai> |
| App version | v2.0.0. The docs already describe v2.0.1, which adds Essentials Plus, cross-region tenant selection and faster Excel/CAD ingest. |
| Plan | **Starter** |
| Scheduled ingests | 1 |
| Messages | 75,000 per month |
| Vector storage | 5.0 GB |
| Headless API rate | 50 requests per minute |

Agents used in this repo:

| Agent | Holds | Used by |
|---|---|---|
| `Project_Files` (any name) | `data/` | The single-project retrieval test, [`RETRIEVAL_TEST.md`](RETRIEVAL_TEST.md) |
| `Client_Drive` (any name) | `sample_drive/Clients` | The `project_searcher` agent, through its wxO search tool |

> If your tenant holds other agents, double-check the agent ID before you run any delete call (section 8).

## 3. UI map (v2.0 interface)

The left sidebar has **Home · Connect · Chat · Agents · Schedule**, and under *Analytics* it has **Ingest · Usage · Admin**. The **PH** avatar and the version number are at the bottom. Most pages have an **Ask ContentIQ** button at the top right, which opens product help in chat.

| Sidebar | URL | What it does |
|---|---|---|
| Home | `/` | Welcome page with Get Started (video), Connect, Monitor, and Deploy cards, plus an "Ask me anything about ContentIQ" box. |
| Connect | `/connect` | **Connect Knowledge Sources.** Shows connector cards, a search box, the *All Connections / Cloud Storage / Web & Files* tabs, and an active-ingestion indicator. |
| Chat | — | Chat with an agent. The docs call this the *Chat Playground*. Since v2.0 it keeps conversation history, and you can reopen, rename or delete chats. |
| Agents | `/agent-studio` | **Agent Management.** Has *All / Deployed / Not Deployed* filters. Each agent card has a ⚙ settings icon, **View contents** and **Deploy**. |
| Schedule | `/scheduling` | Recurring ingest jobs. Each job card has **Run now** and **Actions** (edit or delete). |
| Ingest | `/analytics/ingest` | **Ingestion Runs.** Lists every run with its status and duration, filtered by run type and connector. **View analytics** opens per-run detail. |
| Usage | `/analytics/usage` | Usage analytics per agent. Since v1.4.3 it shows Unanswered Questions, and since v2.0.1 a Conversations view. |
| Admin | `/analytics/admin` | Tenant-wide plan, message counts, conversations, content footprint, the messages-per-month chart, and tenant users with their roles. |

**Settings** opens from the account menu. Its tabs are **Account · Tenant Administration · watsonx Orchestrate · ContentIQ API · Connections · Vector Store · Object Store**.

### Docs names vs. the v2.0 UI

The User Guide text predates the v2.0 redesign, so some names differ:

| Docs say | In our UI |
|---|---|
| Connections → Website Connect / Document Upload / OneDrive Connect | **Connect** → connector card → **Connect** |
| Chat Playground; Conversations | **Chat** (history is built in) |
| Deploy Agent → Embed Agent / Deploy Agent | **Agents** → **Deploy** on the agent card |
| Ingest Analytics | **Ingest** (Ingestion Runs) → **View analytics** |
| Usage Analytics | **Usage** |
| Settings → Orchestrate API Key / API URL | **Settings → watsonx Orchestrate** |
| Settings → Vector Store (Milvus) | **Settings → Vector Store** |

## 4. One-time setup

### 4.1 Connect ContentIQ to watsonx Orchestrate

ContentIQ needs a wxO **API key** and the **service instance URL**. Enter them in **Settings → watsonx Orchestrate**. Since v1.2.4 any user can update these, not just admins, and since v1.4.1 they can be synced tenant-wide.

To get them from wxO on IBM Cloud ([ADK docs](https://developer.watson-orchestrate.ibm.com/environment/production_import.md)):

1. Log in to your watsonx Orchestrate instance and click the user icon (top right), then **Settings**.
2. Open the **API details** tab and copy the **service instance URL**.
3. Click **Generate API key**. This takes you to IBM Cloud IAM. Click **Create**, then copy the key into a vault.

Do **not** use the credentials shown on the IBM Cloud resources page. They are the wrong ones. The `https://api.orchestrate.com` URL in the ContentIQ docs is only a placeholder.

### 4.2 Generate a ContentIQ API key (for the headless API and MCP)

Go to **Settings → ContentIQ API → Access key → Generate key**.

- The key is shown **once**. Copy it immediately, because ContentIQ can't display it again.
- **Generating a new key invalidates the previous one.** The page shows how many keys you have left.
- Paste it into `.env` as `CONTENTIQ_API_KEY=…`. That file is gitignored, and `.env.example` is the committed template. Never commit the key itself. The ContentIQ docs say the same.

## 5. Connectors

| Connector | Use for | Notes |
|---|---|---|
| **Website Connect** | Public or internal sites | Parallel crawl with retries, de-dupe and chunking. Start from a sitemap or hub page, and make sure robots.txt and auth allow the crawl. A manual single-page mode exists (v1.2.1). |
| **Document Upload** | Local files | Handles PDF, DOCX, legacy `.doc`, XLSX, PPTX, TXT, HTML, Outlook MSG and more. Scanned PDFs need a text layer, so OCR them first. Table extraction and an email on completion are optional. |
| **CAD Drawing PDFs** *(New)* | Engineering drawings | Uses the dedicated **Visual NAV** workflow. Document prep is deterministic, and the visual model is called only when a question is answered. Accepts drawing PDFs and native DWG, DXF, STEP, IGES, Parasolid, SolidWorks part and CATPart files (v2.0.0). It must be enabled on the backend. |
| **OneDrive Connect** | Microsoft OneDrive | Authenticate with Microsoft OAuth, then pick files or folders. |
| **SharePoint Connect** | SharePoint sites, drives and folders | Use checkboxes or select all. You can ingest a whole site or specific drives and folders. |
| **Google Drive Connect** | Google Drive | Same flow as OneDrive. |
| **Box Connect** | Box files and folders | Available since v1.2.5. |
| **FileNet Connect** *(New)* | IBM FileNet repositories | In the UI but **not yet in the docs**. It lets you browse repositories and ingest supported files and folders. |
| **IBM COS Connect** | IBM Cloud Object Storage | Set credentials and the bucket **region** in Settings first (v1.3.0). |

Every connector lets you **attach to an existing agent** (recommended) or **create a new agent**. New agent names are checked for duplicates.

**Rules that matter in practice:**

- **One active ingest at a time per API key.** Another start returns `409 Ingest already in progress`. You can pause, resume or cancel a run from its status page.
- A document run completes if **at least one** file succeeds. Check per-file status for failures, which include a reason and a suggested fix.
- **Excel:** v2.0.1 fixed tables that were split or that lost sparsely populated columns. Re-upload a workbook that was processed before the upgrade.

## 6. Scheduling

Go to **Schedule → New schedule**. Each job has an agent, a source, a selection, an ingest behaviour, a frequency, and a run-at time and timezone.

| Ingest behaviour | Processes on each run |
|---|---|
| **Full reingest** | Every file in scope, even unchanged ones |
| Only reingest changed documents | Files already ingested that have a newer *last modified* time. New files are skipped. |
| Only ingest new documents | Files never ingested before |
| **Ingest changed and new documents** | New files plus modified ones. This is the usual "keep it fresh" choice. |

- Frequency can be daily, every X days, weekly or monthly. A single job can cover several folders, drives or SharePoint libraries, but you can't select a parent and its child together.
- Sources are OneDrive, SharePoint, Google Drive, Box and Website.
- Queued runs appear in Scheduling and in Ingest (v2.0.0).

**For this repo:** schedule the client-drive agent on OneDrive with the selection `Clients` and **Ingest changed and new documents**. Starter allows only **1** scheduled job, so edit the existing job rather than adding another.

> **Watch out:** with **Full reingest**, a daily job re-processed all 7 files in `data/` every night and took **4 to 4.5 hours** each time (Nov 5 to 8, 2026). For a static test set, use **Ingest changed and new documents**, and **Run now** when you actually change a file.

## 7. Running the single-project test (Q1 to Q6)

The questions and expected answers are in [`RETRIEVAL_TEST.md`](RETRIEVAL_TEST.md). For the multi-project RFQ demo, follow the main [`README.md`](../README.md) instead.

### 7.1 Load the documents

Create an agent for the test (for example `Project_Files`) and load the files in `data/` into it:

| File(s) in `data/` | Connector |
|---|---|
| `spec/…SPC-00006-Q.pdf` + `.docx`, `datasheet/…DST-00006-Q.pdf` + `.xlsx`, `mill/…55017-Q.pdf`, `site/…DBD-00002-B.pdf` | **Document Upload**, or drop them in the OneDrive folder |
| `drawing/QAZ-5200-265-E-001_B.pdf` (single line diagram) | **CAD Drawing PDFs** (Visual NAV) |

Q5 and Q6 depend on callouts in the single line diagram. If the drawing comes in only through OneDrive as a plain PDF, compare the answers against a run that sends it through **CAD Drawing PDFs** to the same agent.

Watch progress in **Ingest**, then check what was indexed with **Agents → View contents**. In Content Management you can also edit individual chunks, and version history lets you roll them back (v1.4.4).

### 7.2 Ask the questions

**In the UI:** open **Chat**, pick your test agent, and paste each question heading from [`RETRIEVAL_TEST.md`](RETRIEVAL_TEST.md). Ask only the question sentence, not the source notes. Score the answers with the rubric there: the right value plus the right document is a pass.

**Headless API:**

```bash
set -a; source .env; set +a           # CONTENTIQ_API_KEY, CONTENTIQ_API_BASE, CONTENTIQ_AGENT_ID

curl -sS -X POST "$CONTENTIQ_API_BASE/api/headless/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CONTENTIQ_API_KEY" \
  -d "{\"agent_id\": \"$CONTENTIQ_AGENT_ID\",
       \"message\": \"What seismic zone applies to the site, and what is the peak ground acceleration?\",
       \"thread_id\": \"qaz-q1-$(date +%s)\"}"
```

Use a fresh `thread_id` for each question so earlier answers don't leak into later ones. The docs say you can find the agent ID through the wxO ADK or in the ContentIQ dashboard under **Usage**. Since v1.4.4, Content Management also shows agent and ingestion IDs.

### 7.3 Read the results

- **Usage → your agent → View analytics** shows questions, answer success and fallback rates, citation accuracy, latency and unanswered questions.
- **Ingest → View analytics** shows documents ingested, success rate, embedding coverage, duplicates, chunk stats, and failures by type.

| Symptom | Likely fix (from the docs' playbook) |
|---|---|
| Right value, no source | Check citation and grounding settings on the agent |
| Answer missing or "don't know" | Confirm the file is in **View contents**, then re-ingest. Make sure headings are clear. |
| Wrong value from the drawing | Re-ingest the drawing through **CAD Drawing PDFs** |
| Excel values missing | Re-upload the `.xlsx` on v2.0.1 or later |
| High latency | Reduce retrieved context, and check the region |

## 8. Headless API quick reference

Base URL: `https://backend.contentiq.symplistic.ai`. Every call sends `Authorization: Bearer <ContentIQ API key>`. The rate limit is per user per minute, and going over it returns `429`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/headless/chat` | Chat. JSON body: `agent_id`, `message`, `thread_id` |
| POST | `/api/headless/document/ingest` | Upload files as multipart: `files=@…` (repeatable), `agent_id`, optional `use_gpu`. For drawings add `agent_name` and `ingestion_mode=cad`. |
| GET | `/api/headless/document/status/<run_id>/stream` | Ingest status as a stream (`curl -N`) |
| GET | `/api/headless/structured_data/files?agent_id=…` | List structured files (Parquet, CSV, Excel, JSON, XML) with schema and sample rows |
| DELETE | `/api/headless/structured_data/files/{filename}?agent_id=…` | Delete a structured file |
| GET | `/api/headless/milvus/sources?agent_id=…&batch_size=512` | List the sources indexed for an agent |
| DELETE | `/api/headless/milvus/chunks` | JSON body `{agent_id, source}`. Deletes one source's chunks. |
| DELETE | `/api/headless/milvus/collection` | JSON body `{agent_id}`. ⚠️ **Deletes the agent's whole collection. This can't be undone.** |

Rate limits by plan: Starter 50, Essentials 100, Essentials Plus 125, Standard 150 and Premium 200 requests per minute. GPU ingestion is listed as an Essentials Plus entitlement, so `use_gpu=true` may not apply on Starter.

Full details: [API docs](https://contentiq.symplistic.ai/documentation/api). The Swagger spec at <https://backend.contentiq.symplistic.ai/apidocs/> lists more endpoints than the docs show.

## 9. MCP (Claude Code, Claude Desktop, Cursor)

ContentIQ exposes the same capabilities as the headless API as **36 MCP tools** at `https://backend.contentiq.symplistic.ai/mcp/` (HTTPS, Bearer key).

**Claude Code:**

```bash
set -a; source .env; set +a
claude mcp add --transport http contentiq https://backend.contentiq.symplistic.ai/mcp/ \
  --header "Authorization: Bearer $CONTENTIQ_API_KEY"
```

Keep the default *local* scope. `--scope project` writes `.mcp.json` into this repo, and the key would end up in git.

**Cursor:** add this to `~/.cursor/mcp.json`:

```json
{ "mcpServers": { "contentiq": {
    "url": "https://backend.contentiq.symplistic.ai/mcp/",
    "headers": { "Authorization": "Bearer YOUR_CONTENTIQ_API_KEY" } } } }
```

| Area | Tools |
|---|---|
| Chat | `ciq_chat` (preferred), `ciq_chat_stream`, `ciq_get_conversation`, `ciq_delete_conversation` |
| Ingest and status | `ciq_document_ingest`, `ciq_website_ingest`, **`ciq_document_status_stream`** (poll it with `run_id` for any ingest type) |
| Connectors | `ciq_onedrive_*`, `ciq_sharepoint_*`, `ciq_box_*`, `ciq_ibm_cos_*` (list, then ingest with a `body_json` selection) |
| Scheduler | `ciq_get_scheduler_config`, `ciq_save_scheduler_config`, `ciq_trigger_scheduler_run`, … |
| Knowledge and vector store | `ciq_list_milvus_sources`, `ciq_delete_milvus_chunks`, `ciq_delete_milvus_collection`, `ciq_*_milvus_credentials`, `ciq_*_structured_file` |

MCP gotchas:

- `file_paths` refers to paths on **ContentIQ's server**, not your laptop. For local files, use `content_base64`, which only suits small files because base64 adds about a third to the size. Use a connector or the multipart API for anything large. Our spec PDF is 0.7 MB and the mill data sheet is 2.2 MB.
- Status tools return a single snapshot, so poll until the status is `completed`, `failed` or `aborted`.
- The one-ingest-at-a-time rule and the rate limits apply here too.

Full tool table: [MCP docs](https://contentiq.symplistic.ai/documentation/mcp). In our tests (2026-11-09) the MCP endpoint returned 404; see [`FOLDER_SCOPING.md`](FOLDER_SCOPING.md).

## 10. Deploying an agent

From **Agents → Deploy** you can either:

- **Embed** the agent: copy the widget snippet and place it before `</body>`. You can customise the brand name, opening message, colours (header, launcher, citations, sign-in), and the icon. Set allowed origins as well.
- **Deploy** the agent: push it to a target URL or portal.

A deployed agent counts toward **Deployed agents** on the Admin page. The demos in this repo don't need a deployed agent.

## 11. Security and governance (summary)

From the docs ([User Guide](https://contentiq.symplistic.ai/documentation/guide)):

- **SaaS storage:**
  - MongoDB is encrypted at rest with AES-256-GCM and uses TLS 1.3 in transit.
  - API keys and secrets are encrypted with Fernet, with PBKDF2 key derivation. Passwords and headless keys are bcrypt-hashed with a salt.
  - Sessions expire after 24 hours.
- **Vector store:** Zilliz Cloud (Milvus), Qdrant or Azure. **Object store:** S3 or Azure Blob. Both are AES-256 at rest on SaaS. If you bring your own instances, securing them is your responsibility.
- **Auth:**
  - IBM broker JWT (RS256, JWKS, CRN validation).
  - Azure Entra ID SSO (OAuth 2.0 with PKCE and a domain allowlist). MFA comes through Entra.
  - Headless calls use a Bearer key checked against its bcrypt hash, with tenant isolation.
- **RBAC:**
  - Custom roles per tenant. Admin is required for RBAC and SSO configuration.
  - Content visibility follows role. v2.0.0 applies these rules more consistently in chat, shared content and SharePoint.
- **Logs:** retained for 365 days by default, which is configurable. Conversations export as CSV or JSON.

## 12. Plans

| | Starter | Essentials | Essentials Plus | Standard | Premium |
|---|---|---|---|---|---|
| API rate (req/min) | 50 | 100 | 125 | 150 | 200 |
| Scheduled ingests | 1 | — | 3 | — | — |
| Messages per month | 75,000 | — | 1,000,000 | — | — |
| Storage | 5.0 GB | — | 35 GB | — | — |
| GPU ingestion | — | — | Eligible | — | — |

Starter figures come from a Starter tenant's Admin and Scheduling pages. A dash means the docs don't say.

## 13. References

- ContentIQ docs (live): <https://contentiq.symplistic.ai/documentation/>. Local mirror: `python3 scripts/mirror_contentiq_docs.py`.
  - [User Guide](https://contentiq.symplistic.ai/documentation/guide) · [API](https://contentiq.symplistic.ai/documentation/api) · [MCP](https://contentiq.symplistic.ai/documentation/mcp) · [Releases](https://contentiq.symplistic.ai/documentation/releases) · [What's new](https://contentiq.symplistic.ai/documentation/latest)
- watsonx Orchestrate ADK docs index for LLMs: <https://developer.watson-orchestrate.ibm.com/llms.txt>
  - 2.x page index: <https://developer.watson-orchestrate.ibm.com/_llms/2-x.txt> (518 pages). Every page is available as `.md`.
  - Getting wxO credentials: <https://developer.watson-orchestrate.ibm.com/environment/production_import.md>
- Symplistic support: info@symplistic.ai
