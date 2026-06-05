"""
AISStream.io WebSocket client.

Protocol: https://aisstream.io/documentation
- Open wss://stream.aisstream.io/v0/stream
- Send a JSON subscription on connect:
    {
        "APIKey": "...",
        "BoundingBoxes": [[[min_lat, min_lon], [max_lat, max_lon]]],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
    }
- Receive a stream of JSON messages until the socket is closed.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator

import structlog
import websockets
from websockets.exceptions import ConnectionClosed

log = structlog.get_logger(__name__)

URL = "wss://stream.aisstream.io/v0/stream"


def build_subscription(api_key: str, bbox: tuple[float, float, float, float]) -> dict:
    min_lat, min_lon, max_lat, max_lon = bbox
    return {
        "APIKey": api_key,
        "BoundingBoxes": [[[min_lat, min_lon], [max_lat, max_lon]]],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }


async def stream_messages(
    api_key: str,
    bbox: tuple[float, float, float, float],
    duration_seconds: int,
    max_reconnects: int = 3,
) -> AsyncIterator[dict]:
    """Yield AIS messages for at most `duration_seconds`. Reconnects on transient drops."""
    deadline = time.monotonic() + duration_seconds
    subscription = build_subscription(api_key, bbox)
    reconnects = 0

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        log.info("aisstream.connect", remaining_seconds=int(remaining))
        try:
            async with websockets.connect(URL, ping_interval=20, ping_timeout=20) as ws:
                await ws.send(json.dumps(subscription))
                log.info("aisstream.subscribed", bbox=bbox)

                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        log.info("aisstream.deadline_reached")
                        return
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        log.info("aisstream.deadline_reached")
                        return
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError:
                        log.warning("aisstream.bad_json", raw=str(raw)[:200])
        except ConnectionClosed as e:
            reconnects += 1
            if reconnects > max_reconnects:
                log.error("aisstream.giving_up", reconnects=reconnects, code=e.code)
                return
            backoff = min(2**reconnects, 30)
            log.warning("aisstream.reconnect", reconnects=reconnects, backoff_s=backoff, code=e.code)
            await asyncio.sleep(backoff)
        except Exception:
            log.exception("aisstream.fatal")
            return
