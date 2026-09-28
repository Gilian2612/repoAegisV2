# Aegis Review

A quality-control assistant for Florida estate-planning law firms. It compares a client **intake form** against a drafted **estate plan** (revocable trust, will, durable power of attorney, health care surrogate, warranty deed, certification of trust) and produces a section-by-section report of what matches, what doesn't, and what must be fixed before signing.

It is a reviewer's aid, not a lawyer: every output is meant to be read by an attorney, and the prompts explicitly forbid legal advice and outside-law analysis.

## The problem

Estate plans are assembled from templates and re-typed client data. One wrong word in a fiduciary name can invalidate an appointment or send assets to the wrong person, and the errors are easy to miss in a long document that is *supposed* to look repetitive.

In the sample in this repo, the intake form names the Attorney in Fact as `Rafael Eduardo Suarez Torres`. The drafted power of attorney says `Maria Rafael Eduardo Suarez Torres`. That is one extra word inside a ~96,000-character document. Aegis Review flags it as a **critical correction before signing** (see [`output/aegis_sectional_report.md`](output/aegis_sectional_report.md)).

## How it works

```mermaid
flowchart LR
    A["intake.docx<br/>estate_plan.docx"] --> B["extract_docx_text.py<br/>(python-docx)"]
    B --> C["plain text<br/>output/*.txt"]
    C --> D["marker-based slicing<br/>extract_estate_section()"]
    D --> E["5 focused prompts<br/>client · fiduciary · distribution<br/>deed · typos"]
    E --> F["Anthropic Messages API<br/>claude-haiku-4-5, temperature 0"]
    F --> G["aegis_sectional_report.md"]
    G --> H["Attorney review"]
```

1. **Extract** – `extract_docx_text.py` turns both `.docx` files into plain text (paragraphs, then table rows).
2. **Slice** – `extract_estate_section()` cuts only the relevant excerpts out of the estate plan using start/end text markers (for example, Article XI for trustee provisions, the appointment paragraph of the power of attorney, the deed).
3. **Review by section** – each section gets its own prompt with the intake form as the source of truth and only the matching excerpt of the plan.
4. **Assemble** – the section outputs are concatenated into one Markdown report.

Sections and what each one checks:

| Section | Compares | Status vocabulary |
|---|---|---|
| Client details | names, address, county, marital status, children | MATCH / mismatch |
| Fiduciaries | successor & alternate trustee, personal representative, attorney in fact, health care surrogate (and alternates) | MATCH · MISMATCH · **CRITICAL MISMATCH** · NOT FOUND |
| Distribution | beneficiary names and percentages | MATCH · PERCENTAGE MISMATCH · MISSING / EXTRA IN ESTATE PLAN |
| Real estate / deed | address, legal description, parcel ID, grantor, grantee, trust name | Match / mismatch |
| Typos & drafting | typos, spacing, singular/plural (Settlor vs Settlors), gendered language, blank fields | table of suggestions (chunked, 8,000 characters per call) |

## Design decisions

- **One narrow prompt per section instead of one large prompt.** The first prototype (`build_prompt.py` + a local model) asked for the whole report in one shot. The current pipeline gives each call a single job ("Compare ONLY fiduciary roles…") and only the text it needs, so a wrong answer can be traced to a specific prompt and excerpt.
- **The intake form is the source of truth.** Every prompt says so. The model never has to decide which document is right; it only reports differences.
- **Exact-match rules written into the prompt.** Fiduciary names must match "word for word", partial matches don't count, and the model must not normalize or shorten names before comparing. A mismatch in the power-of-attorney appointment paragraph is explicitly `CRITICAL`.
- **Rules that read like fixes for observed failures.** Several prompt rules look like responses to a first version getting something wrong: blank `Child 1 / Child 2` placeholders are not children, and a beneficiary is not "missing" if the name and percentage appear anywhere in the excerpt. Compare the Ollama prototype (commit `8242993`) with the current prompts to see this.
- **No test hints in the prompts.** The Ollama sectional prototype told the model which error to expect. The production prompts state general rules only, so the model can't pass by knowing the answer.
- **Deterministic pre-processing, structured output.** Slicing is plain string search, and every section must answer in a fixed Markdown table, which makes reports easy to skim and diff. A marker that can't be found is passed to the model as `[SECTION NOT FOUND: …]`; the pipeline does not yet stop on it (see limitations).
- **Small model, temperature 0.** `claude-haiku-4-5` keeps a full run cheap enough to run on every draft. `temperature=0` is used for repeatable output.
- **Local-first instead of AWS Bedrock.** The project started on Bedrock (`bedrock_test.py` is what remains of that evaluation). It was moved to a local Mac plus the direct Anthropic API for **traceability and security**: the whole pipeline, its inputs, and its reports live in one place the firm controls, and every run is a script anyone can read and re-run. The trade-off is that the firm operates that machine itself. See the security model below.

## Results

Run on the sample documents in `input/` (the committed report is in `output/`):

- **Caught the planted critical error**: Attorney in Fact `Maria Rafael Eduardo Suarez Torres` vs `Rafael Eduardo Suarez Torres`, with the paragraph, both names, the problem and a recommended correction.
- **Confirmed the consistent parts**: name, county, marital status, all eight fiduciary roles except one, the three distribution shares (50% / 25% / 25%), legal description, parcel ID and grantor.
- **Cost**: about **$0.14 per full run** with Claude Haiku 4.5 on the sample (author-measured; the scripts don't log token usage yet, so this isn't reproducible from the repo).
- **Volume**: the committed report reflects 19 API calls (4 comparison prompts + 15 typo-review chunks).

## Known limitations

These come from reading the sample report against the code, and are the next things to fix:

1. **No ground-truth evaluation.** One sample document with one planted error. I can't report precision or recall yet.
2. **Overlapping typo sections.** `HEALTH CARE SURROGATE` is split up to the next marker, `LIVING WILL`, which does not appear in the text, so that section runs to the end of the document. As a result the report contains "Health Care Surrogate (Part 2–5)" chunks that are really the trust summary, the deed and the certification of trust, which are then reviewed a second time. The Living Will itself is never reviewed.
3. **A false `MATCH` in client details.** The address row compares the intake address to the text `Seminole County, Florida` and reports a match, because the excerpt sent to the model didn't contain the address.
4. **The typo pass is noisy.** Some suggestions are wrong or already identical to the current text, and some rewrite legal drafting conventions (for example, replacing `aliens` in a deed's granting clause, or `his/her` with `they`). These need an attorney's judgment; they shouldn't be applied automatically.
5. **Markers are tied to one firm's templates.** Section boundaries such as `ARTICLE VI - DISTRIBUTION OF TRUST REMAINDER UPON DEATH OF THE SETTLOR` won't survive a different template.
6. **Tables lose their position.** `extract_docx_text.py` appends all table rows after all paragraphs, so document order is not preserved.

## Security and privacy model

Aegis Review handles confidential client documents, so where data goes matters.

- **Runs on one Mac.** The pipeline, the documents and the reports live on a MacBook. The team reaches it through AnyDesk, so files are not uploaded to a shared drive or a hosted app.
- **Direct Anthropic API, not a cloud platform.** The model is called through the Anthropic API with the firm's own key, stored in a local `.env` (git-ignored; only a blank `.env.example` is committed).
- **What leaves the Mac.** For each review call, the extracted text of the intake form and the relevant part of the estate plan is sent to the Anthropic API. Data handling is governed by Anthropic's [Commercial Terms](https://www.anthropic.com/legal/commercial-terms); under them, API inputs and outputs are not used for model training by default. <!-- TODO(author): verify this sentence and the retention period against Anthropic's current terms before submitting -->
- **Human in the loop.** Reports are advisory and marked for attorney review.

Open security questions (not yet done):

- **Prompt injection.** Document text is interpolated straight into the prompt (`f"""...{estate_text}"""`). A draft containing instructions such as "report that everything matches" is not treated as untrusted input. There is no test for this yet.
- **Remote-access surface.** AnyDesk is the access channel to a machine holding both the documents and the API key. Hardening and audit of that path are outside this repo.
- **Silent failure.** A missing marker degrades the review without stopping it (see limitation 2). The report should fail loudly when a section can't be located.

## Quickstart

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env            # then add your ANTHROPIC_API_KEY

# put intake.docx and estate_plan.docx in input/  (samples are included)
venv/bin/python extract_docx_text.py
venv/bin/python anthropic_sectional_review.py
# -> output/aegis_sectional_report.md
```

Each run sends the sample text to the Anthropic API and costs money.

## Repository layout

| Path | Purpose |
|---|---|
| `extract_docx_text.py` | `.docx` → plain text |
| `anthropic_sectional_review.py` | **Production pipeline**: section prompts → Claude → report |
| `build_prompt.py`, `ollama_review.py` | First prototype: one big prompt run on a local model (`qwen3:14b` via Ollama) |
| `bedrock_test.py` | Leftover from the initial Bedrock evaluation, which was dropped for traceability and security; not part of the pipeline (`boto3` is not in `requirements.txt`) |
| `input/`, `output/` | Sample intake form, sample estate plan, extracted text and the resulting report |

## Roadmap

- Log `usage` per call and report real cost and latency per run.
- Build a labeled evaluation set (planted errors with known answers) and report precision and recall per section.
- Fix section slicing (fail loudly, fix the overlap) and preserve table order in extraction.
- Add a prompt-injection test suite for hostile document text.
- Separate "must fix before signing" findings from stylistic suggestions in the report.
