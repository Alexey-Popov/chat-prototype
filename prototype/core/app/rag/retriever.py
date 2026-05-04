"""Access-filtered chunk retriever using pgvector.

Filters by table_name matching the user's effective allowed table patterns
(resolved by PolicyEngine). Role names in metadata are NOT compared here —
the policy engine's output is the authoritative access decision.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from openai import AsyncOpenAI
from app.config import settings


class ChunkResult:
    def __init__(self, chunk_id: str, content: str, metadata: dict):
        self.chunk_id = chunk_id
        self.content = content
        self.metadata = metadata


class AccessFilteredRetriever:
    def __init__(self, vector_db: AsyncSession, allowed_table_patterns: set[str]):
        self.vector_db = vector_db
        self.allowed_table_patterns = allowed_table_patterns
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def retrieve(self, query: str, top_k: int = 5) -> list[ChunkResult]:
        """
        Retrieve top_k chunks relevant to query, filtered at query time
        by the user's effective table patterns. No post-filter.
        """
        if not self.allowed_table_patterns:
            return []

        embedding_response = await self._client.embeddings.create(
            model=settings.embedding_model,
            input=query,
        )
        query_embedding = embedding_response.data[0].embedding
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = text("""
            SELECT id::text, content, metadata
            FROM chunks
            WHERE metadata->>'table_name' = ANY(:patterns)
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """)

        result = await self.vector_db.execute(
            sql,
            {
                "patterns": list(self.allowed_table_patterns),
                "query_embedding": embedding_str,
                "top_k": top_k,
            },
        )

        return [
            ChunkResult(chunk_id=str(row[0]), content=row[1], metadata=row[2] or {})
            for row in result.all()
        ]
