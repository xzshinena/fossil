import json
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

_publisher = None
_topic_path: str | None = None
RAW_EVENTS_TOPIC = 'raw-events'


def _get_publisher():
    global _publisher, _topic_path
    if _publisher is None:
        from google.cloud import pubsub_v1
        _publisher = pubsub_v1.PublisherClient()
        project = settings.PUBSUB_PROJECT_ID
        _topic_path = _publisher.topic_path(project, RAW_EVENTS_TOPIC)
        _ensure_topic(_publisher, _topic_path)
    return _publisher, _topic_path


def _ensure_topic(publisher, topic_path: str) -> None:
    try:
        publisher.create_topic(request={'name': topic_path})
        logger.info('created Pub/Sub topic %s', topic_path)
    except Exception:
        # topic already exists or emulator already has it
        pass


def publish_raw_event(
    source: str,
    language: str,
    year: int,
    month: int,
    raw_value: float,
    language_id: int | None = None,
) -> None:
    try:
        publisher, topic_path = _get_publisher()
        payload = json.dumps({
            'source': source,
            'language': language,
            'language_id': language_id,
            'year': year,
            'month': month,
            'raw_value': raw_value,
        }).encode('utf-8')
        future = publisher.publish(topic_path, payload)
        future.result(timeout=5)
    except Exception as exc:
        # Pub/Sub failures must never crash the ingest scripts
        logger.warning('pub/sub publish failed (%s): %s', source, exc)
