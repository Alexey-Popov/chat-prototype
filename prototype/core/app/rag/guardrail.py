"""Post-generation access guardrail.

Re-verifies every chunk used in LLM generation against the user's current
effective table patterns (from PolicyEngine). If any chunk's table_name is
not in allowed_patterns → BLOCK, log HIGH severity.

This is the secondary enforcement layer. Primary is the retriever WHERE clause.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


class GuardrailResult:
    def __init__(self, passed: bool, violated_chunk_ids: list[str]):
        self.passed = passed
        self.violated_chunk_ids = violated_chunk_ids


class AccessGuardrail:
    @staticmethod
    async def verify(
        chunk_ids: list[str],
        allowed_table_patterns: set[str],
        vector_db: AsyncSession,
    ) -> GuardrailResult:
        """
        Fetch each chunk's metadata from vector_db and verify its table_name
        is in the user's current effective allowed patterns.

        Always re-reads from DB — never trusts in-memory state.
        """
        if not chunk_ids:
            return GuardrailResult(passed=True, violated_chunk_ids=[])

        sql = text("""
            SELECT id::text, metadata->>'table_name' AS table_name
            FROM chunks
            WHERE id::text = ANY(:chunk_ids)
        """)
        result = await vector_db.execute(sql, {"chunk_ids": chunk_ids})
        rows = {row[0]: row[1] for row in result.all()}

        violated: list[str] = []
        for chunk_id in chunk_ids:
            if chunk_id not in rows:
                violated.append(chunk_id)  # chunk not found = violation
                continue
            table_name = rows[chunk_id]
            if table_name not in allowed_table_patterns:
                violated.append(chunk_id)

        return GuardrailResult(passed=len(violated) == 0, violated_chunk_ids=violated)
