# Aegis Review

Aegis Review is an internal legal document quality control prototype for comparing an estate planning intake form against a drafted estate planning packet.

The current proof of concept focuses only on document comparison. It does not yet connect to emails, Zoom, Teams, Outlook, client calls, or any external case management system.

## Current Scope

The current version compares:

* `input/intake.docx`
* `input/estate_plan.docx`

The intake form is treated as the source of truth unless otherwise stated.

Aegis currently reviews the estate plan by section and generates a markdown report.

## Main Review Areas

The current `sectional_review.py` script reviews:

1. Client details
2. Fiduciary roles
3. Distribution terms
4. Real estate and deed information
5. Typographical and drafting cleanup

## Important Current Finding

The project is being refined because the earlier general review missed a critical fiduciary name mismatch.

Example issue:

* Intake Form Attorney in Fact: `Rafael Eduardo Suarez Torres`
* Estate Plan Attorney in Fact: `Maria Rafael Eduardo Suarez Torres`

This should be treated as a critical mismatch because the estate plan added an extra word to the fiduciary name.

The `develop` branch includes stronger fiduciary name matching instructions inside `sectional_review.py`.

## Current Runtime Issue

The first four review sections run successfully:

* Client Details Review
* Fiduciary Review
* Distribution Review
* Real Estate / Deed Review

However, the final section, `Typographical and Drafting Cleanup Review`, currently sends the full estate plan text to the local model. On the Mac test environment, this section took approximately 19 minutes and timed out after 20 minutes.

The timeout occurred here:

```python
sections.append(call_ollama(build_typos_prompt(estate_text), timeout=1200))
```

For the next development session, this section should either be skipped temporarily or refactored to review smaller chunks instead of the entire estate plan at once.

## Recommended Next Step

For the next session, update `sectional_review.py` so that the typographical cleanup section does not block report generation.

Temporary option:

```python
print("Skipping Typographical and Drafting Cleanup Review for now...")
sections.append("## Typographical and Drafting Cleanup\n\nSkipped for this proof of concept to avoid long runtime. Focus is currently document comparison.")
```

Better long-term option:

Refactor the typo review to run in smaller document sections, such as:

* Revocable Trust
* Last Will and Testament
* Durable Power of Attorney
* Health Care Surrogate
* Living Will
* Warranty Deed
* Certification of Trust

## How to Run

Make sure Ollama is running and that the local model is available.

Check Ollama:

```bash
ollama list
```

Expected model:

```text
qwen3:14b
```

Activate the Python virtual environment:

```bash
source venv/bin/activate
```

Extract text from the Word documents:

```bash
python extract_docx_text.py
```

Run the sectional review:

```bash
python sectional_review.py
```

The final report should be created at:

```text
output/aegis_sectional_report.md
```

## Required Input Files

Place the estate planning documents here:

```text
input/intake.docx
input/estate_plan.docx
```

## Generated Output Files

The script creates files in:

```text
output/
```

Common generated files include:

```text
output/intake_text.txt
output/estate_plan_text.txt
output/aegis_sectional_report.md
```

## Git Branching Plan

* `main` is the production branch.
* `develop` is the working branch for changes and testing.

Current development work should continue in:

```bash
git checkout develop
```

After testing and approval, changes can later be merged into `main`.

## Current Runtime Note

During the Mac test, the script completed the first four review sections but timed out during the final typographical cleanup section.

Observed runtime:

- Total elapsed time before timeout: approximately 28 minutes and 41 seconds.
- Typographical and Drafting Cleanup Review ran for approximately 19 minutes before timing out.
- The timeout limit in the script was 1200 seconds, or 20 minutes.

The comparison sections completed before the timeout:

- Client Details Review
- Fiduciary Review
- Distribution Review
- Real Estate / Deed Review

The timeout occurred during:

- Typographical and Drafting Cleanup Review

Next step: refactor or temporarily skip the typographical cleanup section so the comparison report can complete reliably.

