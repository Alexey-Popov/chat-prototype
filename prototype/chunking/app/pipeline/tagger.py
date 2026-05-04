"""Chunk tagging with access control policies."""

import hashlib
from typing import Any

import yaml


class ChunkTagger:
    """Tags chunks with role-based access control metadata."""

    def __init__(self, policies_path: str) -> None:
        """Load access control policies from YAML file."""
        with open(policies_path, "r") as f:
            self.policies = yaml.safe_load(f)

    def get_metadata(
        self, table: str, row_id: str, schema_hash: str
    ) -> dict[str, Any]:
        """Generate metadata for a chunk including access control."""
        if "tables" not in self.policies:
            raise ValueError("Policies file missing 'tables' section")

        if table not in self.policies["tables"]:
            raise ValueError(f"Table '{table}' not found in policies")

        table_policy = self.policies["tables"][table]
        allowed_roles = table_policy.get("allowed_roles", [])
        allowed_users = table_policy.get("allowed_users", [])

        return {
            "table_name": table,
            "row_id": str(row_id),
            "allowed_roles": allowed_roles,
            "allowed_users": allowed_users,
            "schema_hash": schema_hash,
        }

    @staticmethod
    def compute_schema_hash(columns: list[str]) -> str:
        """Compute hash of column names for schema change detection."""
        # Sort to ensure consistent ordering
        sorted_cols = sorted(columns)
        col_string = "|".join(sorted_cols)
        return hashlib.sha256(col_string.encode()).hexdigest()[:16]
