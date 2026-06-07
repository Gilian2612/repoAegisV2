import os
import requests

MODEL = "qwen3:14b"

PROMPT_PATH = os.path.join("output", "aegis_prompt_ready.txt")
REPORT_PATH = os.path.join("output", "aegis_report.md")

def read_prompt(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

def run_ollama(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt + "\n\nDo not include private reasoning. Output only the final Aegis Review Report.",
            "stream": False,
            "options": {
                "temperature": 0.0, 
		"num_ctx":32768
            }
        },
        timeout=1200
    )

    response.raise_for_status()
    return response.json()["response"]

if __name__ == "__main__":
    if not os.path.exists(PROMPT_PATH):
        print(f"ERROR: Missing file: {PROMPT_PATH}")
        print("Run: python extract_docx_text.py")
        print("Then run: python build_prompt.py")
        exit()

    print("Reading Aegis prompt...")
    prompt = read_prompt(PROMPT_PATH)

    print(f"Running local Aegis Review with Ollama model: {MODEL}")
    report = run_ollama(prompt)

    os.makedirs("output", exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Done. Report saved to: {REPORT_PATH}")
