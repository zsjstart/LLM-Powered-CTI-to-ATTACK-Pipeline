import csv
import json
import re
import argparse
from multi_llm import call_llm
from json_repair import repair_json


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


def build_prompt(behavior):
    return f"""
You are a cybersecurity analyst familiar with MITRE ATT&CK.

Task:
Map the given behavior to the most relevant MITRE ATT&CK technique.

Behavior:
{behavior}

Instructions:
- Identify:
  1) behavior (what is done)
  2) implementation (how it is done)
- Put behavior-level technique FIRST
- Add implementation-level only if it adds value
- Prefer the most specific sub-technique if clearly supported
- If vague → use parent technique
- If multiple interpretations exist → include all valid techniques
- Do NOT include both parent and sub-technique unless they represent different interpretations
- Keep reasoning under 20-30 words


Output JSON:
{{
  "technique": ["TXXXX", "TXXXX.XXX"],
  "reasoning": "<short explanation>"
}}

Rules:
Respond ONLY with valid JSON
Do not include markdown
Do not add extra text

"""


def read_data(file_path, text_column="text", label_column="label", limit=None):
    data = []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            behavior = row[text_column].strip()
            label = row[label_column].strip()

            data.append((behavior, label))

            if limit and i + 1 >= limit:
                break

    return data


def parse_response(output):
    """
    Parse LLM response into:
    {
        "technique": [...],
        "confidence": ...,
        "reasoning": ...
    }
    """

    result = {
        "technique": [],
        "confidence": None,
        "reasoning": ""
    }

    if not output:
        return result

    # Try JSON parsing
    try:
        output = extract_and_fix_json(output)
        data = json.loads(output)

        techniques = data.get("technique", [])
        if isinstance(techniques, list):
            result["technique"] = list(dict.fromkeys(techniques))

        result["confidence"] = data.get("confidence")
        result["reasoning"] = data.get("reasoning", "")

        return result

    except Exception:
        pass
    '''
    # Fallback extraction
    matches = re.findall(r"T\d{4}(?:\.\d{3})?", output)
    result["technique"] = list(dict.fromkeys(matches))
    '''

    return result


def evaluate_pred_list(pred_list, gt):
    if not pred_list or not gt:
        return "mismatch"

    # Exact hit
    if gt in pred_list:
        if len(pred_list) == 1:
            return "exact"
        else:
            return "multi_hit"

    gt_parent = gt.split(".")[0]

    for p in pred_list:
        if p.split(".")[0] == gt_parent:
            return "partial"

    return "mismatch"


def save_results_json(results, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def save_results_csv(results, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "behavior",
            "ground_truth",
            "prediction",
            "confidence",
            "reasoning",
            "evaluation"
        ])

        for r in results:
            writer.writerow([
                r["behavior"],
                r["ground_truth"],
                ";".join(r["prediction"]),
                r["confidence"],
                r["reasoning"],
                r["evaluation"]
            ])


def main():
    parser = argparse.ArgumentParser(
        description="MITRE ATT&CK mapping with LLM"
    )

    parser.add_argument("--model", required=True)
    parser.add_argument("--temper", type=float, default=0.3)
    parser.add_argument("--base_url", type=str,
                        default="http://localhost:8000")
    parser.add_argument("--api_key", type=str, default=None)
    parser.add_argument("--input", type = str, default="../Data/train_set.csv")
    parser.add_argument("--output", type = str, default="../results/llm_mapping_out.json")
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    model_name = args.model
    temperature = args.temper
    base_url = args.base_url
    api_key = args.api_key
    
    if not (args.output.endswith(".json")):
        raise ValueError(
            "args.output suffix only allowed to be '.json'"
        )

    data = read_data(
        args.input,
        text_column="text",
        label_column="label",
        limit=args.limit
    )

    correct = 0
    results = []

    for i, (behavior, label) in enumerate(data):

        prompt = build_prompt(behavior)

        print(f"\n===== Sample {i+1} =====")
        print(f"Behavior: {behavior}")
        print(f"Ground Truth: {label}")
        
        if "gemini" in model_name:
            response = call_gemini(
                    prompt,
                    model_name,
                    api_key
                )
        else:
            response = call_llm(
                prompt,
                model=model_name,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature
            )

        print(f"Response: {response}")

        parsed = parse_response(response)
        
        if parsed.get("technique") == []:
            parsed = {
                        "technique": ["Needs Review"],
                        "confidence": 0.0,
                        "reasoning": "insufficient evidence"
                      }
            

        prediction = parsed["technique"]
        confidence = parsed["confidence"]
        reasoning = parsed["reasoning"]
        
        print(f"LLM Output: {prediction}")

        res = evaluate_pred_list(prediction, label)

        print(f"Evaluation: {res}")

        if res != "mismatch":
            correct += 1

        results.append({
            "behavior": behavior,
            "ground_truth": label,
            "prediction": prediction,
            "confidence": confidence,
            "reasoning": reasoning,
            "evaluation": res
        })

    total = len(data)
    accuracy = correct / total if total > 0 else 0

    print("\n===== Summary =====")
    print(f"Model: {model_name}")
    print(f"Samples: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.2%}")
    
    save_results_json(results, args.output)

    #json_file = f"results_{model_name}.json"
    #csv_file = f"results_{model_name}.csv"

        



if __name__ == "__main__":
    main()
