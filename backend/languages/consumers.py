import asyncio
import json
import os

from channels.generic.websocket import AsyncWebsocketConsumer
from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPICallError

PROJECT_ID = os.environ.get('PUBSUB_PROJECT_ID', 'fossil-dev')
SUBSCRIPTION = 'django-score-updates'
TOPIC = 'score-updates'


def _make_client() -> pubsub_v1.SubscriberClient:
    # PUBSUB_EMULATOR_HOST env var is auto-detected by the library
    return pubsub_v1.SubscriberClient()


def _ensure_subscription(client: pubsub_v1.SubscriberClient) -> str:
    sub_path = client.subscription_path(PROJECT_ID, SUBSCRIPTION)
    topic_path = f'projects/{PROJECT_ID}/topics/{TOPIC}'
    try:
        client.create_subscription(
            request={
                'name': sub_path,
                'topic': topic_path,
                'ack_deadline_seconds': 20,
            }
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
        loop = asyncio.get_event_loop()
        client = await loop.run_in_executor(None, _make_client)
        sub_path = await loop.run_in_executor(None, _ensure_subscription, client)

        while True:
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: client.pull(
                        request={
                            'subscription': sub_path,
                            'max_messages': 10,
                        }
                    ),
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
                await loop.run_in_executor(
                    None,
                    lambda: client.acknowledge(
                        request={
                            'subscription': sub_path,
                            'ack_ids': ack_ids,
                        }
                    ),
                )
            except asyncio.CancelledError:
                raise
            except GoogleAPICallError:
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)
