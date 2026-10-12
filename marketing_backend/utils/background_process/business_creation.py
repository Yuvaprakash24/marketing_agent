"""Background business onboarding.

Runs on a worker thread after the create-business request returns, and reports
progress through ``BusinessProcessingStatus`` which the UI polls.
"""

import logging
import os
import shutil

from django.conf import settings

from business.models import BusinessProcessingStatus, BusinessUser
from core.models import Business, KnowledgeBase, SystemPrompt, User
from utils.ai_agents.create_system_prompts import RESEARCH_PROMPT, BusinessPromptGenerator
from utils.ai_agents.knowledge_base_summarizer import summarize_knowledge_base
from utils.extractors.document_extractor import DocumentToKnowledgeBase
from utils.extractors.website_extractor import WebsiteExtractor

logger = logging.getLogger(__name__)


class BusinessBackgroundProcessor:
    def __init__(self):
        self.website_extractor = WebsiteExtractor()
        self.doc_extractor = DocumentToKnowledgeBase()
        self.system_prompt_generator = BusinessPromptGenerator()

    def process_business(self, request_id, business_data, files_data, user_id):
        """Create the business, build its knowledge base, derive its brand voice."""
        logger.info("Starting business processing for request %s", request_id)
        processing_status = BusinessProcessingStatus.objects.get(id=request_id)
        request_dir = f'business_processing/{request_id}'

        try:
            processing_status.status = 'processing'
            processing_status.message = 'Creating business...'
            processing_status.save()

            business = Business.objects.create(
                created_by_id=user_id,
                **{k: v for k, v in business_data.items() if v},
            )
            BusinessUser.objects.create(
                business=business, user=User.objects.get(id=user_id), role='admin'
            )
            logger.info("Created business %s", business.id)

            processing_status.business = business
            processing_status.save()

            # Website content is the richest source, so it is pulled first.
            if business_data.get('website_url'):
                processing_status.message = 'Reading your website...'
                processing_status.save()
                try:
                    website_content = self.website_extractor.process_website(
                        business_data['website_url']
                    )
                    if website_content:
                        kb = KnowledgeBase.objects.create(
                            name=f"{business.name} Website Content",
                            content=website_content,
                        )
                        kb.businesses_knowledge_base.add(business)
                except Exception as exc:  # noqa: BLE001 - one bad site should not fail onboarding
                    logger.error("Website processing failed: %s", exc)

            if files_data:
                processing_status.message = 'Processing uploaded documents...'
                processing_status.save()

            for file_data in files_data:
                try:
                    file_content = self.doc_extractor.process_document(file_data['path'])
                    if file_content:
                        kb = KnowledgeBase.objects.create(
                            name=file_data['name'],
                            content=file_content,
                        )
                        kb.businesses_knowledge_base.add(business)
                except Exception as exc:  # noqa: BLE001
                    logger.error("Failed to process %s: %s", file_data['name'], exc)

            processing_status.message = 'Summarising your knowledge base...'
            processing_status.save()

            knowledge_base_entries = KnowledgeBase.objects.filter(
                businesses_knowledge_base=business
            )
            business.knowledge_base_summary = summarize_knowledge_base(
                knowledge_base_entries, business
            )
            business.save()

            processing_status.message = 'Learning your brand voice...'
            processing_status.save()

            social_prompt = self.system_prompt_generator.generate_prompt(
                business.name, business.knowledge_base_summary
            )
            business.system_prompt = SystemPrompt.objects.create(
                social_media_system_prompt=social_prompt,
                research_system_prompt=RESEARCH_PROMPT,
            )
            business.save()

            processing_status.status = 'completed'
            processing_status.message = 'Business processing completed successfully'
            processing_status.save()
            logger.info("Finished business processing for request %s", request_id)

        except Exception as exc:  # noqa: BLE001
            logger.error("Error in business processing: %s", exc, exc_info=True)
            processing_status.status = 'error'
            processing_status.message = f"Error processing business: {exc}"
            processing_status.save()

        finally:
            # request_dir is a directory of staged uploads, so it needs rmtree
            # rather than a storage delete() call.
            staged_dir = os.path.join(settings.MEDIA_ROOT, request_dir)
            try:
                shutil.rmtree(staged_dir, ignore_errors=True)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not clean up %s: %s", staged_dir, exc)


# Reused across requests so the extractors are only constructed once.
business_background_processor = BusinessBackgroundProcessor()
