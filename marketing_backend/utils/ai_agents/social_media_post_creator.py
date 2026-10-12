"""Social media post generation.

A small LangGraph pipeline: optional web research, then post ideas, then the
final copy and an image per idea. Each stage degrades gracefully so a failure in
research or image generation still yields usable drafts.
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Union

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from social_media.models import SocialMediaPost
from utils.chat_openrouter import get_llm
from utils.image_gen import AiImageGen

logger = logging.getLogger(__name__)

# --- Platform Configuration ---
PLATFORM_CONFIGS = {
    'facebook': {
        'max_characters': 63206,
        'optimal_characters': 500,
        'hashtag_limit': 5,
        'tone': 'conversational and engaging',
    },
    'instagram': {
        'max_characters': 2200,
        'optimal_characters': 150,
        'hashtag_limit': 10,
        'tone': 'visual-first and trendy',
    },
    'twitter': {
        'max_characters': 280,
        'optimal_characters': 250,
        'hashtag_limit': 2,
        'tone': 'concise and witty',
    },
    'linkedin': {
        'max_characters': 3000,
        'optimal_characters': 1300,
        'hashtag_limit': 5,
        'tone': 'professional and informative',
    },
}

CONTENT_TYPES = [
    'educational',
    'inspirational',
    'question',
    'tip',
    'behind_scenes',
    'trending',
    'promotional',
]


# --- JSON parsing helpers ---
def extract_json_from_response(response_text: str) -> Optional[List[Dict]]:
    """Pull a JSON array out of an LLM response, tolerating prose and code fences."""
    if not response_text:
        return None

    cleaned = response_text.strip()

    if cleaned.startswith('```json'):
        cleaned = cleaned.replace('```json', '').replace('```', '').strip()
    elif cleaned.startswith('```'):
        cleaned = cleaned.replace('```', '').strip()

    array_match = re.search(r'(\[.*\])', cleaned, re.DOTALL)
    if array_match:
        cleaned = array_match.group(1)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and all(isinstance(item, dict) for item in parsed):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fall back to collecting individual objects when the array itself is malformed.
    try:
        objects = re.findall(r'\{[^{}]*"idea_number"[^{}]*\}', response_text, re.DOTALL)
        parsed_objects = []
        for obj_str in objects:
            try:
                parsed_objects.append(json.loads(obj_str))
            except json.JSONDecodeError:
                continue
        if parsed_objects:
            return parsed_objects
    except Exception:  # noqa: BLE001
        pass

    return None


def create_structured_post_ideas(response_text: str, topic: str, num_posts: int) -> List[Dict]:
    """Build usable ideas out of a non-JSON response rather than losing the generation."""
    lines = [line.strip() for line in response_text.split('\n') if line.strip()]

    post_ideas = []
    for i in range(num_posts):
        content_section = lines[i % len(lines)] if lines else f"Engaging content about {topic}"
        post_ideas.append({
            "idea_number": i + 1,
            "content_type": CONTENT_TYPES[i % len(CONTENT_TYPES)],
            "angle": f"Unique perspective {i + 1}: {content_section[:100]}",
            "key_message": content_section[:200],
            "visual_style": f"Professional, eye-catching image related to {topic}",
            "engagement_strategy": "Ask a question to encourage comments and shares",
        })

    return post_ideas


def basic_post_ideas(topic: str, num_posts: int) -> List[Dict]:
    """Last-resort ideas used when the ideas call fails outright."""
    return [
        {
            "idea_number": i + 1,
            "content_type": CONTENT_TYPES[i % len(CONTENT_TYPES)],
            "angle": f"Engaging approach {i + 1} to {topic}",
            "key_message": f"Compelling content about {topic} - focus on value and engagement",
            "visual_style": f"High-quality, professional image showcasing {topic}",
            "engagement_strategy": "Use questions and calls-to-action to boost interaction",
        }
        for i in range(num_posts)
    ]


def extract_hashtags_from_text(text: str) -> tuple[str, List[str]]:
    """Split hashtags out of the copy so they can be edited independently."""
    hashtags = re.findall(r'#\w+', text)

    clean_text = re.sub(r'#\w+\s*', '', text)
    clean_text = re.sub(r'[ \t]{2,}', ' ', clean_text).strip()

    return clean_text, [tag[1:] for tag in hashtags]


def clean_post_content(raw_content: str) -> str:
    """Strip the commentary and markdown models tend to add around the post itself."""
    content = raw_content.strip()

    separators = [
        '---',
        '**Key features:**',
        '**Features:**',
        'Key features:',
        'Features:',
        '\n\n**',
        '\n---',
        "Here's the",
        '(Analysis:',
        '[Analysis:',
        'Character count:',
        'Word count:',
    ]

    for separator in separators:
        if separator in content:
            content = content.split(separator)[0].strip()

    content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
    content = re.sub(r'\*(.*?)\*', r'\1', content)

    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()


def truncate_for_platform(post_text: str, platform: str) -> str:
    """Keep copy inside the hard platform limit, trimming at a word boundary."""
    config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['facebook'])
    limit = config['max_characters']

    if len(post_text) <= limit:
        return post_text

    truncated = post_text[:limit].rsplit(' ', 1)[0]
    logger.warning("Trimmed %s post from %s to %s characters", platform, len(post_text), len(truncated))
    return truncated


# --- LangGraph state ---
class SocialMediaGenState(BaseModel):
    topic: str
    platform: str
    business_context: Optional[str] = None
    num_posts: int = 1
    search_results: Optional[str] = None
    sources: Optional[list] = None
    post_ideas: Optional[List[Dict]] = None
    generated_posts: Optional[List[Dict]] = None
    error: Optional[str] = None
    is_research_needed: bool = True


def get_field(state: Union[SocialMediaGenState, dict], field: str):
    if isinstance(state, dict):
        return state.get(field)
    return getattr(state, field, None)


def set_field(state: Union[SocialMediaGenState, dict], field: str, value):
    if isinstance(state, dict):
        state[field] = value
    else:
        setattr(state, field, value)


# --- Node: research ---
async def research_node(
    state: Union[SocialMediaGenState, dict],
) -> Union[SocialMediaGenState, dict]:
    """Look up recent context for the topic so posts can reference what's current."""
    search_query = get_field(state, "topic")
    platform = get_field(state, "platform")

    if platform in ('instagram', 'facebook'):
        search_query += " social media trends visual content"
    elif platform == 'twitter':
        search_query += " trending news discussion"
    elif platform == 'linkedin':
        search_query += " industry insights professional"

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.warning("SERPAPI_API_KEY not set; generating without research")
        set_field(state, "search_results", "No search results available")
        set_field(state, "sources", [])
        return state

    to_date = datetime.now(dt_timezone.utc)
    from_date = to_date - timedelta(days=7)

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": search_query,
                    "api_key": api_key,
                    "engine": "google",
                    "num": 8,
                    "tbs": (
                        f"cdr:1,cd_min:{from_date.strftime('%m/%d/%Y')},"
                        f"cd_max:{to_date.strftime('%m/%d/%Y')}"
                    ),
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        sources = []
        for result in data.get("organic_results", []):
            title = result.get("title", "")
            results.append(f"• {title}: {result.get('snippet', '')}")
            sources.append({
                "title": title,
                "url": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "date_accessed": to_date.isoformat(),
            })

        set_field(state, "search_results", "\n\n".join(results))
        set_field(state, "sources", sources)
        logger.info("Found %s research results for '%s'", len(sources), search_query)

    except Exception as exc:  # noqa: BLE001 - research is optional
        logger.error("Research failed: %s", exc)
        set_field(state, "search_results", "Search unavailable")
        set_field(state, "sources", [])

    return state


# --- Node: post ideas ---
async def post_ideas_node(
    state: Union[SocialMediaGenState, dict],
) -> Union[SocialMediaGenState, dict]:
    """Produce a distinct angle per requested post."""
    if get_field(state, "error"):
        return state

    topic = get_field(state, "topic")
    platform = get_field(state, "platform")
    num_posts = get_field(state, "num_posts")
    search_results = get_field(state, "search_results") or "No research provided"
    business_context = get_field(state, "business_context") or ""

    platform_config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['facebook'])

    prompt = f"""
Generate {num_posts} creative and engaging social media post ideas for {platform.upper()} about: {topic}

Platform requirements:
- Character limit: {platform_config['max_characters']} (optimal: {platform_config['optimal_characters']})
- Hashtag limit: {platform_config['hashtag_limit']}
- Tone: {platform_config['tone']}

Business context:
{business_context}

Recent trends and information:
{search_results}

Give each idea a genuinely different angle on the topic.

IMPORTANT: Return ONLY a valid JSON array. No extra text, explanation, or markdown.

Use this exact structure:
[
    {{
        "idea_number": 1,
        "content_type": "educational",
        "angle": "unique perspective or approach",
        "key_message": "main point or hook",
        "visual_style": "description of the ideal accompanying image",
        "engagement_strategy": "how to encourage likes, comments and shares"
    }}
]

Content types to choose from: {', '.join(CONTENT_TYPES)}
"""

    try:
        llm = get_llm()
        logger.info("Generating %s post ideas for '%s' on %s", num_posts, topic, platform)
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()

        post_ideas = extract_json_from_response(response_text)

        if post_ideas:
            validated_ideas = []
            for i, idea in enumerate(post_ideas[:num_posts]):
                validated_ideas.append({
                    "idea_number": idea.get("idea_number", i + 1),
                    "content_type": idea.get("content_type", "educational"),
                    "angle": idea.get("angle", f"Engaging perspective on {topic}"),
                    "key_message": idea.get("key_message", f"Compelling message about {topic}"),
                    "visual_style": idea.get(
                        "visual_style", f"Professional image related to {topic}"
                    ),
                    "engagement_strategy": idea.get(
                        "engagement_strategy", "Ask questions to encourage comments"
                    ),
                })
            set_field(state, "post_ideas", validated_ideas)
            logger.info("Parsed %s post ideas", len(validated_ideas))
        else:
            logger.warning("Could not parse ideas as JSON; deriving them from the text")
            set_field(
                state, "post_ideas", create_structured_post_ideas(response_text, topic, num_posts)
            )

    except Exception as exc:  # noqa: BLE001
        logger.error("Post ideas generation failed: %s", exc)
        set_field(state, "post_ideas", basic_post_ideas(topic, num_posts))

    return state


# --- Node: content + image ---
async def content_generation_node(
    state: Union[SocialMediaGenState, dict],
) -> Union[SocialMediaGenState, dict]:
    """Write the publishable copy for each idea and generate a matching image."""
    if get_field(state, "error"):
        return state

    topic = get_field(state, "topic")
    platform = get_field(state, "platform")
    post_ideas = get_field(state, "post_ideas")
    business_context = get_field(state, "business_context") or ""

    if not post_ideas:
        set_field(state, "error", "No post ideas available")
        return state

    platform_config = PLATFORM_CONFIGS.get(platform, PLATFORM_CONFIGS['facebook'])
    llm = get_llm()

    try:
        image_gen = AiImageGen()
    except Exception as exc:  # noqa: BLE001 - posts are still useful without images
        logger.warning("Image generation unavailable: %s", exc)
        image_gen = None

    generated_posts = []

    for idea in post_ideas:
        try:
            content_prompt = f"""
Create a {platform} post based on this idea. Return ONLY the post content, nothing else.

Topic: {topic}
Content type: {idea.get('content_type', 'educational')}
Angle: {idea.get('angle', '')}
Key message: {idea.get('key_message', '')}

Platform requirements:
- Hard character limit: {platform_config['max_characters']} (stay under {platform_config['optimal_characters']} for best engagement)
- Tone: {platform_config['tone']}
- Include exactly {platform_config['hashtag_limit']} relevant hashtags at the end

Business context:
{business_context}

The post should:
- Hook the reader in the first line
- Match the platform's tone and style
- Include a clear call-to-action
- Use emojis strategically, not excessively
- Invite engagement through a question or prompt

IMPORTANT: Return ONLY the post text, ready to publish. No analysis, notes or explanation.
"""

            content_response = await llm.ainvoke(content_prompt)
            cleaned_content = clean_post_content(content_response.content.strip())
            post_text, hashtags = extract_hashtags_from_text(cleaned_content)
            post_text = truncate_for_platform(post_text, platform)
            hashtags = hashtags[: platform_config['hashtag_limit']]

            image_prompt = f"""
Create a high-quality, professional social media image for {platform} about: {topic}

Visual style: {idea.get('visual_style', f'Professional image related to {topic}')}
Content type: {idea.get('content_type', 'educational')}
Key message: {idea.get('key_message', '')}

Requirements:
- High resolution and visually striking
- Composed for the {platform} feed
- Clear focal point that supports the message
- Modern, clean design with vibrant colours and good contrast
- Brand-safe and commercially appropriate
- No garbled or misspelled text
"""

            image_url = None
            if image_gen:
                try:
                    image_url = image_gen.generate_image(image_prompt)
                except Exception as img_error:  # noqa: BLE001
                    logger.error("Image generation failed: %s", img_error)

            generated_posts.append({
                "post_number": idea.get('idea_number', len(generated_posts) + 1),
                "content_type": idea.get('content_type', 'educational'),
                "post_text": post_text,
                "hashtags": hashtags,
                "image_url": image_url,
                "image_prompt": image_prompt,
                "platform": platform,
                "topic": topic,
                "engagement_strategy": idea.get('engagement_strategy', ''),
                "character_count": len(post_text),
                "hashtag_count": len(hashtags),
                "created_at": datetime.now(dt_timezone.utc).isoformat(),
            })

            logger.info(
                "Generated %s post %s (%s chars, %s hashtags)",
                platform,
                idea.get('idea_number'),
                len(post_text),
                len(hashtags),
            )

        except Exception as exc:  # noqa: BLE001 - keep the posts that did succeed
            logger.error("Failed to generate post for idea %s: %s", idea.get('idea_number'), exc)
            continue

    if not generated_posts:
        set_field(state, "error", "Failed to generate any posts")
    else:
        set_field(state, "generated_posts", generated_posts)

    return state


# --- Workflow ---
async def generate_social_media_posts(
    topic: str,
    platform: str,
    num_posts: int = 1,
    business_context: str = None,
    is_research_needed: bool = True,
) -> tuple[List[Dict], list]:
    """Run the generation pipeline and return ``(posts, sources)``."""
    if platform.lower() not in PLATFORM_CONFIGS:
        raise ValueError(
            f"Unsupported platform: {platform}. Supported: {list(PLATFORM_CONFIGS.keys())}"
        )

    workflow = StateGraph(SocialMediaGenState)
    workflow.add_node("research", research_node)
    workflow.add_node("post_ideas", post_ideas_node)
    workflow.add_node("content_generation", content_generation_node)

    workflow.add_edge("research", "post_ideas")
    workflow.add_edge("post_ideas", "content_generation")
    workflow.add_edge("content_generation", END)

    workflow.set_entry_point("research" if is_research_needed else "post_ideas")

    initial_state = SocialMediaGenState(
        topic=topic,
        platform=platform.lower(),
        business_context=business_context,
        num_posts=num_posts,
        is_research_needed=is_research_needed,
    )

    app = workflow.compile()

    logger.info(
        "Generating %s %s post(s) for '%s' (research=%s)",
        num_posts,
        platform,
        topic,
        is_research_needed,
    )
    final_state = await app.ainvoke(initial_state)

    if isinstance(final_state, dict):
        error = final_state.get("error")
        generated_posts = final_state.get("generated_posts", [])
        sources = final_state.get("sources", [])
    else:
        error = getattr(final_state, "error", None)
        generated_posts = getattr(final_state, "generated_posts", [])
        sources = getattr(final_state, "sources", [])

    if error:
        raise Exception(error)

    if not generated_posts:
        raise Exception("No posts were generated")

    return generated_posts, sources


# --- Utilities ---
def get_platform_recommendations(platform: str) -> Dict[str, Any]:
    return PLATFORM_CONFIGS.get(platform.lower(), PLATFORM_CONFIGS['facebook'])


def validate_post_length(post_text: str, platform: str) -> Dict[str, Any]:
    config = PLATFORM_CONFIGS.get(platform.lower(), PLATFORM_CONFIGS['facebook'])
    char_count = len(post_text)

    return {
        "character_count": char_count,
        "max_characters": config['max_characters'],
        "optimal_characters": config['optimal_characters'],
        "is_valid": char_count <= config['max_characters'],
        "is_optimal": char_count <= config['optimal_characters'],
        "recommendation": (
            "good"
            if char_count <= config['optimal_characters']
            else "acceptable"
            if char_count <= config['max_characters']
            else "too_long"
        ),
    }


class SocialMediaPostCreator:
    """Runs the generation pipeline for a business and saves the drafts."""

    def __init__(self, business):
        self.business = business

    def build_business_context(self) -> str:
        """Everything the writer should know about the business, as plain text."""
        parts = [
            f"Business name: {self.business.name}",
            f"Industry: {self.business.industry}",
            f"Description: {self.business.description}",
        ]

        if self.business.website_url:
            parts.append(f"Website: {self.business.website_url}")

        if self.business.knowledge_base_summary:
            parts.append(f"Knowledge base summary:\n{self.business.knowledge_base_summary}")

        if self.business.system_prompt and self.business.system_prompt.social_media_system_prompt:
            parts.append(
                "Brand voice guidelines:\n"
                f"{self.business.system_prompt.social_media_system_prompt}"
            )

        return "\n\n".join(parts)

    def create_posts(self, topic, num_posts, platform, is_research_needed=True):
        """Generate posts and persist them as drafts. Runs on a background thread."""
        try:
            # A dedicated loop is needed because this runs outside the request loop.
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                generated_posts, sources = loop.run_until_complete(
                    generate_social_media_posts(
                        topic=topic,
                        platform=platform,
                        num_posts=num_posts,
                        business_context=self.build_business_context(),
                        is_research_needed=is_research_needed,
                    )
                )
            finally:
                loop.close()

            source_title = None
            source_url = None
            if sources:
                source_title = (sources[0].get("title") or "")[:100]
                source_url = sources[0].get("url") or None

            created_posts = []
            for post in generated_posts:
                created_posts.append(
                    SocialMediaPost.objects.create(
                        business=self.business,
                        post_platform=platform.lower(),
                        post_text=post.get("post_text", ""),
                        hashtags=post.get("hashtags", []),
                        post_images_urls=(
                            [post["image_url"]] if post.get("image_url") else []
                        ),
                        image_prompt=post.get("image_prompt", ""),
                        source=source_title,
                        source_url=source_url,
                        status="Draft",
                    )
                )

            logger.info(
                "Created %s social media posts for business %s",
                len(created_posts),
                self.business.id,
            )
            return created_posts

        except Exception as exc:  # noqa: BLE001
            # This runs on a daemon thread; re-raising only dumps a traceback.
            # The UI polls for new drafts, so a logged failure is the signal.
            logger.error("Failed to create posts for business %s: %s", self.business.id, exc)
            return []
