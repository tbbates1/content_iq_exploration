# Retrieval test: one project across formats

A fully fictional set of engineering documents in [`synthetic_data/sample_documents/`](../synthetic_data/sample_documents/) for testing whether ContentIQ (or any search or RAG system) can find answers across formats (PDF, DOCX, XLSX, drawing). Everything here is invented. The client, project, companies, places and values are not real, and the values are not engineering-accurate. The test checks retrieval and consistency only.

How to load the files and ask the questions in ContentIQ is in [`CONTENTIQ_GUIDE.md`](CONTENTIQ_GUIDE.md), section 7.

## Fictional project

- Client: Bramhall Copper Corp.
- Project: Quebrada Azul Copper Expansion (Norte Alto Province, Calderón Verde)
- Contractor: Ostrander Engineering Services Ltd.
- Document prefix: QAZ

## Documents (`synthetic_data/sample_documents/`)

| Folder | File | Type |
|---|---|---|
| `spec/` | `QAZ-EP-0000-265-SPC-00006-Q` (.pdf, .docx) | Gearless mill drive specification, 33 pages |
| `datasheet/` | `QAZ-EP-0000-265-DST-00006-Q` (.pdf, .xlsx) | Drive datasheet, 18 pages, plus workbook |
| `mill/` | `QAZ-EP-3100-255-DST-55017-Q.pdf` | Grinding mill data sheet, 38 pages |
| `site/` | `QAZ-EP-0000-210-DBD-00002-B.pdf` | General site conditions, 9 pages |
| `drawing/` | `QAZ-5200-265-E-001_B.pdf` | Single line diagram, 1 sheet |

## How to test

Load the files in `synthetic_data/sample_documents/` into the search or RAG source, then ask the questions below. The agent should answer from its index and does not see the files directly. Ask only the question sentence (the heading text), not the source notes.

A correct answer gives the value and the document it came from. A right value with no source is a partial pass. For Q4 and Q5, an answer that cites only one of the two sources is a partial pass. Some values also appear in other documents, and citing one of those is fine as long as the value is right.

Q1, Q2 and Q3 have one source. Q4 and Q5 need two sources at once. Q6 needs the drawing alone.

---

## Q1. What seismic zone applies to the site, and what is the peak ground acceleration?

**Source (one):** `synthetic_data/sample_documents/site/QAZ-EP-0000-210-DBD-00002-B.pdf`, **page 8**, section 2.6 Seismic Parameters: seismic zone **4**, PGA **0.42 g**.

**Expected answer:** Seismic zone 4, with a peak ground acceleration of 0.42 g.

---

## Q2. How many poles does the SAG mill drive motor have, and what is its rated speed?

**Source (one):** `synthetic_data/sample_documents/spec/QAZ-EP-0000-265-SPC-00006-Q.pdf`, **page 15**, section "Pole Count and Rated Speed": **72 poles**, **10.13 rpm**.

**Expected answer:** 72 poles, running at 10.13 rpm.

---

## Q3. What is the full-load current of the motor control center at 380 V, and what is its rated power?

**Source (one):** `synthetic_data/sample_documents/datasheet/QAZ-EP-0000-265-DST-00006-Q.pdf`, **page 17**, motor control center table (3220-MCC-01): full-load current **855.7 A**, rated power **450 kW**.

**Expected answer:** 855.7 A at 380 V, for a 450 kW load.

---

## Q4. What is the SAG mill critical speed, and what percentage of critical is the operating speed?

**Two sources (grinding mill data sheet PDF + datasheet workbook):**
- **Source 1:** `synthetic_data/sample_documents/mill/QAZ-EP-3100-255-DST-55017-Q.pdf`, **page 3**, SAG mill mechanical table: critical speed **13.51 rpm**, operating speed **10.13 rpm** (**75.0%** of critical).
- **Source 2:** `synthetic_data/sample_documents/datasheet/QAZ-EP-0000-265-DST-00006-Q.xlsx`, sheet **-01**, cell **D17** (critical speed **13.51**) and cell **D18** (**75.0%**).

**Expected answer:** The critical speed is 13.51 rpm. The operating speed of 10.13 rpm is 75.0% of critical.

---

## Q5. What is the full-load current of the ball mill drive at 34.5 kV?

**Two sources (diagram + datasheet):**
- **Source 1:** `synthetic_data/sample_documents/drawing/QAZ-5200-265-E-001_B.pdf`, **page 1**, callout **3210-MTR-02**: "12,000 kW, I_FL **217.9 A** at 34.5 kV".
- **Source 2:** `synthetic_data/sample_documents/datasheet/QAZ-EP-0000-265-DST-00006-Q.pdf`, **page 12**, 3210-MTR-02 electrical table: full-load current **217.9 A**.

**Expected answer:** 217.9 A at 34.5 kV, for a 12,000 kW drive.

---

## Q6. What is the rating and impedance of transformer 3210-XFR-02, and which bus feeds it? (drawing only)

**Source (one):** `synthetic_data/sample_documents/drawing/QAZ-5200-265-E-001_B.pdf`, **page 1**, callout **3210-XFR-02**: "20.0 MVA, 7.5% impedance, taps ±2 x 2.5% (5 positions), fed from 34.5 kV bus".

**Expected answer:** 20.0 MVA, 7.5% impedance, fed from the 34.5 kV bus.

**Why this is drawing-only:** the feed to the 34.5 kV bus appears only on the single line diagram. The rating and impedance also appear in other documents, so a correct answer may cite them, but the bus feed should come from the drawing.
