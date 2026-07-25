from collections import defaultdict
from dataclasses import dataclass

from fastapi import WebSocket


@dataclass
class Connection:
    websocket: WebSocket
    role: str  # "teacher" | "student"
    student_id: str | None = None


class ConnectionManager:
    """Broadcasts session/stage events to everyone connected to a session, and
    supports targeting a single student (for Focus Mode warnings etc. later).
    Both the teacher's live dashboard and every joined student hold a
    connection here, so stage-change commands reach every device at once."""

    def __init__(self):
        self.session_connections: dict[str, list[Connection]] = defaultdict(list)

    async def connect(self, session_code: str, websocket: WebSocket, role: str, student_id: str | None = None) -> None:
        await websocket.accept()
        self.session_connections[session_code].append(Connection(websocket, role, student_id))

    def disconnect(self, session_code: str, websocket: WebSocket) -> None:
        self.session_connections[session_code] = [
            c for c in self.session_connections[session_code] if c.websocket is not websocket
        ]

    async def broadcast(self, session_code: str, message: dict, roles: tuple[str, ...] | None = None) -> None:
        """If roles is given, only connections with that role receive the
        message. Use this for anything containing another student's
        identity or data (join/response/focus/help/status events) -- a
        student's own connection must never see another student's info.
        Leave roles as None only for messages safe for every role, like
        stage pacing commands that carry no student-identifying data."""
        dead: list[WebSocket] = []
        for conn in self.session_connections[session_code]:
            if roles is not None and conn.role not in roles:
                continue
            try:
                await conn.websocket.send_json(message)
            except Exception:
                dead.append(conn.websocket)
        for ws in dead:
            self.disconnect(session_code, ws)

    async def send_to_student(self, session_code: str, student_id: str, message: dict) -> None:
        for conn in self.session_connections[session_code]:
            if conn.role == "student" and conn.student_id == student_id:
                try:
                    await conn.websocket.send_json(message)
                except Exception:
                    self.disconnect(session_code, conn.websocket)

    def online_student_ids(self, session_code: str) -> set[str]:
        return {c.student_id for c in self.session_connections[session_code] if c.role == "student" and c.student_id}


manager = ConnectionManager()
