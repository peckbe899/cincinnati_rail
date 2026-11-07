"""The region model: SQLite with versioned records, ids that never change, legacy keys, seeds for git.

See migrations/0001_init.sql for the tables and db.py for the API.
"""
from . import db, seed

__all__ = ["db", "seed"]
