import asyncio
import json
import os

from channels.generic.websocket import AsyncWebsocketConsumer
from google.api_core.exceptions import GoogleAPICallError
from google.auth.credentials import AnonymousCredentials
from google.cloud.pubsub_v1.services.subscriber.async_client import SubscriberAsyncClient
from google.cloud.pubsub_v1.services.subscriber.transports.grpc_asyncio import (
    SubscriberGrpcAsyncIOTransport,
)
from google.pubsub_v1.types import PullRequest, AcknowledgeRequest, Subscription

PROJECT_ID = os.environ.get('PUBSUB_PROJECT_ID', 'fossil-dev')
SUBSCRIPTION = 'django-score-updates'
TOPIC = 'score-updates'
EMULATOR_HOST = os.environ.get('PUBSUB_EMULATOR_HOST', '')


def _make_client() -> SubscriberAsyncClient:
    if EMULATOR_HOST:
        transport = SubscriberGrpcAsyncIOTransport(
            host=EMULATOR_HOST,
            credentials=AnonymousCredentials(),
            options=[('grpc.enable_http_proxy', 0)],
        )
        return SubscriberAsyncClient(transport=transport)
    return SubscriberAsyncClient()


async def _ensure_subscription(client: SubscriberAsyncClient) -> str:
    sub_path = client.subscription_path(PROJECT_ID, SUBSCRIPTION)
    topic_path = f'projects/{PROJECT_ID}/topics/{TOPIC}'
    try:
        await client.create_subscription(
            request=Subscription(
                name=sub_path,
                topic=topic_path,
                ack_deadline_seconds=20,
            )
        )
    except Exception:
        pass  # already exists
    return sub_path


class ScoreUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self._pull_task = asyncio.create_task(self._pull_loop())

    async def disconnect(self, close_code):
        self._pull_task.cancel()
        try:
            await self._pull_task
        except asyncio.CancelledError:
            pass

    async def _pull_loop(self):
        client = _make_client()
        sub_path = await _ensure_subscription(client)
        while True:
            try:
                response = await client.pull(
                    request=PullRequest(
                        subscription=sub_path,
                        max_messages=10,
                    )
                )
                messages = response.received_messages
                if not messages:
                    await asyncio.sleep(0.2)
                    continue
                for msg in messages:
                    try:
                        data = json.loads(msg.message.data.decode('utf-8'))
                        await self.send(text_data=json.dumps(data))
                    except Exception:
                        pass
                ack_ids = [m.ack_id for m in messages]
                await client.acknowledge(
                    request=AcknowledgeRequest(
                        subscription=sub_path,
                        ack_ids=ack_ids,
                    )
                )
            except asyncio.CancelledError:
                raise
            except GoogleAPICallError:
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)
