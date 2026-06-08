\# Aegis Review Runtime Reduction Session



\## Branch



Current branch:



`feature/reduce-typo-runtime`



\## Purpose



This branch reduces runtime by skipping the full-document Typographical and Drafting Cleanup section for now.



The goal of this session was to make sure Aegis can complete the core document comparison report without timing out.



\## What Changed



The prior version attempted to run the typographical cleanup review against the entire estate plan text.



That section used:



```python

sections.append(call\_ollama(build\_typos\_prompt(estate\_text), timeout=1200))



During testing, this caused the script to time out after 1200 seconds.



The updated version skips that section temporarily and inserts a note in the final report.



Test Environment



The test was run on Mac using:



Ollama

qwen3:14b

Local Python virtual environment



Input files:



input/intake.docx

input/estate\_plan.docx



Output file:



output/aegis\_sectional\_report.md



A copy of the test report should be saved at:



docs/reports/aegis\_sectional\_report\_runtime\_test.md



Timer screenshot should be saved at:



docs/images/runtime-timer-typo-timeout.png

Test Result



The report completed after skipping the Typographical and Drafting Cleanup section.



The final report includes these sections:



Client Details Review

Fiduciary Review

Distribution Review

Real Estate / Deed Review

Typographical and Drafting Cleanup, skipped

Successful Finding



Aegis correctly detected the critical Durable Power of Attorney fiduciary mismatch.



The report flagged:



Role: Attorney in Fact

Intake Form Exact Name: Rafael Eduardo Suarez Torres

Estate Plan Exact Name: Maria Rafael Eduardo Suarez Torres

Status: CRITICAL MISMATCH



This is the exact type of drafting error Aegis is intended to catch.



Runtime Issue Resolved for Now



The previous test timed out during the Typographical and Drafting Cleanup Review because that section sent the entire estate plan text to the local model.



The current feature branch avoids that timeout by skipping the typographical review for now.



This is temporary.



Known False Positives

1\. Children Field



The Client Details Review incorrectly treated blank placeholder rows as actual children:



Child 1

Child 2

Child 3



These should not be treated as actual children unless real names appear next to those fields.



Future prompt fix:



Do not treat blank placeholder rows such as Child 1, Child 2, or Child 3 as actual children. Only treat a child as listed if a real name appears next to the child field.

2\. Distribution Review



The Distribution Review incorrectly stated that the beneficiaries were missing from the Estate Plan.



The report showed:



Maria Desiree Suarez Guevara, 50%, Missing in Estate Plan

Rafael Eduardo Suarez Torres, 25%, Missing in Estate Plan

Gioconda Del Carmen Guevara, 25%, Missing in Estate Plan



This appears to be a false positive because the estate plan contains the Article VI distribution language.



Future fix:



Review build\_distribution\_prompt and confirm whether extract\_estate\_section is properly capturing Article VI through Article VII.

Typographical Cleanup Status



Typographical and Drafting Cleanup is currently skipped.



Reason:



The full-document typo review caused a timeout because the entire estate plan text was sent to the local model.



Future fix options:



Keep it skipped during the proof of concept.

Refactor typographical review into smaller chunks.

Run typographical review document by document, such as:

Revocable Trust

Last Will and Testament

Durable Power of Attorney

Health Care Surrogate

Living Will

Warranty Deed

Certification of Trust

Next Development Steps



Recommended next fixes:



Fix Client Details prompt so blank child placeholders are ignored.

Fix Distribution Review prompt or section extraction.

Later refactor Typographical and Drafting Cleanup by chunks.

After testing, merge this feature branch into develop.

Only merge develop into main after the report is stable.

Current Git Strategy

main = production

develop = integration/testing

feature/reduce-typo-runtime = current runtime reduction work



DO NOT MERGE INTO MAIN (Yet) 

WSRM 

