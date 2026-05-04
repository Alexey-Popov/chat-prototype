"""OpenAI embedding client with exponential backoff."""

import asyncio
import math
from typing import Any

from openai import AsyncOpenAI, RateLimitError

from app.config import settings


class EmbeddingService:
    """Service for embedding text using OpenAI API with exponential backoff."""

    def __init__(self) -> None:
        """Initialize the embedding service."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.batch_size = settings.batch_size
        self.max_retries = settings.max_retries
        self.initial_retry_delay = settings.initial_retry_delay

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, handling rate limiting with exponential backoff."""
        embeddings: list[list[float]] = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            embeddings.extend(await self._embed_batch_with_retry(batch))

        return embeddings

    async def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts with exponential backoff retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                # Extract embeddings from response
                embeddings = [item.embedding for item in response.data]
                return embeddings

            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.initial_retry_delay * math.pow(2, attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError("Failed to embed batch after max retries")

    async def close(self) -> None:
        """Close the client connection."""
        await self.client.close()
