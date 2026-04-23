"""Webhook / notification system for the Magma API.

Provides subscription management (CRUD via WebhookManager), async
delivery with retry logic (WebhookDispatcher), and HTTP route
handlers (routes module).

Typical setup (module-level singleton)
---------------------------------------
::

    from app.webhooks import WebhookManager, WebhookDispatcher, routes

    _manager    = WebhookManager()
    _dispatcher = WebhookDispatcher(_manager)

    # In the HTTP router:
    result, status = routes.handle_webhook_subscribe(body, pubkey, _manager)
"""

from .manager import WebhookManager, SUPPORTED_EVENTS
from .dispatcher import WebhookDispatcher
from . import routes

__all__ = [
    "WebhookManager",
    "WebhookDispatcher",
    "SUPPORTED_EVENTS",
    "routes",
]
