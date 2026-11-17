# Dataiku Python recipe: verify_agent_answers   (Milestone 9: check AI answers against the data)
# Input : agent_decision_cards   (agent_cases + the specialist answer + the coordinator card)
# Output: agent_checks           (one row per case per AI-written column, with PASS / REVIEW)
# Rules: every number in an AI answer must appear in that case's facts / suggestion / task; no forbidden advice;
# coordinator cards must contain the four required lines. The LLM never creates numbers that reach the dashboard unchecked.
import re
import dataiku
import pandas as pd

BASE = ["case_id", "case_type", "route", "role", "task", "facts", "rule_action"]
FORBIDDEN = ["fare increase", "raise fares", "increase fares", "fare hike", "surge pricing", "dedicated lane", "bus lane",
             "new depot", "cut frequency", "reduce frequency", "cancel trips", "reduce trips", "cut trips", "skip rest"]
REQUIRED_LINES = ["CHANGE:", "WHY:", "MEASURABLE:", "GUARDRAIL CHECK:"]
FIXED_RULE_NUMBERS = {5.0, 30.0}   # numbers stated in the fixed rules (5 minutes late, 30 percent)

df = dataiku.Dataset("agent_decision_cards").get_dataframe()


def numbers(text):
    t = re.sub(r"(?<=\d),(?=\d{3})", "", str(text))
    return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)}


PREFERRED = ["specialist_view", "llm_output"]            # the two AI-written columns of the pipeline
LABELS = {"specialist_view": "specialist", "llm_output": "coordinator_card"}


def looks_like_answer(col):
    if col in BASE or re.search(r"error|raw|validation|query", col, re.I):
        return False
    s = df[col].dropna().astype(str)
    s = s[s.str.strip() != ""]          # rows where the model failed (empty) must not hide the column
    return len(s) > 0 and s.str.len().mean() >= 40 and s.str.contains(" ").mean() > 0.8


answer_cols = [c for c in PREFERRED if c in df.columns]
if not answer_cols:                                      # fallback: any prose column except raw / error / validation columns
    answer_cols = [c for c in df.columns if looks_like_answer(c)]
rows = []
for _, r in df.iterrows():
    allowed = numbers(r["facts"]) | numbers(r["rule_action"]) | numbers(r["task"]) | FIXED_RULE_NUMBERS
    for col in answer_cols:
        text = "" if pd.isna(r[col]) else str(r[col]).strip()
        bad_nums = sorted(n for n in numbers(text) if n not in allowed)
        low = text.lower()
        bad_terms = [t for t in FORBIDDEN if t in low]
        is_card = "CHANGE:" in text.upper() or "GUARDRAIL CHECK" in text.upper()
        fmt_ok = (all(k in text.upper() for k in REQUIRED_LINES) if is_card
                  else len(re.findall(r"[.!?](?:\s|$)", text)) <= 5)
        status = "PASS" if (text and not bad_nums and not bad_terms and fmt_ok) else "REVIEW"
        rows.append({"case_id": r["case_id"], "case_type": r["case_type"], "route": r["route"], "ai_column": LABELS.get(col, col),
                     "answer": text, "unsupported_numbers": ", ".join(f"{n:g}" for n in bad_nums),
                     "forbidden_terms": ", ".join(bad_terms), "format_ok": bool(fmt_ok), "status": status})

out = pd.DataFrame(rows, columns=["case_id", "case_type", "route", "ai_column", "answer", "unsupported_numbers",
                                  "forbidden_terms", "format_ok", "status"])
dataiku.Dataset("agent_checks").write_with_schema(out)
