from __future__ import annotations

from .wikipedia import WikiPage


LANGUAGE_RULES = {
    "auto": "Reply in the same language/script style the user used. If mixed, prefer the user's dominant style.",
    "en": "Reply in clear English.",
    "ur": "Reply in natural Urdu script. Keep technical names in English in parentheses when useful.",
    "roman-ur": "Reply in natural Roman Urdu using simple Pakistani vocabulary.",
    "ps": "Reply in natural Pashto. Keep technical names in English in parentheses when useful.",
}

MODE_RULES = {
    "local": (
        "The user is likely a Pakistan resident. Prefer practical local context: province/city differences, "
        "documents, government authorities, PKR, local terminology, and actionable steps."
    ),
    "visitor": (
        "The user is a visitor or foreigner interested in Pakistan. Explain local assumptions, abbreviations, "
        "cultural context, currency, etiquette, safety context, and processes that may differ for foreigners."
    ),
}


def build_system_prompt(mode: str, language: str, warnings: list[str]) -> str:
    warning_text = "\n".join(f"- {w}" for w in warnings) if warnings else "- None"
    return f"""You are Pakistan AI, a Pakistan-specialized assistant for residents and international visitors.

Core behavior:
- Be accurate, practical, neutral, and specific to Pakistan.
- Never invent facts, citations, government requirements, fees, deadlines, phone numbers, or URLs.
- Use retrieved context when it is relevant. If the context does not support a claim, clearly say what is uncertain.
- Wikipedia is useful for general/background knowledge, but it is not the final authority for government, legal, tax, immigration, identity, medical, emergency, or other high-stakes procedures.
- For high-stakes or changing procedures, tell the user to verify with the official authority shown in the source list.
- Do not claim you checked an official website unless official page content was actually provided in the retrieved context.
- Do not add fake inline citation numbers. The application renders sources separately.
- If a question is not about Pakistan, you may answer briefly but remind the user that this assistant is optimized for Pakistan.
- Prefer useful structure: short direct answer first, then steps/details where appropriate.

User mode:
{MODE_RULES.get(mode, MODE_RULES['local'])}

Language:
{LANGUAGE_RULES.get(language, LANGUAGE_RULES['auto'])}

Risk notices detected by the application:
{warning_text}
"""


def build_user_prompt(question: str, pages: list[WikiPage], official_sources: list[dict[str, str]]) -> str:
    context_blocks: list[str] = []
    for i, page in enumerate(pages, start=1):
        context_blocks.append(
            f"[Wikipedia context {i}]\nTitle: {page.title}\nLanguage: {page.language}\nURL: {page.url}\nContent:\n{page.extract}"
        )

    official_text = "\n".join(
        f"- {item['title']} ({item['authority']}): {item['url']}" for item in official_sources
    ) or "- No topic-specific official authority was matched."

    retrieved = "\n\n".join(context_blocks) or "No Wikipedia context was retrieved."

    return f"""USER QUESTION:
{question}

RETRIEVED GENERAL KNOWLEDGE:
{retrieved}

OFFICIAL AUTHORITIES TO RECOMMEND WHEN RELEVANT (links only; their page content was NOT retrieved):
{official_text}

Answer the question. Use the retrieved material when it helps. Distinguish stable background facts from details that should be verified with an official authority."""
