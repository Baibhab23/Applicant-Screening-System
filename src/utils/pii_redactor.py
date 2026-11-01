from __future__ import annotations

import re

# These patterns match identifiers that are never useful to the LLM for evaluation
# but are PII that should not leave the environment when using cloud providers.
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]")
_URL_RE = re.compile(r"https?://[^\s]+")


def redact_pii(text: str) -> str:
    """
    Replace email addresses, phone numbers, and URLs with placeholders.
    Call this before sending resume text to a cloud LLM provider (Groq, OpenAI).

    Names are not redacted automatically — name extraction requires an NER model
    that is not available here. The name is instead excluded from the candidate
    profile dict sent to evaluate_interview (see llm_client.py).

    Limitation: redaction is regex-based and will miss obfuscated or
    unconventionally formatted identifiers. It is a risk-reduction measure,
    not a complete anonymisation solution.
    """
    text = _EMAIL_RE.sub("[EMAIL]", text)
    text = _PHONE_RE.sub("[PHONE]", text)
    text = _URL_RE.sub("[URL]", text)
    return text
