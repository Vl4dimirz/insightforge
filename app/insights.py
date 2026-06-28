"""
The insights layer — where Data meets AI.

It takes the *profile* of a dataset (the structured summary from Phase 2/3, NOT
the raw rows) and asks Gemini to turn those numbers into a plain-language,
business-focused analysis. Sending the profile instead of the whole file keeps
it cheap, fast, and private.
"""

from app.ai import generate

PROMPT = """You are a senior data analyst. Below is a PROFILE of a dataset (summary statistics, not the raw rows).
Write a concise, business-focused analysis with these sections:
1. Overview - what this dataset appears to be about.
2. Key findings - notable patterns or standouts, grounded in the stats.
3. Data quality - missing values, duplicates, or anything to clean.
4. Recommended next steps - 3 concrete analyses or actions.
Be practical and tight. Never invent values that aren't supported by the profile.

DATASET PROFILE:
{digest}"""


def _digest(profile: dict) -> str:
    """Flatten the profile dict into a compact, readable block for the model."""
    lines = [
        f"Rows: {profile['rows']} | Columns: {profile['columns']} | Duplicate rows: {profile['duplicate_rows']}",
        "Columns:",
    ]
    for c in profile["column_profiles"]:
        line = f"- {c['name']} ({c['dtype']}): {c['nulls']} missing ({c['null_pct']}%), {c['unique']} unique"
        if c.get("numeric"):
            n = c["numeric"]
            line += f" | min={n['min']} max={n['max']} mean={n['mean']} median={n['median']} std={n['std']}"
        else:
            line += f" | sample={c['sample']}"
        lines.append(line)
    return "\n".join(lines)


def analyze_profile(profile: dict, question: str | None = None) -> str:
    """Send the profile to Gemini and return a narrative analysis."""
    prompt = PROMPT.format(digest=_digest(profile))
    if question:
        prompt += f"\n\nAlso answer this specific question about the data: {question}"
    return generate(prompt)
