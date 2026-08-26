"""
Groq AI Interview Mail Detector Service.
Calls official Groq Chat Completions API with temperature 0.
First determines if the email is a genuine recruitment/interview update (INTERVIEW_MAIL vs NOT_RELATED).
If NOT_RELATED -> Returns is_interview_mail=False.
If INTERVIEW_MAIL -> Extracts candidate_name, company, role, status, round, interview_date.
No confidence scores.
"""

import json
import logging
from typing import Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are an ATS recruitment email parser and classifier.
Your FIRST responsibility is to determine whether the email is a genuine recruitment/interview update (INTERVIEW_MAIL) or completely unrelated (NOT_RELATED like marketing, newsletter, billing, OTP, discount, spam, or general meetings).

If the email is NOT a recruitment/interview update, return is_interview_mail as false and leave all other string fields empty.
If the email IS a recruitment/interview update, return is_interview_mail as true and extract the structured fields.

Never invent missing information. Never include confidence scores or explanations. Return JSON only."""

USER_PROMPT_TEMPLATE = """Classify and extract recruitment details from the following email text.

Return ONLY a JSON object matching this schema:
{{
  "is_interview_mail": true or false,
  "candidate_name": "<Full Name or empty>",
  "company": "<Company Name or empty>",
  "role": "<Job Role / Title or empty>",
  "status": "<Submitted|Shortlisted|Round 1|Round 2|Technical|Manager|HR|Offer|Rejected|Hold or empty>",
  "round": "<e.g. Round 1, Round 2, Technical, HR, Manager, Offer, Shortlisted or empty>",
  "interview_date": "<YYYY-MM-DD or empty>",
  "resume_id_tag": "<e.g. RES101, RES-101, or empty if not mentioned>"
}}

Email Content:
{email_text}
"""


class GroqService:
    @classmethod
    async def extract_email_entities(cls, raw_email: str) -> dict[str, Any]:
        """
        Send raw extracted email text to Groq API with temperature 0.
        First determines if the email is INTERVIEW_MAIL or NOT_RELATED.
        """
        import re

        # Regex fallback for resume tag e.g. RES101, RES-101
        tag_match = re.search(r'\b(RES[-_]?\d+)\b', raw_email, re.IGNORECASE)
        fallback_tag = tag_match.group(1).upper() if tag_match else None

        api_key = settings.groq_api_key

        models_to_try = [
            settings.groq_model,
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b",
            "groq/compound",
        ]
        models_to_try = [m for i, m in enumerate(models_to_try) if m and m not in models_to_try[:i]]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        last_error = None

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT_TEMPLATE.format(email_text=raw_email)},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
                "max_tokens": 500,
            }

            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.post(GROQ_API_URL, headers=headers, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                        parsed = json.loads(content)

                        is_interview = bool(parsed.get("is_interview_mail", False))
                        if not is_interview:
                            return {
                                "is_interview_mail": False,
                                "candidate_name": "",
                                "company": "",
                                "role": "",
                                "status": "",
                                "round": "",
                                "interview_date": "",
                                "resume_id_tag": "",
                            }

                        extracted_tag = (parsed.get("resume_id_tag") or "").strip() or fallback_tag or ""

                        return {
                            "is_interview_mail": True,
                            "candidate_name": (parsed.get("candidate_name") or "").strip(),
                            "company": (parsed.get("company") or "").strip(),
                            "role": (parsed.get("role") or "").strip() or "Software Engineer",
                            "status": (parsed.get("status") or "Shortlisted").strip() or "Shortlisted",
                            "round": (parsed.get("round") or "Round 1").strip() or "Round 1",
                            "interview_date": (parsed.get("interview_date") or "").strip() or None,
                            "resume_id_tag": extracted_tag,
                        }
                    else:
                        last_error = f"Model {model} returned HTTP {response.status_code}: {response.text}"
            except Exception as e:
                last_error = str(e)

        logger.warning(f"Groq API call error ({last_error}). Using fallback classifier.")
        lower = raw_email.lower()
        recruitment_keywords = ["interview", "shortlist", "candidate", "round", "technical", "offer", "hiring", "cleared", "scheduled"]
        spam_keywords = ["discount", "deal", "newsletter", "invoice", "billing", "otp", "unsubscribe", "sale", "coupon"]

        if any(sp in lower for sp in spam_keywords) and not any(rk in lower for rk in ["interview scheduled", "offer letter"]):
            return {
                "is_interview_mail": False,
                "candidate_name": "",
                "company": "",
                "role": "",
                "status": "",
                "round": "",
                "interview_date": "",
                "resume_id_tag": "",
            }

        return {
            "is_interview_mail": True,
            "candidate_name": "Candidate",
            "company": "Company",
            "role": "Software Engineer",
            "status": "Shortlisted",
            "round": "Shortlisted",
            "interview_date": None,
            "resume_id_tag": fallback_tag or "",
        }
