"""Chunk serializer - strips metadata, returns plain text"""
from typing import Optional
from uuid import UUID
from app.rag.retriever import ChunkResult


class ChunkSerializer:
    """Serializes chunks for LLM context, stripping all metadata"""

    @staticmethod
    def serialize_for_llm(chunks: list[ChunkResult]) -> str:
        """
        Build plain text context from chunks (metadata stripped).

        Returns just the concatenated content with chunk boundaries marked.
        """
        if not chunks:
            return ""

        lines = []
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"[Chunk {i}]")
            lines.append(chunk.content)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def extract_chunk_ids(chunks: list[ChunkResult]) -> list[str]:
        """Extract list of chunk IDs from chunks"""
        return [chunk.chunk_id for chunk in chunks]
