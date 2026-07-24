from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Broadcasts session events (joins, responses) to connected teacher dashboards."""

    def __init__(self):
        self.session_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, session_code: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.session_connections[session_code].append(websocket)

    def disconnect(self, session_code: str, websocket: WebSocket) -> None:
        if websocket in self.session_connections[session_code]:
            self.session_connections[session_code].remove(websocket)

    async def broadcast(self, session_code: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.session_connections[session_code]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_code, ws)


manager = ConnectionManager()
