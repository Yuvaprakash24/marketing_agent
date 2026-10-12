import logging

from django.conf import settings
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = PromptTemplate(
    input_variables=["text"],
    template="""
Summarise the following business knowledge base content.
Focus on the products and services, audience, positioning, tone and any facts that would
help someone write accurate marketing content for this business.
Keep it clear, concise and well structured.

Content:
{text}

Summary:
""",
)


def summarize_knowledge_base(knowledge_base_entries, business):
    """Condense all knowledge base entries into the summary used for post generation."""
    entries = list(knowledge_base_entries)
    if not entries:
        return ""

    business_info = (
        f"Business Name: {business.name}\n"
        f"Business Description: {business.description}\n"
        f"Business Industry: {business.industry}"
    )
    knowledge_base_content = "\n\n".join(entry.content for entry in entries)
    combined_content = f"{business_info}\n\n{knowledge_base_content}"

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    docs = text_splitter.create_documents([combined_content])

    try:
        chain = load_summarize_chain(
            llm=settings.LLM,
            chain_type="map_reduce",
            map_prompt=SUMMARY_PROMPT,
            combine_prompt=SUMMARY_PROMPT,
        )
        return chain.invoke(docs)["output_text"]

    except Exception as exc:  # noqa: BLE001
        logger.error("Knowledge base summarisation failed: %s", exc)
        # Keep the raw content so posts still have business context to draw on.
        return combined_content[:8000]
