import os
import re
import json
import requests

NUM_FILES = 14
NUM_ATTEMPTS = 2
OUTPUT_DIR = " "
BASELINE_DIR = " "  
INPUT_DIR = " "

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# RCI Step 1: Review the previously generated diagram
# ---------------------------------------------------------
RCI_REVIEW_TEMPLATE = """ """


# ---------------------------------------------------------
# RCI Step 2: Improve the diagram based on the review
# ---------------------------------------------------------
RCI_IMPROVE_TEMPLATE = """ """

def build_prompt_wrapper(filled_prompt: str) -> str:
    return f"<｜User｜>\n{filled_prompt}\n<｜Assistant｜>"

def call_llm(prompt_text: str) -> str:
    try:
        response = requests.post(
            "http://localhost:1234/v1/completions",
            json={
                "model": "deepseek-r1-distill-llama-8b",
                "prompt": prompt_text,
                "temperature": 0.1,
                "top_p": 1.0,
                "top_k": 0,
                "repeat_penalty": 1.0,
                "seed": 42,
                "max_tokens": 4096,
                "stream": False
            },
            timeout=600
        )
        response.raise_for_status()
        return response.json()["choices"][0]["text"]
    except Exception as e:
        return f"ERROR: {e}"

def strip_think_tags(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def format_llm_response(text):
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        raw_json_str = json_match.group(0)
        try:
            parsed_json = json.loads(raw_json_str)
            pretty_json_str = json.dumps(parsed_json, ensure_ascii=False, indent=2)
            return text[:json_match.start()] + pretty_json_str + text[json_match.end():]
        except json.JSONDecodeError:
            pass
    return text

def extract_json_only(text):
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            return json_match.group(0)
    return text

# ---------------------------------------------------------
# Main Loop: load previous baseline → RCI review → RCI improve
# ---------------------------------------------------------
for i in range(1, NUM_FILES + 1):
    file_name = f"ex{i}.java"
    file_path = os.path.join(INPUT_DIR, file_name)
    example_name = f"java_example_{i}"

    if not os.path.exists(file_path):
        print(f"⚠️  File {file_name} not found! Skipping...")
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    print(f"\n==========================================")
    print(f"Processing file: {file_name}")
    print(f"==========================================")

    for attempt in range(1, NUM_ATTEMPTS + 1):
        print(f"[{example_name}] Attempt {attempt}/{NUM_ATTEMPTS}")

        # ---- Load previously generated baseline JSON ----
        baseline_filename = f"{example_name}_attempt_{attempt}.json"
        baseline_path = os.path.join(BASELINE_DIR, baseline_filename)

        if not os.path.exists(baseline_path):
            print(f"  ⚠️  Baseline file not found: {baseline_path} — Skipping...")
            continue

        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_raw = f.read()

        baseline_json = extract_json_only(baseline_raw)
        print(f"  → Loaded baseline: {baseline_filename}")

        # ---- Step 1: RCI review ----
        review_prompt = RCI_REVIEW_TEMPLATE.format(
            code_content=code_content,
            previous_json=baseline_json
        )
        review_final = build_prompt_wrapper(review_prompt)

        print("Step 1: RCI review...")
        review_response_raw = call_llm(review_final)
        review_response = strip_think_tags(review_response_raw)

        review_filename = f"{example_name}_attempt_{attempt}_step1_review.txt"
        with open(os.path.join(OUTPUT_DIR, review_filename), "w", encoding="utf-8") as f:
            f.write(review_response.strip())

        # ---- Step 2: RCI improve ----
        improve_prompt = RCI_IMPROVE_TEMPLATE.format(
            review_response=review_response,
            previous_json=baseline_json
        )
        improve_final = build_prompt_wrapper(improve_prompt)

        print("Step 2: RCI improve...")
        improve_response = call_llm(improve_final)

        formatted_output = format_llm_response(improve_response)
        output_filename = f"{example_name}_attempt_{attempt}.json"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(formatted_output.strip())

        print(f"Saved final (RCI-improved) JSON: {output_path}")

print("\nAll files processed (RCI using previous baseline results).")
