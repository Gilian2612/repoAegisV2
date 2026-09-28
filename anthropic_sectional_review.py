import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5"

INTAKE_PATH = os.path.join("output", "intake_text.txt")
ESTATE_PATH = os.path.join("output", "estate_plan_text.txt")
REPORT_PATH = os.path.join("output", "aegis_sectional_report.md")

TYPO_CHUNK_SIZE = 8000

TYPO_SECTIONS = [
    "REVOCABLE TRUST AGREEMENT",
    "LAST WILL AND TESTAMENT",
    "DURABLE FAMILY POWER OF ATTORNEY",
    "HEALTH CARE SURROGATE",
    "LIVING WILL",
    "WARRANTY DEED",
    "CERTIFICATION OF TRUST",
]


def read_file(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def call_claude(prompt):
    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        temperature=0,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return message.content[0].text


def extract_estate_section_nth(estate_text, start_marker, end_markers, occurrence=1):
    start_index = 0
    for _ in range(occurrence):
        found = estate_text.find(start_marker, start_index)
        if found == -1:
            return f"[SECTION NOT FOUND: {start_marker}]"
        start_index = found + len(start_marker)

    end_index = len(estate_text)
    for marker in end_markers:
        marker_index = estate_text.find(marker, start_index)
        if marker_index != -1:
            end_index = min(end_index, marker_index)

    return estate_text[found:end_index]


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


def chunk_text(text, chunk_size=TYPO_CHUNK_SIZE):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            last_newline = text.rfind("\n", start, end)
            if last_newline > start:
                end = last_newline
        chunks.append(text[start:end].strip())
        start = end
    return chunks


def split_estate_by_sections(estate_text):
    result = []
    for i, section_name in enumerate(TYPO_SECTIONS):
        start_index = estate_text.find(section_name)
        if start_index == -1:
            continue

        if i + 1 < len(TYPO_SECTIONS):
            next_section = TYPO_SECTIONS[i + 1]
            end_index = estate_text.find(next_section, start_index + len(section_name))
            if end_index == -1:
                end_index = len(estate_text)
        else:
            end_index = len(estate_text)

        section_text = estate_text[start_index:end_index].strip()
        result.append((section_name, section_text))

    if not result:
        chunks = chunk_text(estate_text)
        result = [(f"Part {i+1}", chunk) for i, chunk in enumerate(chunks)]

    return result


def build_client_details_prompt(intake_text, estate_text):
    estate_excerpt = "\n\n".join([
        extract_estate_section(
            estate_text,
            "THIS TRUST AGREEMENT",
            ["ARTICLE I"]
        ),
        extract_estate_section(
            estate_text,
            "LAST WILL AND TESTAMENT",
            ["Article I", "ARTICLE I"]
        )
    ])

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
            "ARTICLE XI",
            ["ARTICLE XII"]
        ),
        extract_estate_section(
            estate_text,
            "Article VII",
            ["[The remainder of this page is intentionally left blank"]
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
- Names must match exactly, word for word.
- Compare the full fiduciary name from the Intake Form against the full fiduciary name in the Estate Plan.
- Do not treat a partial name match as a match.
- Do not ignore extra words in a person's name.
- Do not ignore missing words in a person's name.
- Do not treat a name as matching if the Estate Plan adds or removes any first name, middle name, last name, prefix, suffix, or any other word.
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
- Output only the Fiduciary Review.

INTAKE FORM:
{intake_text}

ESTATE PLAN EXCERPTS:
{estate_excerpt}
"""


def build_distribution_prompt(intake_text, estate_text):
    estate_excerpt = extract_estate_section_nth(
        estate_text,
        "ARTICLE VI - DISTRIBUTION OF TRUST REMAINDER UPON DEATH OF THE SETTLOR",
        ["ARTICLE VII"],
        occurrence=2
    )

    return f"""
You are Aegis Review.

Compare ONLY distribution beneficiaries and percentages from the Intake Form against the Estate Plan excerpt.

The Intake Form is the source of truth.

Important rules for distribution matching:
- Compare beneficiary names and percentages exactly.
- A beneficiary is not missing if the Estate Plan lists the beneficiary followed by a percentage.
- Recognize distribution lines even if they are written with a colon, bullet point, dash, or plain text.
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


def build_typos_prompt_chunk(section_name, section_text):
    return f"""
You are Aegis Review.

Review ONLY the Estate Plan section below for typographical and drafting cleanup issues.

Section: {section_name}

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

### {section_name} — Typographical and Drafting Cleanup

| Issue | Where | Current Wording | Suggested Correction |
|---|---|---|---|

Rules:
- Quote the current wording when possible.
- If no issues are found, write: No issues found in this section.
- Output only the table for this section.

ESTATE PLAN SECTION TEXT:
{section_text}
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
    sections.append(call_claude(build_client_details_prompt(intake_text, estate_text)))

    print("Running Fiduciary Review...")
    sections.append(call_claude(build_fiduciary_prompt(intake_text, estate_text)))

    print("Running Distribution Review...")
    sections.append(call_claude(build_distribution_prompt(intake_text, estate_text)))

    print("Running Real Estate / Deed Review...")
    sections.append(call_claude(build_real_estate_prompt(intake_text, estate_text)))

    print("Running Typographical and Drafting Cleanup Review (chunked by section)...")
    typo_parts = []
    estate_sections = split_estate_by_sections(estate_text)

    for section_name, section_text in estate_sections:
        if len(section_text) > TYPO_CHUNK_SIZE:
            sub_chunks = chunk_text(section_text, TYPO_CHUNK_SIZE)
            for i, chunk in enumerate(sub_chunks):
                label = f"{section_name} (Part {i+1})"
                print(f"  Reviewing typos: {label}...")
                typo_parts.append(call_claude(build_typos_prompt_chunk(label, chunk)))
        else:
            print(f"  Reviewing typos: {section_name}...")
            typo_parts.append(call_claude(build_typos_prompt_chunk(section_name, section_text)))

    sections.append("## Typographical and Drafting Cleanup\n\n" + "\n\n".join(typo_parts))

    final_report = "# Aegis Review Sectional Report\n\n"
    final_report += "This report compares the Intake Form against the Estate Plan Draft by section.\n\n"
    final_report += "\n\n---\n\n".join(sections)

    os.makedirs("output", exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(final_report)

    print(f"\nDone. Report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
