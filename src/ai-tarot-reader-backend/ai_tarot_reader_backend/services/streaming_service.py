import json
import random
import uuid
from typing import AsyncGenerator
from uuid import UUID

from openai import AsyncOpenAI

from ai_tarot_reader_backend.api.schemas.streaming import SseEvent
from ai_tarot_reader_backend.configs import get_config
from ai_tarot_reader_backend.core.errors import NotFoundError, UnauthorizedError
from ai_tarot_reader_backend.db.data_layer.cards import CardGraphRepository
from ai_tarot_reader_backend.db.data_layer.images import CardImageRepository
from ai_tarot_reader_backend.db.data_layer.messages import MessageRepository
from ai_tarot_reader_backend.db.data_layer.sessions import SessionRepository
from ai_tarot_reader_backend.db.data_layer.users import UserRepository
from ai_tarot_reader_backend.entities.enums import (
    MessageRoleType,
    SessionStageType,
    SessionStatusType,
    UIThemeType,
)
from ai_tarot_reader_backend.services import ml_client
from ai_tarot_reader_backend.services.prompts import get_clarification_prompt, get_system_prompt


def _sse(event: SseEvent, data: dict, event_id: int) -> str:
    return f"event: {event.value}\ndata: {json.dumps(data, ensure_ascii=False)}\nid: {event_id}\n\n"


def _error_sse(message: str, event_id: int) -> str:
    return _sse(SseEvent.error, {"message": message}, event_id)


def _openrouter_client() -> AsyncOpenAI:
    config = get_config()
    return AsyncOpenAI(
        base_url=config.open_router.base_url,
        api_key=config.open_router.api_key.get_secret_value(),
    )


class StreamingService:

    @staticmethod
    async def stream(ip: str, session_id: str) -> AsyncGenerator[str, None]:
        event_id = 0

        try:
            user = await UserRepository.get_by_ip(ip)
            if not user:
                yield _error_sse("Пользователь не найден", event_id + 1)
                return

            session = await SessionRepository.get_by_id(
                session_id=UUID(session_id),
                user_id=user.user_id,
                with_messages=True,
            )
            if not session:
                yield _error_sse("Сессия не найдена", event_id + 1)
                return

            messages = await MessageRepository.get_by_session(UUID(session_id))
            user_messages = [m for m in messages if m.role == "user"]
            if not user_messages:
                yield _error_sse("Вопрос не найден в сессии", event_id + 1)
                return

            user_question = user_messages[-1].content
            is_clarification = session.stage == SessionStageType.CLARIFICATION.value

            await SessionRepository.update_state(
                session_id=UUID(session_id),
                status=SessionStatusType.IN_PROGRESS,
            )

            validation = await ml_client.validate_message(user_question)
            if validation["decision"] == "blocked":
                await SessionRepository.update_state(
                    session_id=UUID(session_id),
                    status=SessionStatusType.FAILED,
                )
                event_id += 1
                yield _sse(SseEvent.message, {
                    "role": MessageRoleType.ASSISTANT.value,
                    "content": "Карты не могут ответить на этот вопрос. Попробуй спросить о чём-то личном.",
                }, event_id)
                return

            if not is_clarification:
                classification = await ml_client.classify_message(user_question)
                theme = classification["theme"]
                await SessionRepository.update_state(
                    session_id=UUID(session_id),
                    theme=theme,
                )
            else:
                theme = session.theme

            event_id += 1
            yield _sse(SseEvent.theme, {"theme": theme}, event_id)

            all_card_ids = list(range(78))
            used_card_ids = list(session.prediction_cards or [])

            if is_clarification:
                available = [c for c in all_card_ids if c not in used_card_ids]
                chosen_ids = random.sample(available, 1)
                await SessionRepository.update_state(
                    session_id=UUID(session_id),
                    clarification_card=chosen_ids[0],
                    stage=SessionStageType.CLARIFICATION,
                )
            else:
                chosen_ids = random.sample(all_card_ids, 3)
                await SessionRepository.update_state(
                    session_id=UUID(session_id),
                    prediction_cards=chosen_ids,
                )

            cards_data = []
            card_meanings = []

            for card_id in chosen_ids:
                image = await CardImageRepository.get_by_card_id(card_id, UIThemeType.PINK)
                card_info = await CardGraphRepository.get_card_data(card_id)
                is_reversed = random.choice([True, False])

                title = card_info["title"].strip('"') if card_info else f"Карта {card_id}"
                meaning = card_info["meaning"].strip('"') if card_info else ""

                cards_data.append({
                    "cardId": card_id,
                    "title": title,
                    "reversed": is_reversed,
                    "imageBase64": image.image.hex() if image else None,
                })
                card_meanings.append(
                    f"{title} ({'перевёрнутая' if is_reversed else 'прямая'}): {meaning[:200]}"
                )

            event_id += 1
            yield _sse(SseEvent.cards, {"cards": cards_data}, event_id)

            tone = session.tone
            if is_clarification:
                system_prompt = get_clarification_prompt(tone=tone)
                history = [
                    {"role": m.role, "content": m.content}
                    for m in messages
                    if not (m.role == "user" and m.content == user_question)
                ]
                llm_messages = [
                    {"role": "system", "content": system_prompt},
                    *history,
                    {
                        "role": "user",
                        "content": (
                            f"Уточняющий вопрос: {user_question}\n"
                            f"Новая карта: {', '.join(card_meanings)}"
                        ),
                    },
                ]
            else:
                system_prompt = get_system_prompt(theme=theme, tone=tone)
                llm_messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Вопрос: {user_question}\n"
                            f"Карты: {', '.join(card_meanings)}"
                        ),
                    },
                ]

            client = _openrouter_client()
            full_response = ""

            async with client as c:
                stream = await c.chat.completions.create(
                    model=get_config().open_router.model,
                    messages=llm_messages,
                    stream=True,
                    max_tokens=1000,
                )
                async for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        full_response += delta
                        event_id += 1
                        yield _sse(SseEvent.message, {
                            "role": MessageRoleType.ASSISTANT.value,
                            "content": delta,
                        }, event_id)

            await MessageRepository.create(
                message_id=uuid.uuid4(),
                session_id=UUID(session_id),
                role=MessageRoleType.ASSISTANT,
                content=full_response,
            )

            session_title = user_question[:50] + "..." if len(user_question) > 50 else user_question

            await SessionRepository.update_state(
                session_id=UUID(session_id),
                status=SessionStatusType.DONE,
                title=session_title,
            )

            event_id += 1
            yield _sse(SseEvent.session_title, {"title": session_title}, event_id)

        except Exception as e:
            event_id += 1
            yield _error_sse(f"Внутренняя ошибка: {str(e)}", event_id)
            try:
                await SessionRepository.update_state(
                    session_id=UUID(session_id),
                    status=SessionStatusType.FAILED,
                )
            except Exception:
                pass