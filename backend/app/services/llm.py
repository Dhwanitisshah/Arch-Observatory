from groq import Groq

from app.config import settings

SYSTEM_PROMPT = (
    "You are a senior software engineer doing a focused code review. Given ONE "
    "architectural smell and the relevant code or dependency context, explain the "
    "concrete refactor to fix it. Be specific and actionable. Do not rewrite the "
    "whole file — describe the change and show only the key snippet. Keep it "
    "under ~250 words."
)


class LLMError(Exception):
    pass


def generate_fix(smell: dict, context: str) -> str:
    """Ask Groq for a fix suggestion. Raises LLMError on any failure — never
    leaks the API key or raw SDK exception details to callers."""
    metrics = smell.get("metrics", {})
    user_content = (
        f"Smell type: {smell.get('type')}\n"
        f"Target: {smell.get('target')}\n"
        f"Metrics: {metrics}\n\n"
        f"Context:\n{context}"
    )

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        raise LLMError("Failed to get a fix suggestion from the model") from e
