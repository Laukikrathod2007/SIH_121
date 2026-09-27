"""
FastAPI Dependencies & Shared Providers.
"""

from typing import Generator
from app.core.job_store import SQLiteJobStore
from app.modules.well_intelligence.services.data_store import NWISDataStore


def get_job_store() -> SQLiteJobStore:
    return SQLiteJobStore()


def get_data_store() -> NWISDataStore:
    store = NWISDataStore()
    if not store.is_loaded():
        store.load()
    return store
