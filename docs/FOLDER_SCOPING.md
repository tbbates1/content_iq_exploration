# Searching one project folder in ContentIQ

**The question:** can you link one OneDrive folder (such as `Clients/`) once, and then have a search look only inside one project subfolder?

**The answer, tested against the API on 2026-11-09:** not with ContentIQ as it works today. You link OneDrive only once, but one agent can't be told to search a single subfolder. Each agent is the only boundary a search respects.

The architecture this feeds into is drawn in [`architecture/rfq-assistant.html`](architecture/rfq-assistant.html).

## Why one agent can't search a subfolder

1. **The chat call has no place to say which folder.** `POST /api/headless/chat` takes only `agent_id`, `message`, `thread_id` and `stream`. Nothing else in the API filters a search.
2. **ContentIQ doesn't record the folder.** Each file is stored under its file name only. For example, `Project_Files` lists `QAZ-EP-0000-265-SPC-00006-Q.pdf`, not `Projects/.../spec/QAZ-EP-0000-265-SPC-00006-Q.pdf`. A filter would have no folder path to match against.
3. **Files with the same name in different folders may collide.** Because files are identified by name, two projects that both have an `RFQ.pdf` may overwrite or merge in one agent. In `synthetic_data/Clients`, 1,242 files share only 1,145 names.
4. **The only labels stored on each file are access roles.** These are for permissions (`access_roles`, `tenant_id`). They depend on who is asking, not on what is asked, and changing them needs a website login.

## The two options that work today

| Option | Pros | Cons |
|---|---|---|
| **One agent per subfolder** | The search stays strictly inside one project. | Each agent has to be created in the website. The API can't see inside folders to set it up. |
| **One agent for everything, with the project named in the question** | You set up only one agent. The RFQ Assistant rewrites a vague question into an exact one, e.g. *"Bramhall Copper 2021 Quebrada Azul Expansion: how many poles?"* | This only works when the file names or the text say which project they belong to, because the folder path isn't stored. Files with the same name may collide. |

## What to ask Symplistic

Two changes would make "link once, search a subfolder" work as intended:

1. **Record each file's folder path when it's loaded** from OneDrive or SharePoint, and identify files by full path instead of by name alone. This also fixes the name collisions.
2. **Add a folder filter to the chat call**, for example `"folder": "Clients/Bramhall_Copper/2021_Quebrada_Azul_Expansion"`.

With both, the architecture stays almost the same. The project catalog would store a folder path instead of an agent ID, and the RFQ Assistant would pass that path with every question.

If they only offer one agent per project instead, ask for these:

3. Let the API key create an agent. Today only the website can.
4. Let the API key list folders below the top level. Today only the website can.
5. Fix the documented MCP endpoint `https://backend.contentiq.symplistic.ai/mcp/`, which returns 404 for our key.
6. OneDrive Connect signs in as one account. Confirm whether everyone who asks then gets answers from every file that account can open.
7. Let the API key call raw retrieval (`/api/external/retrieve`), with a setting for how many results to return. Our own agent needs the passages and their sources to check and filter them; a finished answer isn't enough. Today, passages are only reachable through the wxO tool, which returns a fixed 15 (`answer_top_n`).
8. **Make `source_hint` work as a filter**, and let it take a list of file names. The backend already has an empty `source_filter` field. If a hint filled it, one parent-folder agent plus our own OneDrive map could search one project. This is the smallest change that would make that design work.
9. Fix the domain-knowledge error that appears in every tool response: `'MongoDB' object has no attribute 'list_agent_domain_knowledge'`.
10. If we connect our own vector store (`POST /api/milvus/credentials`): which embedding model and chunk fields does ContentIQ write? Does the setting apply to every agent on the service account? Do existing agents need re-ingesting?

## What the API key can and can't do

Tested 2026-11-09 against the backend API spec at <https://backend.contentiq.symplistic.ai/apidocs/>.

| Task | With the API key |
|---|---|
| Chat with an agent | Yes. [Q2](RETRIEVAL_TEST.md) returned 72 poles and 10.13 rpm with 3 sources in about 27 s. |
| List OneDrive | Top level only. Query parameters are ignored. |
| Load OneDrive files or whole folders into an agent | Yes (`POST /api/headless/onedrive/ingest`), but only into an agent that already exists. |
| Create an agent | No. Website only. |
| List subfolders, or list agents | No. Website only; the key gets 401 `session_expired`. |
| Read the schedule, plan limits and agent ID | Yes, through the undocumented `GET /api/headless/scheduler/config`. |
| List or delete an agent's files and tables | Yes. |
| MCP | 404, also with a proper MCP `initialize` call (retested 2026-11-09). Its documented tools mirror the headless API (chat, ingest, schedules, sources). None of them returns raw passages or takes a file filter, so a working MCP server wouldn't solve scoping. |
| Get raw search results (passages, not an answer) | No. `POST /api/external/retrieve?agent_id=…` with `{"question": …}` exists and returns `results: [{content, source}]`, but the key gets 401 `Unauthorized`. The spec has no setting for how many results it returns. The wxO tool does return passages, through a different endpoint (see "Inside watsonx Orchestrate"). |
| How many results per chat call | One composed answer that cites 1–3 files in our tests (Q2: 3, SAG motor power: 1, with a file named in the question: 2). Behind it are up to 15 passages and one table. There's no setting for how many. |
| Steer the search by naming a file in the question | No, either through chat or through the wxO tool's `source_hint`. "Using only `QAZ-EP-3100-255-DST-55017-Q.pdf`…" cited the spec PDF and a datasheet table, not the named file. |

## Inside watsonx Orchestrate (checked 2026-11-09)

Read through the wxO API with `WXO_API_KEY`. For the `source_hint` test, we sent six questions to `Project_Files` with `POST /v1/orchestrate/runs` (`{agent_id, message}`). Each run's `step_history`, from `GET /v1/orchestrate/threads/{thread_id}/messages`, shows the tool's inputs and the tool's full response, including a `debug` block.

- **`Project_Files` in wxO** runs on `azure-openai/gpt-5.4` (style `react_intrinsic`), with 25,000 characters of instructions written by ContentIQ. It has one tool and no wxO knowledge base.
- **The tool** is named `symplisticai_tool_<agent>_a_<id>` (for `Project_Files`: `symplisticai_tool_project_files_a_…`). It is a Python tool. It posts to `https://backend.contentiq.symplistic.ai/api/external/contentiq-tool-query` and signs each request with an HMAC secret stored in the tool's code. That makes it specific to one agent: the agent ID is built in.
- **Tool inputs:** `query` (required) and an optional `source_hint`, described as "Exact drawing/PDF filename or registered source identifier when the user names one", plus thread and turn IDs. There is no input for how many results.
- **Calls per question:** one. The instructions say "Call the retrieval tool once for the user's knowledge question, then answer from the information returned." Every test made exactly one call.
- **Results per call: up to 15 text passages and one spreadsheet table.** The debug block shows `answer_top_n: 15`, a backend setting. Each passage comes back with its text and file name. A call took about 17 s; the spreadsheet search and a catalog check took most of that.
- **`source_hint` doesn't restrict the search, and doesn't noticeably favour the named file either.** The agent filled it in whenever the question named a file. But the response's `source_filter` stayed empty every time, and the backend's file-name matcher (`explicit_filenames`) matched nothing.

  | The question named | Passages from the named file | Passages from other files |
  |---|---|---|
  | No file ([Q2](RETRIEVAL_TEST.md)) | n/a | 15 from 4 files, plus 1 table |
  | Site conditions PDF, asked about poles (wrong file) | 0 | 13, plus 1 table |
  | Mill data sheet PDF, asked about critical speed (right file) | 0 | 13, plus 1 table |
  | A file that doesn't exist | n/a | 12, plus 1 table |
  | Single line diagram, asked which bus feeds 3210-XFR-02 | 5 | 10, plus 1 table |
  | Mill data sheet number without `.pdf` | 1 | 14, plus 1 table |

  In the right-file test, the agent answered from the datasheet and said it couldn't confirm the value came from the named file.
- **The backend has a file filter that nothing reaches.** The response has `source_filter`, `needs_source_choice`, `source_cards` and `force_source_choice` fields, so ContentIQ can probably narrow a search to chosen files. Nothing the tool sends fills them today. See item 8 under "What to ask Symplistic".
- **What this means for our design:** our own wxO agent can attach this tool and read the passages and file names it returns. That is the raw retrieval the API key can't reach. It could then drop passages from files outside the chosen project. But that only filters the top 15 across the whole agent. With 400 similar projects in one agent, the right project's files may not make the top 15 at all. So a parent-folder agent needs a working file filter. Until there is one, use one agent per project.
- **Built and tested 2026-11-09:** our own `project_searcher` agent calls the search tool of the client-drive agent without problems, together with our folder-map MCP tools. See [`backend/README.md`](../backend/README.md).
- **Backend error:** every response's debug block shows `'MongoDB' object has no attribute 'list_agent_domain_knowledge'`. The domain-knowledge step fails and is skipped.
- **Security:** anyone who can download tools in this wxO instance can read the tool's signing secret. Ask Symplistic how to rotate it, and keep downloaded copies of the tool out of the repo.

## Lead: our own vector store (not tested)

ContentIQ can write its index to a vector store we own. `POST /api/milvus/credentials` takes a `uri`, a `token` and an optional `provider`: Milvus/Zilliz, Qdrant or Azure AI Search. The MCP docs list the same as `ciq_set_milvus_credentials`.

If the passages land in our store, our backend could run the search itself and filter it to the project's file names, with no change from Symplistic. Three things are unknown:

- The setting is per service account, so it would also move every other agent in the tenant.
- Existing agents would probably need re-ingesting.
- Our backend would have to embed questions with the same model ContentIQ uses.

Don't call this endpoint on a shared tenant before checking with Symplistic (item 10).

## How to test the collision risk

1. Upload `synthetic_data/Clients` to the top level of OneDrive.
2. Create one test agent in the website and load the whole `Clients` folder into it (step 2 of the main [`README.md`](../README.md)).
3. Count its files with `GET /api/headless/milvus/sources?agent_id=$CONTENTIQ_DRIVE_AGENT_ID`. If it shows fewer than 1,242, files with the same name were merged.
4. Ask it a vague question and an exact one:
   - *"How many poles did the Quebrada Azul Expansion drive have?"* This is ambiguous: the 2018 job had 80 poles and the 2021 job had 72.
   - *"How many poles did the Bramhall Copper 2021 Quebrada Azul Expansion drive have?"* The answer should be 72.
