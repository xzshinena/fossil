import logging
from datetime import datetime, timezone

from django.conf import settings
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

_client: MongoClient | None = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGODB_URI)
    return _client.get_default_database()


def get_raw_collection() -> Collection:
    db = get_db()
    col = db['raw_scores']
    col.create_index(
        [('source', ASCENDING), ('language', ASCENDING), ('year', ASCENDING), ('month', ASCENDING)],
        unique=True,
        background=True,
    )
    return col


def upsert_raw(
    source: str,
    language: str,
    year: int,
    month: int,
    raw_value: float,
    extra: dict | None = None,
) -> dict:
    col = get_raw_collection()
    doc = {
        'source': source,
        'language': language,
        'year': year,
        'month': month,
        'raw_value': raw_value,
        'ingested_at': datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    col.update_one(
        {'source': source, 'language': language, 'year': year, 'month': month},
        {'$set': doc},
        upsert=True,
    )
    logger.debug('upserted raw %s/%s %d-%02d = %s', source, language, year, month, raw_value)
    return doc
