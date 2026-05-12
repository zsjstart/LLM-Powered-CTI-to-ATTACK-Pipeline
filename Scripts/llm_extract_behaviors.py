import json
import re
import argparse
from multi_llm import call_llm
from pypdf import PdfReader
import textract


def build_dedup_prompt(behaviors):
    return f"""
You are a cybersecurity threat intelligence analyst.

Task:
Remove redundant CTI behaviors.

Input Behaviors:
{behaviors}

Instructions:
- Remove duplicate or highly similar behaviors
- If multiple behaviors describe the same attacker activity:
  - keep the most complete
  - keep the most operationally meaningful
  - keep the behavior with the strongest technical detail
- Preserve distinct attacker activities
- Preserve the original CTI wording whenever possible
- Do NOT add new information
- Do NOT merge unrelated behaviors

Output JSON:
{{
  "behaviors": [
    "behavior 1",
    "behavior 2"
  ]
}}

Rules:
- Output ONLY JSON
"""

def build_refinement_prompt(behaviors):
    return f"""
You are a cybersecurity threat intelligence analyst.

Task:
Keep only concrete cyber intrusion behaviors.

Input Behaviors:
{behaviors}

Instructions:
- Keep ONLY behaviors that describe concrete attacker techniques or intrusion activity
- Keep behaviors related to:
  - exploitation
  - malware execution
  - credential theft
  - persistence
  - privilege escalation
  - reconnaissance
  - lateral movement
  - command and control
  - tunneling or proxying
  - internal data collection and exfiltration
  - defense evasion
  
- Remove:
  - high-level goals, intentions, or strategic/future objective
  - intelligence or surveillance goals
  - targeting information
  - statements about the threat actor rather than attacker activity
  - political or regional analysis
  - generic malware or capability descriptions
  - narrative statements
  
 
- If multiple behaviors are similar:
  - keep the most complete and operationally meaningful behavior
- Preserve the original CTI wording whenever possible
- Preserve technical details
- Do NOT add unrelated information
- Remove duplicates

Output JSON:
{{
  "behaviors": [
    "behavior 1",
    "behavior 2"
  ]
}}

Rules:
- Output ONLY JSON
"""



def build_initial_prompt(paragraph):
    return f"""
You are a cybersecurity threat intelligence analyst.

Task:
Extract explicit adversary behavior statements from the CTI paragraph.

CTI Paragraph:
{paragraph}

Instructions:
- Extract ONLY explicit attacker behaviors suitable for ATT&CK mapping
- Preserve the ORIGINAL wording from the CTI report whenever possible
- Do NOT paraphrase or summarize
- Focus on attacker actions, capabilities, or procedures
- Extract behavior-bearing sentences or clauses
- Ignore attribution, malware family names, analyst opinions, and background information
- Exclude campaign descriptions or summaries of threat actor activity
- Ignore vague or generic statements
- Remove duplicates
- Do NOT infer unstated behaviors
- If no attacker behaviors exist, return an empty list

Good examples:
- uses PowerShell to download payloads
- creates scheduled tasks for persistence
- injects shellcode into explorer.exe
- enumerates installed antivirus products

Output JSON:
{{
  "behaviors": [
    "behavior 1",
    "behavior 2"
  ]
}}

Rules:
- Output ONLY JSON
"""

def parse_response(output):
    """
    Parse LLM response into:
    {
        "behaviors": [...]
    }
    """

    result = {
        "behaviors": []
    }

    if not output:
        return result

    try:
        data = json.loads(output)

        behaviors = data.get("behaviors", [])

        if isinstance(behaviors, list):

            cleaned = []

            for b in behaviors:

                if not isinstance(b, str):
                    continue

                b = b.strip()

                if len(b) < 3:
                    continue

                cleaned.append(b)

            result["behaviors"] = list(dict.fromkeys(cleaned))

        return result

    except Exception:
        pass

    return result


def deduplicate_behaviors(behaviors):
    """
    Global deduplication.
    """

    seen = set()

    unique = []

    for b in behaviors:

        key = b.lower().strip()

        if key not in seen:
            seen.add(key)
            unique.append(b)

    return unique


def deduplicate_behaviors_llm(behaviors, model_name,
        base_url,
        api_key,
        temperature):
    prompt = build_dedup_prompt(behaviors)
    response = call_llm(
            prompt,
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature
    )
    print("\nLLM Response:")
    print(response)
    parsed = parse_response(response)
    behaviors = parsed["behaviors"]
    print("\n Final Behaviors:", behaviors)


    return behaviors

def refine_behaviors(behaviors, model_name,
        base_url,
        api_key,
        temperature):
    prompt = build_refinement_prompt(behaviors)
    response = call_llm(
            prompt,
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature
    )
    print("\nLLM Response:")
    print(response)
    parsed = parse_response(response)
    behaviors = parsed["behaviors"]
    print("\n Refined Behaviors:", behaviors)


    return behaviors


def extract_behaviors(
    report_text,
    model_name,
    base_url,
    api_key,
    temperature
):

    paragraphs = split_paragraphs(report_text)

    #print(f"[+] Total paragraphs: {len(paragraphs)}")
    #for i, p in enumerate(paragraphs):
        #print(i, p)

    all_behaviors = []

    for i, paragraph in enumerate(paragraphs):

        print(f"\n===== Paragraph {i+1} =====")

        print(paragraph)

        prompt = build_initial_prompt(paragraph)

        response = call_llm(
            prompt,
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature
        )

        #print("\nLLM Initial Response:")
        #print(response)

        parsed = parse_response(response)

        behaviors = parsed["behaviors"]

        print("\nExtracted Behaviors:")

        for b in behaviors:
            print(f"- {b}")
        if len( behaviors) == 0:
            continue
        # refine behaviors
        behaviors = refine_behaviors(behaviors, 
        model_name,
        base_url,
        api_key,
        temperature)

        all_behaviors.extend(behaviors)
    #deduplicate behaviors
    all_behaviors = deduplicate_behaviors(all_behaviors) 
    #all_behaviors = deduplicate_behaviors(all_behaviors, model_name, base_url, api_key, temperature)
    return all_behaviors





def read_report(file_path):

    text = textract.process(
        file_path
    ).decode("utf-8", errors="ignore")

    return text



def split_paragraphs(text):

    # normalize line endings
    text = text.replace("\r\n", "\n")

    # remove excessive spaces/tabs
    text = re.sub(r'[ \t]+', ' ', text)

    # split on blank lines
    raw_paragraphs = re.split(r'\n\s*\n', text)

    paragraphs = []

    for p in raw_paragraphs:

        # remove PDF line-wrap artifacts
        p = re.sub(r'\n+', ' ', p)

        # normalize spaces again
        p = re.sub(r'[ \t]+', ' ', p)

        p = p.strip()

        # skip short/noisy chunks
        if len(p.split()) < 15 or p.istitle():
            continue

        paragraphs.append(p)

    return paragraphs


def save_results(behaviors, output_path):

    with open(output_path, "w", encoding="utf-8") as f:

        json.dump(
            {
                "behaviors": behaviors
            },
            f,
            indent=2,
            ensure_ascii=False
        )


def main():

    parser = argparse.ArgumentParser(
        description="CTI Behavior Extraction with LLM"
    )

    parser.add_argument("--model", required=True)

    parser.add_argument(
        "--temper",
        type=float,
        default=0.0
    )

    parser.add_argument(
        "--base_url",
        type=str,
        default="http://localhost:8000"
    )

    parser.add_argument(
        "--api_key",
        type=str,
        default=None
    )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="CTI report text file"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="behaviors.json"
    )

    args = parser.parse_args()

    report_text = read_report(args.input)

    behaviors = extract_behaviors(
        report_text=report_text,
        model_name=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        temperature=args.temper
    )
    
    
    print("\n===== Final Behaviors =====\n")

    for i, b in enumerate(behaviors, 1):
        print(f"{i}. {b}")

    save_results(behaviors, args.output)

    print(f"\n[+] Saved to: {args.output}")


if __name__ == "__main__":
    main()
