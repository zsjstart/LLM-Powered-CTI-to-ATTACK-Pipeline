import json
import argparse
from multi_llm import call_llm
import google.generativeai as genai
import re
import json
from json_repair import repair_json
import time

def extract_and_fix_json(text):
    # Extract JSON block
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON found in text")
    
    json_str = text[start:end]
    json_str = json_str.strip().replace("```json", "").replace("```", "").strip()
    
    # Fix 1: escaped underscores  "origin\_AS" -> "origin_AS"
    json_str = re.sub(r'\\\_', '_', json_str)
    return json_str


def build_eval_prompt(sample):
    return f"""
You are a cybersecurity analyst evaluating MITRE ATT&CK mappings.

Behavior:
{sample["behavior"]}

Ground Truth:
{sample["ground_truth"]}

Model Prediction:
{sample["prediction"]}

Model Reasoning:
{sample["reasoning"]}

Task:
Determine whether the prediction should still be considered:
- "reasonable" → prediction is directly supported by the behavior text and semantically aligns with the behavior
- "incorrect" → prediction is unsupported, weakly related, overly inferred, or semantically mismatched

Guidelines:
- ATT&CK mappings are often ambiguous
- Multiple techniques may reasonably apply
- Different abstraction levels (parent vs sub-technique) may both be acceptable
- Consider the model reasoning when evaluating the prediction
- Focus on whether the prediction is grounded in the explicit behavior text
- Do NOT accept predictions based only on inferred intent, objectives, or unstated actions
- Minor abstraction differences alone should not make a prediction incorrect

Output JSON ONLY:

{{
  "verdict": "reasonable | incorrect",
  "reason": "<short explanation under 30 words>",
  "suggested": ["TXXXX"]
}}
"""


def load_results(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def parse_eval_response(response): 
    try:
        response = extract_and_fix_json(response)
        data = json.loads(response)

        return {
            "verdict": data.get("verdict", "unknown"),
            "reason": data.get("reason", "")
        }

    except Exception:

        return {
            "verdict": "parse_error",
            "reason": response
        }


def call_gemini(prompt, model_name, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    response = model.generate_content(prompt)

    return response.text

def main():

    parser = argparse.ArgumentParser(
        description="LLM evaluator for ATT&CK mismatch cases"
    )

    parser.add_argument("--model", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True, help = "Output a json file")
    parser.add_argument("--base_url",
                        default="http://localhost:8000")
    parser.add_argument("--api_key", type=str, default=None)
    parser.add_argument("--temper", type=float, default=0.0)

    args = parser.parse_args()
    
    output_file = args.output
    if not(output_file.endswith(".json")):
        raise ValueError(
            "args.output suffix only allowed to be '.json'"
        )


    data = load_results(args.input)

    mismatch_cases = []

    reasonable_count = 0
    incorrect_count = 0

    for i, sample in enumerate(data):

        # ONLY evaluate mismatch cases
        if sample["evaluation"] != "mismatch" or sample['prediction'] == ["Needs Review"]:
            continue
        
        print(f"\n===== Mismatch Sample {i+1} =====")
        print(f"Behavior: {sample['behavior']}")
        print(f"Ground Truth: {sample['ground_truth']}")
        print(f"Prediction: {sample['prediction']}")
        print(f"Reasoning: {sample['reasoning']}")

        prompt = build_eval_prompt(sample)
        
        if "gemini" in args.model:
            response = call_gemini(
                    prompt,
                    args.model,
                    args.api_key
                )
        else:
            response = call_llm(
                prompt,
                model=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                temperature=args.temper
            )

        print("\nLLM Evaluator Response:")
        print(response)

        parsed = parse_eval_response(response)

        sample["llm_verdict"] = parsed["verdict"]
        sample["llm_reason"] = parsed["reason"]

        if parsed["verdict"] == "reasonable":
            reasonable_count += 1
        else:
            incorrect_count += 1

        mismatch_cases.append(sample)

    

    save_results(mismatch_cases, output_file)

    print("\n===== Summary =====")
    print(f"Mismatch cases evaluated: {len(mismatch_cases)}")
    print(f"Reasonable: {reasonable_count}")
    print(f"Incorrect: {incorrect_count}")

    print(f"\nSaved results to: {output_file}")


if __name__ == "__main__":
    main()
