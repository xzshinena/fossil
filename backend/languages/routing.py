from django.urls import path
from .consumers import ScoreUpdateConsumer

websocket_urlpatterns = [
    path('ws/scores/', ScoreUpdateConsumer.as_asgi()),
]
