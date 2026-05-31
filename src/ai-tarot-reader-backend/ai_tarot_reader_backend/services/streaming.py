import asyncio
import json
import uuid
from fastapi import Request
from loguru import logger
from ai_tarot_reader_backend.core.database import DatabaseConnection
from ai_tarot_reader_backend.core.errors import UnauthorizedError, ForbiddenError, IncompatibleStateError
from ai_tarot_reader_backend.services.notifications import StreamingNotificationsService
from ai_tarot_reader_backend.db.data_layer.sessions import SessionRepository
from ai_tarot_reader_backend.db.data_layer.users import UserRepository
from ai_tarot_reader_backend.db.data_layer.messages import MessageRepository
from ai_tarot_reader_backend.db.data_layer.cards import CardGraphRepository
from ai_tarot_reader_backend.entities.enums import SessionStatusType, EventType, ObjectType


def _sse(event: EventType, data: dict, event_id: int) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\nid: {event_id}\n\n"


def _error_sse(event_id: int, data: dict) -> str:
    return _sse(EventType.ERROR, data, event_id)


class StreamingService:
    def __init__(self, db: DatabaseConnection):
        self.listener = StreamingNotificationsService(db)

    @staticmethod
    async def validate_request(session_id: uuid.UUID, ip: str):
        user = await UserRepository.get_by_ip(ip)
        if not user:
            raise UnauthorizedError(
                user_message="User not found",
                developer_message=f"User with ip={ip} not found",
            )
        session = await SessionRepository.get_by_id(
            session_id=session_id,
            user_id=user.user_id,
        )
        if not session:
            raise ForbiddenError(
                user_message="Session not found",
                developer_message=f"Session {session_id} not found for user {ip}",
            )
        if session.status not in (SessionStatusType.PENDING, SessionStatusType.IN_PROGRESS):
            raise IncompatibleStateError(
                user_message="Session not in progress",
                developer_message=f"Session {session_id} must be in progress or pending",
            )

    async def event_generator(self, session_id: uuid.UUID, request: Request):
        queue = asyncio.Queue()

        def _enqueue(payload: str):
            queue.put_nowait(payload)

        async with self.listener.session_listener(session_id, handler=_enqueue):
            event_id = 0
            try:
                while True:
                    if await request.is_disconnected():
                        logger.info(f"Client disconnected (is_disconnected) for {session_id}")
                        break
                    try:
                        payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    except asyncio.TimeoutError:
                        yield f": heartbeat\n\n"
                        continue

                    event_id += 1
                    try:
                        payload_raw = json.loads(payload)
                    except json.JSONDecodeError as e:
                        yield _error_sse(event_id, {"errorType": "InvalidEvent", "userMessage": str(e)})
                        break

                    event_type = payload_raw.get("type", "message")
                    payload_data = payload_raw["data"]
                    logger.info(f"Received event {event_type} from {session_id} with payload {payload_data}")
                    if event_type == EventType.ERROR.value:
                        yield _error_sse(event_id, payload_data)
                        break
                    elif event_type == EventType.DONE.value:
                        break
                    else:
                        processed_payload = await self.process_payload(payload_data, event_type)
                        yield _sse(event_type, processed_payload, event_id)

            except (OSError, asyncio.CancelledError, RuntimeError) as e:
                # Клиент закрыл вкладку, оборвал сеть или нажал Stop
                logger.info(f"SSE stream interrupted for {session_id}: {type(e).__name__}")
            finally:
                logger.info(f"SSE stream finalized for {session_id}. Context manager cleanup triggered.")

    @staticmethod
    async def process_payload(payload: dict, event_type: EventType) -> dict:
        if event_type == EventType.MESSAGE:
            result_payload = []
            for payload_message in payload.get("messages"):
                if payload_message.get("message_id") and payload_message.get("objectType") == ObjectType.MESSAGE.value:
                    message = await MessageRepository.get_by_id(payload_message.get("message_id"))
                    if message:
                       result_payload.append({"role": message.role, "content": message.content, "objectType": ObjectType.MESSAGE.value})
                elif payload_message.get("objectType") == ObjectType.MESSAGE.value:
                    result_payload.append(payload_message)
                if payload_message.get("objectType") == ObjectType.CARD.value:
                    if payload_message.get("cardId"):
                        card_info = await CardGraphRepository.get_card_data(payload_message.get("cardId"))

                        title = card_info["title"].strip('"')
                        meaning = card_info["meaning"].strip('"')
                        arcana = card_info["arcana"].strip('"')
                        reversed = card_info["reversed"]
                        result_payload.append({
                            "objectType": ObjectType.CARD.value,
                            "cardId": payload_message.get("cardId"),
                            "title": title,
                            "arcana": arcana,
                            "meaning": meaning,
                            "reversed": reversed
                        })
            return {"messages": result_payload}
        return payload
