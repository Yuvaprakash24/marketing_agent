import logging
import os
import uuid

from django.core.files.base import ContentFile
from google import genai
from google.genai.types import GenerateContentConfig, Modality

from core.storage_backends import PublicMediaStorage

logger = logging.getLogger(__name__)


class AiImageGen:
    """Generates post images with Gemini and stores them in Supabase."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.client = genai.Client(api_key=self.api_key)
        self.model = os.getenv(
            "GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation"
        )

    def generate_image(self, prompt: str) -> str | None:
        """Return the public URL of the generated image, or None on failure."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    response_modalities=[Modality.IMAGE, Modality.TEXT]
                ),
            )

            if not response.candidates:
                logger.error("No candidates returned for image prompt")
                return None

            candidate = response.candidates[0]
            for part in candidate.content.parts:
                if part.inline_data is not None:
                    return self._save_to_supabase(part.inline_data.data)

            logger.error("No image data found in the Gemini response")
            return None

        except Exception as exc:  # noqa: BLE001
            logger.error("Error generating image for '%s...': %s", prompt[:100], exc)
            return None

    def _save_to_supabase(self, image_bytes: bytes, filename_prefix: str = "post_img") -> str | None:
        try:
            filename = f"{filename_prefix}_{uuid.uuid4().hex}.png"
            storage = PublicMediaStorage()
            path = f"ai_generated_images/{filename}"
            storage.save(path, ContentFile(image_bytes))
            return storage.url(path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to upload image to Supabase: %s", exc)
            return None
