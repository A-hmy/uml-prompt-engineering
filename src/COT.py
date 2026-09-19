import os
import re
import json
import requests

# ---------------------------------------------------------
# Configurations
# ---------------------------------------------------------
NUM_FILES = 16
NUM_ATTEMPTS = 2
OUTPUT_DIR = ""
INPUT_DIR = ""

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# Original baseline prompt (identical to your true baseline)
# ---------------------------------------------------------
BASE_PROMPT = """ """

# ---------------------------------------------------------
# Step 1: baseline prompt + CoT suffix (reasoning only, no JSON)
# ---------------------------------------------------------
COT_SUFFIX = """ """

# ---------------------------------------------------------
# Step 2: step-1 reasoning ONLY + same requirements as baseline
# ---------------------------------------------------------
STEP2_TEMPLATE = """ """

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

# ---------------------------------------------------------
# Main Loop
# ---------------------------------------------------------
for i in range(1, NUM_FILES + 1):
    file_name = f"ex{i}.py"
    file_path = os.path.join(INPUT_DIR, file_name)
    example_name = f"python_example_{i}"

    if not os.path.exists(file_path):
        print(f"⚠️  File {file_name} not found! Skipping...")
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    base_prompt_filled = BASE_PROMPT.format(code_content=code_content)

    print(f"\n==========================================")
    print(f"Processing file: {file_name}")
    print(f"==========================================")

    for attempt in range(1, NUM_ATTEMPTS + 1):
        print(f"[{example_name}] Attempt {attempt}/{NUM_ATTEMPTS}")

        # ---- Step 1: baseline prompt + CoT suffix ----
        step1_prompt = base_prompt_filled + COT_SUFFIX
        step1_final = build_prompt_wrapper(step1_prompt)

        print("Step 1: requesting reasoning...")
        step1_response_raw = call_llm(step1_final)
        step1_response = strip_think_tags(step1_response_raw)

        step1_filename = f"{example_name}_attempt_{attempt}_step1_reasoning.txt"
        with open(os.path.join(OUTPUT_DIR, step1_filename), "w", encoding="utf-8") as f:
            f.write(step1_response.strip())

        # ---- Step 2: step1 reasoning ONLY (no java code) + same requirements ----
        step2_prompt = STEP2_TEMPLATE.format(step1_response=step1_response)
        step2_final = build_prompt_wrapper(step2_prompt)

        print("Step 2: requesting final JSON...")
        step2_response = call_llm(step2_final)

        formatted_output = format_llm_response(step2_response)
        output_filename = f"{example_name}_attempt_{attempt}.json"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(formatted_output.strip())

        print(f"Saved: {output_path}")

print("\nAll files processed (pure 2-stage CoT, based on baseline prompt).")