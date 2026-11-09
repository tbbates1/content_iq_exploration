# Synthetic data

Two made-up data sources, each for a different test. Everything here is fictional: clients, projects, sites, companies and values. The values are not engineering-accurate, so don't "correct" them.

| | 1. `files_system_example/` | 2. `sample_documents/` |
|---|---|---|
| Stands in for | A whole client drive in OneDrive or SharePoint | The documents of one real-looking project |
| Size | 40 clients, 400 projects, 1,242 files | 1 project, 7 files |
| Files | One-line `.txt` RFQs | Multi-page PDF, DOCX, XLSX and a drawing |
| Tests | Can a search stay inside **one project** of a deep folder tree? | Can a search find values **across formats** (text, tables, cells, drawing callouts)? |
| ContentIQ agent | The client-drive agent (e.g. `Client_Drive`) | A separate agent (e.g. `Project_Files`) |
| Used by | The RFQ demo: [`README.md`](../README.md) | The retrieval test: [`docs/RETRIEVAL_TEST.md`](../docs/RETRIEVAL_TEST.md) |

## 1. `files_system_example/`: the client folder system

A simulated client drive, laid out like a sales team's OneDrive or SharePoint:

```
files_system_example/                      ← upload as the OneDrive folder "Clients"
  Bramhall_Copper/                         ← client (40)
    2016_Quebrada_Azul_Phase_1/            ← <year>_<project> (10 per client, 2006–2026)
      QAZ-16-RFQ-01.txt                    ← <site code>-<yy>-RFQ-<nn>.txt (2–4 per project)
      ...
    2021_Quebrada_Azul_Expansion/
      QAZ-21-RFQ-01.txt
      QAZ-21-RFQ-02.txt
```

Each file is one line with the RFQ's key values:

> Bramhall Copper 2021 Quebrada Azul Expansion RFQ 01: 16,500 kW drive, 72 poles, 10.13 rpm, 34.5 kV supply, delivery in 84 weeks (simulated, not real).

Project types are Phase 1 and 2, Expansion, Debottleneck, Relocation, Drive Upgrade, Retrofit, SAG and ball mill GMD, and Spares Service.

The drive has traps built in, the same kinds a real drive has:

- **The same site in different years.** Bramhall Copper has a Quebrada Azul Phase 1 in 2006 and in 2016, and an Expansion in 2018 (80 poles) and in 2021 (72 poles). "The current Azul project" or "the one ten years ago" has to pick the right folder.
- **The same site under different clients.** 20 of the 73 sites appear under more than one client.
- **The same file name in different projects.** The 1,242 files have only 1,145 distinct names: 90 names are shared by 187 files. For example, `LSE-22-RFQ-01.txt` exists in four 2022 projects of four clients. ContentIQ identifies files by name, so these may merge in its index.

The folder-map server (`backend/`) is built from this folder, so its project paths look like `Clients/Bramhall_Copper/2021_Quebrada_Azul_Expansion`.

## 2. `sample_documents/`: one project's documents

Realistic, multi-page engineering documents for one fictional project:

- **Client:** Bramhall Copper Corp.
- **Project:** Quebrada Azul Copper Expansion (Norte Alto Province, Calderón Verde), document prefix QAZ
- **Contractor:** Ostrander Engineering Services Ltd.

| Folder | File | Type |
|---|---|---|
| `spec/` | `QAZ-EP-0000-265-SPC-00006-Q` (.pdf, .docx) | Gearless mill drive specification, 33 pages |
| `datasheet/` | `QAZ-EP-0000-265-DST-00006-Q` (.pdf, .xlsx) | Drive datasheet, 18 pages, plus workbook |
| `mill/` | `QAZ-EP-3100-255-DST-55017-Q.pdf` | Grinding mill data sheet, 38 pages |
| `site/` | `QAZ-EP-0000-210-DBD-00002-B.pdf` | General site conditions, 9 pages |
| `drawing/` | `QAZ-5200-265-E-001_B.pdf` | Single line diagram, 1 sheet |

The values fit the 2021 Quebrada Azul Expansion in the folder system: a 16,500 kW SAG mill drive with 72 poles at 10.13 rpm, on a 34.5 kV supply. The documents aren't inside `files_system_example/` today, so the two tests stay separate.
