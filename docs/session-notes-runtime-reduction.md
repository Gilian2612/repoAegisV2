# Aegis Review Runtime Reduction Session

## Branch

Current branch:

`feature/reduce-typo-runtime`

## Purpose

This branch reduces runtime by skipping the full-document Typographical and Drafting Cleanup section for now.

The goal of this session was to make sure Aegis can complete the core document comparison report without timing out.

## What Changed

The prior version attempted to run the typographical cleanup review against the entire estate plan text.

That section used:

```python
sections.append(call_ollama(build_typos_prompt(estate_text), timeout=1200))
```

During testing, this caused the script to time out after 1200 seconds.

The updated version skips that section temporarily and inserts a note in the final report.

## Test Environment

The test was run on Mac using:

```text
Ollama
qwen3:14b
Local Python virtual environment
```

Input files:

```text
input/intake.docx
input/estate_plan.docx
```

Output file:

```text
output/aegis_sectional_report.md
```

A copy of the test report should be saved at:

```text
docs/reports/aegis_sectional_report_runtime_test.md
```

Timer screenshot should be saved at:

```text
docs/images/runtime-timer-typo-timeout.png
```

## Test Result

The report completed after skipping the Typographical and Drafting Cleanup section.

The final report includes these sections:

```text
Client Details Review
Fiduciary Review
Distribution Review
Real Estate / Deed Review
Typographical and Drafting Cleanup, skipped
```

## Successful Finding

Aegis correctly detected the critical Durable Power of Attorney fiduciary mismatch.

The report flagged:

```text
Role: Attorney in Fact
Intake Form Exact Name: Rafael Eduardo Suarez Torres
Estate Plan Exact Name: Maria Rafael Eduardo Suarez Torres
Status: CRITICAL MISMATCH
```

This is the exact type of drafting error Aegis is intended to catch.

## Runtime Issue Resolved for Now

The previous test timed out during the Typographical and Drafting Cleanup Review because that section sent the entire estate plan text to the local model.

The current feature branch avoids that timeout by skipping the typographical review for now.

This is temporary.

## Fixes Completed

### 1. Children Field False Positive, Fixed

The Client Details Review previously treated blank placeholder rows as actual children:

```text
Child 1
Child 2
Child 3
```

This caused a false mismatch because the Estate Plan correctly stated that the client had no children.

This issue has now been fixed in `build_client_details_prompt`.

Aegis now treats blank child placeholder rows as placeholders only. A child is only treated as listed if a real child name appears next to the child field.

Confirmed test result:

```text
Children | Child 1 / Child 2 / Child 3, no names provided | No children listed | MATCH
```

Status:

```text
Fixed
```

## Known False Positives Still Pending

### 1. Distribution Review

The Distribution Review incorrectly stated that the beneficiaries were missing from the Estate Plan.

The report showed:

```text
Maria Desiree Suarez Guevara, 50%, Missing in Estate Plan
Rafael Eduardo Suarez Torres, 25%, Missing in Estate Plan
Gioconda Del Carmen Guevara, 25%, Missing in Estate Plan
```

This appears to be a false positive because the estate plan contains the Article VI distribution language.

Future fix:

```text
Review build_distribution_prompt and confirm whether extract_estate_section is properly capturing Article VI through Article VII.
```

## Typographical Cleanup Status

Typographical and Drafting Cleanup is currently skipped.

Reason:

```text
The full-document typo review caused a timeout because the entire estate plan text was sent to the local model.
```

Future fix options:

1. Keep it skipped during the proof of concept.
2. Refactor typographical review into smaller chunks.
3. Run typographical review document by document, such as:

   * Revocable Trust
   * Last Will and Testament
   * Durable Power of Attorney
   * Health Care Surrogate
   * Living Will
   * Warranty Deed
   * Certification of Trust

## Next Development Steps

Recommended next fixes:

1. Fix Distribution Review prompt or section extraction.
2. Later refactor Typographical and Drafting Cleanup by chunks.
3. After testing, merge this feature branch into `develop`.
4. Only merge `develop` into `main` after the report is stable.

## Current Git Strategy

```text
main = production
develop = integration/testing
feature/reduce-typo-runtime = current runtime reduction work
```

DO NOT MERGE INTO MAIN YET.

WSRM
