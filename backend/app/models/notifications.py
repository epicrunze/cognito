"""
Pydantic models: push notification subscriptions.

Mirrors the browser PushSubscription.toJSON() shape.
"""

from pydantic import BaseModel


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushKeys


class UnsubscribeRequest(BaseModel):
    endpoint: str
