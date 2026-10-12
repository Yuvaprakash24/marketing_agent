import logging

from django.conf import settings

logger = logging.getLogger(__name__)

FALLBACK_SOCIAL_PROMPT = """
You are a social media content creator for this business. Write posts that are on-brand,
specific and useful. Lead with a hook, keep one clear idea per post, close with a
call-to-action, and match the tone and character limits of the target platform.
"""

RESEARCH_PROMPT = (
    "Research the web for recent news and developments about this business, its industry "
    "and its competitors. Prefer sources from the last 7 days and prioritise facts that "
    "could anchor a timely social media post."
)


class BusinessPromptGenerator:
    """Derives a brand-voice system prompt from the business knowledge base."""

    def generate_prompt(self, business_name, business_summary) -> str:
        try:
            response = settings.LLM.invoke(f"""
Given this business context:

Business name: {business_name}
Business summary: {business_summary}

Write a detailed system prompt for a social media content creator AI that works for this
business. The prompt should:
1. Establish the AI's role as this business's social media content creator
2. Give concrete guidelines for creating posts
3. Define the tone and voice requirements
4. Set content quality standards
5. Explain how to use the business's unique aspects and offerings
6. Note how to adapt structure per platform (Facebook, Instagram, Twitter, LinkedIn)

Keep it focused on content creation. Return only the system prompt.
""")
            return response.content

        except Exception as exc:  # noqa: BLE001 - business creation should not fail on this
            logger.error("Failed to generate the brand voice prompt: %s", exc)
            return FALLBACK_SOCIAL_PROMPT.strip()
