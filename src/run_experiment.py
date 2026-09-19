import os
import re
import json
import requests

# ---------------------------------------------------------
# Configurations
# ---------------------------------------------------------
NUM_FILES = 14         # Number of files (ex1.py to ex16.py)
NUM_ATTEMPTS = 5        # Attempts per file
OUTPUT_DIR = ""  # Directory to save JSON results
INPUT_DIR = ""      # Directory containing ex1.py to ex16.py

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Prompt template with placeholder {code_content}
PROMPT_TEMPLATE = ""

def build_final_prompt(code_content: str) -> str:
    filled = PROMPT_TEMPLATE.replace("{code_content}", code_content)
    return f"<\uff5cUser\uff5c>\n{filled}\n<\uff5cAssistant\uff5c>"

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

# Main Loop

for i in range(1, NUM_FILES + 1):
    file_name = f"ex{i}.java"
    # file_name = f"ex{i}.py"
    file_path = os.path.join(INPUT_DIR, file_name)
    example_name = f"java_example_{i}"
    # example_name = f"python_example_{i}"

    if not os.path.exists(file_path):
        print(f"⚠️  File {file_name} not found in '{INPUT_DIR}' directory! Skipping...")
        continue

    # Read code content from file
    with open(file_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    # Format the prompt with the file's code content
    current_prompt = build_final_prompt(code_content)

    print(f"\n==========================================")
    print(f"Processing file: {file_name}")
    print(f"==========================================")

    # Run attempts for the current file
    for attempt in range(1, NUM_ATTEMPTS + 1):
        print(f"[{example_name}] Running attempt {attempt}/{NUM_ATTEMPTS} ...")

        try:
            response = requests.post(
                "http://localhost:1234/v1/completions",
                json={
                    "model": "deepseek-r1-distill-llama-8b",
                    "prompt": current_prompt,
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
            result_text = response.json()["choices"][0]["text"]

        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            result_text = f"ERROR: {e}"

        formatted_output = format_llm_response(result_text)
        output_filename = f"{example_name}_attempt_{attempt}.json"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(formatted_output.strip())

        print(f"Saved to: {output_path}")

print("\nAll files processed and outputs saved successfully.")
