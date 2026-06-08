import os
import requests

MODEL = "qwen3:14b"

INTAKE_PATH = os.path.join("output", "intake_text.txt")
ESTATE_PATH = os.path.join("output", "estate_plan_text.txt")
REPORT_PATH = os.path.join("output", "aegis_sectional_report.md")


def read_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def call_ollama(prompt, timeout=900):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_ctx": 32768
            }
        },
        timeout=timeout
    )

    response.raise_for_status()
    return response.json()["response"]


def extract_estate_section(estate_text, start_marker, end_markers):
    start_index = estate_text.find(start_marker)

    if start_index == -1:
        return f"[SECTION NOT FOUND: {start_marker}]"

    end_index = len(estate_text)

    for marker in end_markers:
        marker_index = estate_text.find(marker, start_index + len(start_marker))
        if marker_index != -1:
            end_index = min(end_index, marker_index)

    return estate_text[start_index:end_index]


def build_client_details_prompt(intake_text, estate_text):
    estate_excerpt = "\n\n".join([
        extract_estate_section(
            estate_text,
            "Dear Maria Dayana Suarez:",
            ["MARIA DAYANA SUAREZ\nREVOCABLE TRUST AGREEMENT"]
        ),
        extract_estate_section(
            estate_text,
            "THIS TRUST AGREEMENT",
            ["ARTICLE I - FUNDING OF TRUST"]
        ),
        extract_estate_section(
            estate_text,
            "LAST WILL AND TESTAMENT",
            ["Article I"]
        )
    ])

    # Fix:
    # The intake template includes blank placeholder rows labeled Child 1, Child 2, and Child 3.
    # Those labels should not be treated as actual children unless a real name is provided.
    return f"""
You are Aegis Review.

Compare ONLY client details from the Intake Form against the Estate Plan excerpts.

The Intake Form is the source of truth.

Important rules for children:
- Do not treat blank placeholder rows such as "Child 1", "Child 2", or "Child 3" as actual children.
- Only treat a child as listed if a real child name appears next to the child field.
- If the intake has child placeholder labels but no child names, treat the intake as having no listed children.
- If the Estate Plan says the client has no children and the intake only contains blank child placeholders, this is a MATCH, not a mismatch.

Do not perform legal compliance review.
Do not add outside law.
Do not summarize generally.
Only compare names, address, county, marital status, and children.

Required output format:

## Client Details Review

| Item | Intake Form | Estate Plan | Status |
|---|---|---|---|

Then list any issues under:

### Client Details Issues

INTAKE FORM:
{intake_text}

ESTATE PLAN EXCERPTS:
{estate_excerpt}

Final instruction:
Output only the Client Details Review.
"""


def build_fiduciary_prompt(intake_text, estate_text):
    estate_excerpt = "\n\n".join([
        extract_estate_section(
            estate_text,
            "ARTICLE XI - PROVISIONS REGARDING TRUSTEE",
            ["ARTICLE XII - PROVISIONS FOR RETIREMENT ACCOUNTS"]
        ),
        extract_estate_section(
            estate_text,
            "Article VII",
            ["[The remainder of this page is intentionally left blank. Signature pages follow.]"]
        ),
        extract_estate_section(
            estate_text,
            "DURABLE FAMILY POWER OF ATTORNEY",
            ["BANKING:"]
        ),
        extract_estate_section(
            estate_text,
            "HEALTH CARE SURROGATE",
            ["II.\tPowers.", "II. Powers.", "Powers."]
        )
    ])

    return f"""
You are Aegis Review.

Compare ONLY fiduciary roles from the Intake Form against the Estate Plan excerpts.

The Intake Form is the source of truth.

Important rules for exact fiduciary name matching:
- Names must match exactly.
- Compare the full fiduciary name from the Intake Form against the full fiduciary name in the Estate Plan.
- Do not treat a partial name match as a match.
- Do not ignore extra words in a person's name.
- Do not ignore missing words in a person's name.
- Do not treat a name as matching if the Estate Plan adds an extra first name, middle name, last name, prefix, suffix, or any other word.
- Do not treat a name as matching if the Estate Plan removes any part of the name.
- If the Intake Form says "Rafael Eduardo Suarez Torres" and the Estate Plan says "Maria Rafael Eduardo Suarez Torres", this is NOT a match.
- If a fiduciary name mismatch appears in the Durable Power of Attorney appointment paragraph, mark it as CRITICAL.
- The Durable Power of Attorney appointment paragraph must be checked word by word.
- Do not say "matches", "consistent", or "aligned" unless the full names are identical.

Compare these roles:
- Successor Trustee
- Alternate Trustee
- Personal Representative
- Alternate Personal Representative
- Attorney in Fact
- Alternate Attorney in Fact
- Health Care Surrogate
- Alternate Health Care Surrogate

The most important expected issue in this test:
The Intake Form says the Attorney in Fact is "Rafael Eduardo Suarez Torres".
The Estate Plan may say "Maria Rafael Eduardo Suarez Torres".
If so, this is a Critical Correction Before Signing.

Required output format:

## Fiduciary Review

| Role | Intake Form Exact Name | Estate Plan Exact Name | Status |
|---|---|---|---|

## Critical Fiduciary Corrections Before Signing

| Issue | Document | Section / Paragraph | Intake Form Exact Name | Estate Plan Exact Name | Problem | Recommended Correction |
|---|---|---|---|---|---|---|

Status rules:
- Use "MATCH" only if the full names are exactly identical.
- Use "CRITICAL MISMATCH" if a Durable Power of Attorney fiduciary name differs by even one word.
- Use "MISMATCH" if any other fiduciary name differs by even one word.
- Use "NOT FOUND" if the role appears in the intake but cannot be located in the Estate Plan excerpt.

Rules:
- Do not perform legal compliance review.
- Do not add outside law.
- Do not infer that two names are the same person.
- Do not normalize, shorten, or clean names before comparing them.
- Do not say "matches" unless the exact full names match word for word.
- If the Estate Plan adds "Maria" before "Rafael Eduardo Suarez Torres", flag it as a CRITICAL MISMATCH.
- Output only the Fiduciary Review.

INTAKE FORM:
{intake_text}

ESTATE PLAN EXCERPTS:
{estate_excerpt}
"""


def build_distribution_prompt(intake_text, estate_text):
    estate_excerpt = extract_estate_section(
        estate_text,
        "ARTICLE VI - DISTRIBUTION OF TRUST REMAINDER UPON DEATH OF THE SETTLOR",
        ["ARTICLE VII - PROVISION REGARDING MINORS"]
    )

    return f"""
You are Aegis Review.

Compare ONLY distribution beneficiaries and percentages from the Intake Form against the Estate Plan excerpt.

The Intake Form is the source of truth.

Important rules for distribution matching:
- Compare beneficiary names and percentages exactly.
- A beneficiary is not missing if the Estate Plan lists the beneficiary followed by a percentage.
- Recognize distribution lines even if they are written with a colon, bullet point, dash, or plain text.
- Treat these formats as valid Estate Plan distribution entries:
  "Maria Desiree Suarez Guevara: 50% of the assets in the Trust Estate"
  "Rafael Eduardo Suarez Torres: 25% of the assets in the Trust Estate"
  "Gioconda Del Carmen Guevara: 25% of the assets in the Trust Estate"
- Extract the percentage from the Estate Plan line even if extra words appear after the percentage.
- Do not mark a beneficiary as missing if the full beneficiary name and percentage appear anywhere in the Estate Plan excerpt.
- Use MATCH only if the beneficiary name and percentage match.
- Use PERCENTAGE MISMATCH if the beneficiary exists but the percentage differs.
- Use MISSING IN ESTATE PLAN only if the beneficiary name does not appear in the Estate Plan excerpt at all.

Required output format:

## Distribution Review

| Beneficiary | Intake Form Share | Estate Plan Exact Text | Estate Plan Share | Status |
|---|---|---|---|---|

## Distribution Issues

Status rules:
- Use MATCH if the beneficiary name appears in both documents and the percentage is the same.
- Use PERCENTAGE MISMATCH if the beneficiary name appears but the percentage is different.
- Use MISSING IN ESTATE PLAN only if the beneficiary name does not appear in the Estate Plan excerpt.
- Use EXTRA IN ESTATE PLAN if the Estate Plan contains a beneficiary not listed in the Intake Form.

Rules:
- Do not perform legal compliance review.
- Do not add outside law.
- Check that beneficiary names match exactly.
- Check that percentages match exactly.
- Quote the Estate Plan distribution line where possible.
- Do not say a beneficiary is missing if the name appears anywhere in the Estate Plan excerpt.
- Output only the Distribution Review.

INTAKE FORM:
{intake_text}

ESTATE PLAN EXCERPT:
{estate_excerpt}
"""


def build_real_estate_prompt(intake_text, estate_text):
    estate_excerpt = "\n\n".join([
        extract_estate_section(
            estate_text,
            "WARRANTY DEED",
            ["CERTIFICATION OF TRUST"]
        ),
        extract_estate_section(
            estate_text,
            "CERTIFICATION OF TRUST",
            ["FURTHER AFFIANT SAYETH NOT."]
        )
    ])

    return f"""
You are Aegis Review.

Compare ONLY real estate and deed information from the Intake Form against the Estate Plan excerpts.

The Intake Form is the source of truth.

Compare:
- Homestead address
- Legal description
- Parcel ID / Folio
- Grantor
- Grantee
- Trust name used in deed
- Property address used in certification of trust

Required output format:

## Real Estate / Deed Review

| Item | Intake Form | Estate Plan | Status |
|---|---|---|---|

## Real Estate / Deed Issues

Rules:
- Do not perform legal compliance review.
- Do not add outside law.
- Do not recommend title examination unless the issue is a mismatch between the documents.
- Output only the Real Estate / Deed Review.

INTAKE FORM:
{intake_text}

ESTATE PLAN EXCERPTS:
{estate_excerpt}
"""


def build_typos_prompt(estate_text):
    return f"""
You are Aegis Review.

Review ONLY the Estate Plan text below for typographical and drafting cleanup issues.

Do not perform legal compliance review.
Do not compare to outside law.
Do not make broad legal recommendations.

Find:
- Typos
- Extra spaces
- Grammar issues
- Singular/plural drafting inconsistencies
- Settlor vs Settlors issues
- Trustee vs Trustees issues
- his/her or gendered language cleanup when obvious
- Placeholder or blank field issues that appear unusual

Required output format:

## Typographical and Drafting Cleanup

| Issue | Where | Current Wording | Suggested Correction |
|---|---|---|---|

Rules:
- Quote the current wording when possible.
- Output only the Typographical and Drafting Cleanup section.

ESTATE PLAN TEXT:
{estate_text}
"""


def main():
    if not os.path.exists(INTAKE_PATH):
        print(f"ERROR: Missing file: {INTAKE_PATH}")
        print("Run: python extract_docx_text.py")
        exit()

    if not os.path.exists(ESTATE_PATH):
        print(f"ERROR: Missing file: {ESTATE_PATH}")
        print("Run: python extract_docx_text.py")
        exit()

    intake_text = read_file(INTAKE_PATH)
    estate_text = read_file(ESTATE_PATH)

    sections = []

    print("Running Client Details Review...")
    sections.append(call_ollama(build_client_details_prompt(intake_text, estate_text)))

    print("Running Fiduciary Review...")
    sections.append(call_ollama(build_fiduciary_prompt(intake_text, estate_text)))

    print("Running Distribution Review...")
    sections.append(call_ollama(build_distribution_prompt(intake_text, estate_text)))

    print("Running Real Estate / Deed Review...")
    sections.append(call_ollama(build_real_estate_prompt(intake_text, estate_text)))

    print("Skipping Typographical and Drafting Cleanup Review for now...")
    sections.append(
        "## Typographical and Drafting Cleanup\n\n"
        "Skipped for this proof of concept to avoid long runtime. "
        "Current priority is document comparison: client details, fiduciaries, distributions, and real estate/deed review.\n\n"
        "Known issue: the prior full-document typographical review timed out because it sent the entire estate plan text to the local model."
    )

    final_report = "# Aegis Review Sectional Report\n\n"
    final_report += "This report compares the Intake Form against the Estate Plan Draft by section.\n\n"
    final_report += "\n\n---\n\n".join(sections)

    os.makedirs("output", exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(final_report)

    print(f"Done. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()