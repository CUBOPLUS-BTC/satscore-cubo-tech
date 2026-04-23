"""WebhookDispatcher — async, queue-based delivery engine.

Delivers webhook payloads to subscriber URLs with:
* HMAC-SHA256 request signing
* 3 delivery attempts with exponential back-off
* Thread-based async dispatch (no event-loop dependencies)
* Per-subscription in-memory delivery log (last 100 entries)
* Automatic subscription disabling after 10 consecutive failures
"""

from __future__ import annotations

import hashlib
import hmac
import json
import queue
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from typing import Dict, List, Optional

from .manager import WebhookManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
INITIAL_BACKOFF = 2       # seconds
BACKOFF_MULTIPLIER = 2    # exponential factor
MAX_DELIVERY_LOG = 100    # log entries per subscription
DELIVERY_TIMEOUT = 10     # HTTP request timeout in seconds
QUEUE_GET_TIMEOUT = 2     # seconds to wait for new jobs before looping

# Supported event types (mirrors manager.SUPPORTED_EVENTS)
EVENT_TYPES = {
    "price_alert",
    "fee_alert",
    "deposit_confirmed",
    "achievement_earned",
    "goal_reached",
    "savings_updated",
    "score_computed",
    "session_created",
}


class WebhookDispatcher:
    """Asynchronous webhook dispatcher.

    Accepts dispatch requests on the main thread, queues them, and
    processes them in a dedicated background thread so HTTP calls never
    block the request/response cycle.

    Parameters
    ----------
    manager:
        A :class:`~app.webhooks.manager.WebhookManager` instance used to
        look up subscribers and record delivery outcomes.
    """

    def __init__(self, manager: WebhookManager) -> None:
        self._manager = manager
        self._queue: queue.Queue = queue.Queue()
        self._delivery_log: Dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_DELIVERY_LOG))
        self._log_lock = threading.Lock()
        self._running = False
        self._worker: Optional[threading.Thread] = None
        self._stats: Dict[str, int] = {
            "dispatched": 0,
            "delivered": 0,
            "failed": 0,
            "retried": 0,
        }
        self._stats_lock = threading.Lock()
        self._start_worker()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _start_worker(self) -> None:
        """Start the background delivery thread."""
        self._running = True
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="webhook-dispatcher",
            daemon=True,
        )
        self._worker.start()

    def stop(self) -> None:
        """Signal the worker thread to exit and wait for it."""
        self._running = False
        # Unblock the queue.get() call in the worker.
        self._queue.put(None)
        if self._worker is not None:
            self._worker.join(timeout=5)

    # ------------------------------------------------------------------
    # Public dispatch API
    # ------------------------------------------------------------------

    def dispatch(
        self,
        event_type: str,
        data: dict,
        pubkeys: Optional[List[str]] = None,
    ) -> int:
        """Enqueue a webhook delivery job.

        Parameters
        ----------
        event_type:
            One of the ``EVENT_TYPES`` strings.
        data:
            Arbitrary event payload (must be JSON-serialisable).
        pubkeys:
            Optional list of pubkeys to restrict delivery to.  If
            ``None``, *all* active subscribers of *event_type* are
            notified.

        Returns
        -------
        int
            Number of subscriptions enqueued for delivery.
        """
        if event_type not in EVENT_TYPES:
            raise ValueError(
                f"Unknown event type: {event_type!r}. "
                f"Supported: {sorted(EVENT_TYPES)}"
            )

        if pubkeys is not None:
            subscriptions = self._manager.get_subscribers_for_pubkeys(
                event_type, pubkeys
            )
        else:
            subscriptions = self._manager.get_subscribers_for_event(event_type)

        if not subscriptions:
            return 0

        payload = {
            "event": event_type,
            "data": data,
            "timestamp": int(time.time()),
        }

        count = 0
        for sub in subscriptions:
            self._queue.put((sub, payload, 0))  # (subscription, payload, attempt)
            count += 1

        with self._stats_lock:
            self._stats["dispatched"] += count

        return count

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Background loop: drain the queue and deliver webhooks."""
        while self._running:
            try:
                item = self._queue.get(timeout=QUEUE_GET_TIMEOUT)
            except queue.Empty:
                continue

            if item is None:
                # Shutdown sentinel.
                break

            sub, payload, attempt = item
            try:
                self._deliver(sub, payload, attempt)
            except Exception:
                # Last-resort catch so the worker never crashes silently.
                pass
            finally:
                self._queue.task_done()

    # ------------------------------------------------------------------
    # Delivery logic
    # ------------------------------------------------------------------

    def _deliver(self, subscription: dict, payload: dict, attempt: int) -> None:
        """Attempt to deliver *payload* to *subscription*.

        Applies exponential back-off before retrying.  Records result
        in the delivery log and updates the subscription failure count.
        """
        if attempt > 0:
            backoff = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** (attempt - 1))
            time.sleep(backoff)
            with self._stats_lock:
                self._stats["retried"] += 1

        success = self._send_webhook(subscription, payload)
        self._manager.record_delivery(subscription["id"], success)
        self._log_delivery(subscription["id"], payload, success, attempt)

        if success:
            with self._stats_lock:
                self._stats["delivered"] += 1
        else:
            with self._stats_lock:
                self._stats["failed"] += 1

            next_attempt = attempt + 1
            if next_attempt < MAX_RETRIES:
                self._queue.put((subscription, payload, next_attempt))

    def _send_webhook(self, subscription: dict, payload: dict) -> bool:
        """Perform the HTTP POST delivery.

        Returns ``True`` on 2xx response, ``False`` otherwise.
        """
        url = subscription.get("url", "")
        secret = subscription.get("secret", "")

        try:
            body = json.dumps(payload).encode("utf-8")
            signature = self._sign_payload(body.decode("utf-8"), secret)

            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            req.add_header("X-Magma-Signature", signature)
            req.add_header("X-Magma-Event", payload.get("event", ""))
            req.add_header("X-Magma-Timestamp", str(payload.get("timestamp", 0)))
            req.add_header("User-Agent", "Magma-Webhook/1.0")

            with urllib.request.urlopen(req, timeout=DELIVERY_TIMEOUT) as resp:
                return 200 <= resp.status < 300
        except urllib.error.HTTPError as exc:
            # 4xx/5xx are failures.
            return False
        except Exception:
            return False

    @staticmethod
    def _sign_payload(payload: str, secret: str) -> str:
        """Return ``sha256=<hex>`` HMAC-SHA256 signature of *payload*."""
        if not secret:
            return ""
        mac = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        )
        return f"sha256={mac.hexdigest()}"

    # ------------------------------------------------------------------
    # Delivery log
    # ------------------------------------------------------------------

    def _log_delivery(
        self,
        sub_id: str,
        payload: dict,
        success: bool,
        attempt: int,
    ) -> None:
        entry = {
            "event": payload.get("event"),
            "timestamp": payload.get("timestamp"),
            "delivered_at": int(time.time()),
            "attempt": attempt,
            "success": success,
        }
        with self._log_lock:
            self._delivery_log[sub_id].append(entry)

    def get_delivery_log(self, sub_id: str, limit: int = 20) -> List[dict]:
        """Return the last *limit* delivery log entries for *sub_id*."""
        with self._log_lock:
            dq = self._delivery_log.get(sub_id, deque())
            entries = list(dq)
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Manual retry
    # ------------------------------------------------------------------

    def retry_failed(self, pubkey: str, sub_id: str) -> bool:
        """Re-enqueue the last failed delivery for a subscription.

        Returns ``True`` if a failed entry was found and re-queued.
        """
        with self._log_lock:
            dq = self._delivery_log.get(sub_id, deque())
            failed = [e for e in dq if not e["success"]]

        if not failed:
            return False

        last_failed = failed[-1]
        sub = self._get_sub_by_id(sub_id, pubkey)
        if sub is None:
            return False

        dummy_payload = {
            "event": last_failed["event"],
            "data": {},
            "timestamp": int(time.time()),
            "_retry": True,
        }
        self._queue.put((sub, dummy_payload, 0))
        return True

    def _get_sub_by_id(self, sub_id: str, pubkey: str) -> Optional[dict]:
        subs = self._manager.list_subscriptions(pubkey)
        for s in subs:
            if s["id"] == sub_id:
                return s
        return None

    # ------------------------------------------------------------------
    # Stats / health
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return aggregate dispatcher statistics."""
        with self._stats_lock:
            stats = dict(self._stats)
        stats["queue_size"] = self._queue.qsize()
        stats["worker_alive"] = self._worker is not None and self._worker.is_alive()
        stats["tracked_subscriptions"] = len(self._delivery_log)
        return stats

    def send_test(self, subscription: dict) -> bool:
        """Send a test payload immediately (blocking).  Returns success flag."""
        payload = {
            "event": "test",
            "data": {
                "message": "This is a test webhook from Magma.",
                "subscription_id": subscription.get("id"),
            },
            "timestamp": int(time.time()),
        }
        return self._send_webhook(subscription, payload)
