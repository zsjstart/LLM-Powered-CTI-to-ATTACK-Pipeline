# LLM-Powered CTI-to-ATT&CK Pipeline

A lightweight multi-stage pipeline for extracting adversary behaviors from Cyber Threat Intelligence (CTI) reports and mapping them to MITRE ATT&CK techniques using Large Language Models (LLMs).

## Overview

As part of their daily work, Cyber Threat Intelligence (CTI) analysts read threat reports, identify adversary behaviors, and map them to MITRE ATT&CK techniques. This process is often manual, time-consuming, and semantically challenging due to the large amount of narrative and contextual information contained in CTI reports.

This project is motivated by leveraging Large Language Models (LLMs) to develop an automated CTI-to-ATT&CK pipeline that:

* extracts adversary behaviors from raw CTI reports,
* refines operational intrusion behaviors,
* reduces semantic noise,
* maps behaviors to MITRE ATT&CK techniques using reasoning-driven prompts.

The framework uses:

* prompt engineering only,
* no supervised fine-tuning,
* no retrieval-augmented generation (RAG),
* no external knowledge base.

---

## Pipeline

```text
CTI Report
   ↓
Paragraph Splitting
   ↓
Behavior Extraction
   ↓
Behavior Refinement
   ↓
MITRE ATT&CK Mapping
```

---

## Pipeline Stages

### 1. Paragraph Splitting

Raw CTI reports are divided into paragraph-level units to:

* reduce context complexity,
* improve extraction quality,
* stabilize LLMs,
* support localized semantic refinement.

---

### 2. Behavior Extraction

The LLM extracts explicit adversary behaviors from CTI paragraphs.

---

### 3. Behavior Refinement

The extracted behaviors are refined per paragraph to:

* remove attribution and narrative statements,
* filter vague or non-operational behaviors,
* reduce strategic or contextual noise,
* preserve ATT&CK-relevant operational semantics,
* remove duplicates


#### Example: Paragraph-Level Refinement

Input CTI paragraph:

```text id="n1r7uo"
APT39 was created to bring together previous activities and methods used by this actor, and its activities largely align with a group publicly referred to as "Chafer." However, there are differences in what has been publicly reported due to the variances in how organizations track activity. APT39 primarily leverages the SEAWEED and CACHEMONEY backdoors along with a specific variant of the POWBAT backdoor. While APT39's targeting scope is global, its activities are concentrated in the Middle East. APT39 has prioritized the telecommunications sector, with additional targeting of the travel industry and IT firms that support it and the high-tech industry.
```

Initially extracted behaviors:

```text id="h3q2xp"
- APT39 primarily leverages the SEAWEED and CACHEMONEY backdoors along with a specific variant of the POWBAT backdoor
- APT39 has prioritized the telecommunications sector, with additional targeting of the travel industry and IT firms that support it and the high-tech industry
- While APT39's targeting scope is global, its activities are concentrated in the Middle East
```

Refined ATT&CK-oriented behaviors:

```text id="z6m4lk"
- APT39 primarily leverages the SEAWEED and CACHEMONEY backdoors along with a specific variant of the POWBAT backdoor
```

This example illustrates how the refinement stage removes targeting information, geopolitical context, and narrative CTI content while preserving operationally meaningful ATT&CK-relevant adversary behaviors.

---

### 5. MITRE ATT&CK Mapping

The refined adversary behaviors are mapped to MITRE ATT&CK techniques using reasoning-oriented prompts.

The ATT&CK mapping component is based on my previous project:

**LLM-Powered ATT&CK Mapping**  
https://github.com/zsjstart/LLM-Powered-ATTACK-Mapping

Unlike strict classification approaches, the framework supports:

* multiple reasonable mappings,
* parent/sub-technique ambiguity,
* implementation-level interpretations,
* analyst-style reasoning.

Example:

Input behavior:

```text
can search for anti-virus products on the system
```

Output:

```json
{
  "technique": [
    "T1518.001"
  ],
  "reasoning": "Searching for anti-virus products matches Security Software Discovery, a sub-technique of Software Discovery."
}
```

---

## Preliminary Results

We leverage `gpt-oss-120b` to evaluate the proposed CTI-to-ATT&CK pipeline.

The behavior extraction and refinement stages exhibit strong and stable performance on raw CTI reports. Given a CTI report, the framework can identify a highly ATT&CK-oriented behavior set that is:

* operationally meaningful,
* technically concrete,
* semantically consistent,
* strongly ATT&CK-relevant.

For example, given the CTI report:

```text id="8lw1ca"
/Data/CTI_report_01.pdf
```

the framework extracts 17 adversary behaviors covering all behaviors manually identified by domain experts.

The remaining differences mainly arise because human experts typically prioritize highly concrete operational intrusion procedures, while LLMs may additionally retain broader adversary operations or higher-level ATT&CK-relevant behaviors.

These observations suggest that multi-stage LLM-based behavior extraction can effectively isolate operational adversary procedures from noisy CTI narratives before downstream ATT&CK mapping.

Performance evaluation of CTI-behavior-to-ATT&CK mapping is presented in the previous project:

LLM-Powered ATT&CK Mapping
https://github.com/zsjstart/LLM-Powered-ATTACK-Mapping

---

## Repository Structure

```text
LLM-Powered-CTI-ATTACK-Pipeline/
├── README.md
├── requirements.txt
├── Data/
|   ├── CTI_report_01.pdf
|   ├── CTI_report_01_expert_labeled.pdf
│   └── MITRE_CTI_Data.csv
├── Scripts/
|   ├── llm_extract_behaviors.py
│   ├── llm_mapping.py
│   └── llm_mismatch_eva.py
```

---

## Installation

```bash
git clone https://github.com/zsjstart/LLM-Powered-CTI-ATTACK-Pipeline.git
cd LLM-Powered-CTI-ATTACK-Pipeline
pip install -r requirements.txt
```

---

## Running

### Behavior Extraction

```bash
python3 llm_extract_behaviors.py \
--model openai/gpt-oss-120b \
--temper 0.1  \
--input ../Data/CTI_report_01.pdf \
--output ../results/behaviors.json
```

### ATT&CK Mapping

```bash
python3 mapping/llm_mapping.py \
    --model openai/gpt-oss-120b \
    --temper 0.3 \
    --input Data/MITRE_CTI_Data.csv \
    --limit 10 \
    --output results/llm_mapping.json
```

---

## Key Insights

* CTI reports contain substantial narrative and contextual noise that can negatively affect direct ATT&CK mapping.

* Multi-stage behavior extraction and refinement can improve operational semantic quality before ATT&CK mapping.

---

## Current Focus

This project currently explores:

* CTI behavior extraction,
* ATT&CK-oriented semantic refinement,
* reasoning-driven ATT&CK mapping,
* operational cybersecurity semantics,
* multi-stage LLM pipelines for cybersecurity automation.

---

## Limitations
* Inability to extract graph-based CTI behaviors
* Performance may vary depending on:

  * CTI writing style,
  * paragraph structure,
  * model capability,
  * prompt configuration.

---

## License

MIT License
