import logging

from django.conf import settings
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

RELEVANCE_PROMPT = PromptTemplate(
    input_variables=["text"],
    template="""
Extract the business information from the following website content: what the business
does, its products and services, audience, positioning, tone and contact details.

Website content:
{text}

Keep the original wording. Omit sections with no information, and navigation or
boilerplate text. If no relevant content is found, return an empty string.

Extracted business information:
""",
)


class WebsiteExtractor:
    """Pulls the business-relevant copy off a website for the knowledge base."""

    # Website copy is long and mostly boilerplate; cap what we send to the model.
    MAX_CHARS_FOR_LLM = 20000

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    def get_relevant_text(self, text: str) -> str:
        try:
            prompt = RELEVANCE_PROMPT.format(text=text[: self.MAX_CHARS_FOR_LLM])
            return settings.LLM.invoke(prompt).content
        except Exception as exc:  # noqa: BLE001
            logger.error("Website relevance filtering failed: %s", exc)
            return text[: self.MAX_CHARS_FOR_LLM]

    def process_website(self, url: str) -> str:
        loader = WebBaseLoader(url)
        documents = loader.load()

        chunks = self.text_splitter.split_documents(documents)
        combined = "\n\n".join(chunk.page_content for chunk in chunks)

        return self.get_relevant_text(combined)
