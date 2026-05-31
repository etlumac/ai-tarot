import uuid
import random
import asyncio
from loguru import logger

from ai_tarot_reader_backend.core.database import DatabaseConnection, session_lifespan
from ai_tarot_reader_backend.services.ml_client import MLClient
from ai_tarot_reader_backend.services.llm import LLMClient
from ai_tarot_reader_backend.db.data_layer.sessions import SessionRepository
from ai_tarot_reader_backend.db.data_layer.cards import CardGraphRepository
from ai_tarot_reader_backend.db.data_layer.messages import MessageRepository
from ai_tarot_reader_backend.entities.enums import (
    MessageRoleType,
    SessionStatusType,
    ToneType,
    EventType,
    ObjectType
)
from ai_tarot_reader_backend.entities.domain import SessionEntity, MessageEntity
from ai_tarot_reader_backend.services.prompts import get_system_prompt, get_clarification_prompt
from ai_tarot_reader_backend.services.notifications import StreamingNotificationsService


class PredictionService:

    def __init__(self, ml_client: MLClient, llm_client: LLMClient, db: DatabaseConnection):
        self.ml_client = ml_client
        self.llm_client = llm_client
        self.db = db
        self.notifications = StreamingNotificationsService(db)

    @staticmethod
    def __form_title_messages(user_question: str) -> list[dict[str, str]]:
        system_prompt = "Твоя задача - придумать КОРОТКОЕ название для пользовательского диалога на основе его вопроса. Название должно отражать суть и быть очень кратким, несколько слов"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ]

    async def prediction_pipeline(self, session_id: uuid.UUID, user_question: str, tone: ToneType):
        async with session_lifespan(self.db):
            try:
                await SessionRepository.update_state(
                    session_id=session_id,
                    status=SessionStatusType.IN_PROGRESS,
                )
                logger.info(f"Session with id {session_id} started prediction pipeline")
                validation = await self.ml_client.validate_message(user_question)
                if validation["decision"] == "blocked":
                    await SessionRepository.update_state(
                        session_id=session_id,
                        status=SessionStatusType.FAILED,
                    )
                    message = {"objectType": ObjectType.MESSAGE.value, "role": MessageRoleType.ASSISTANT.value,
                               "content": "Карты не могут ответить на этот вопрос. Попробуй спросить о чём-то личном"}
                    await self.notifications.notify_session(session_id, EventType.MESSAGE.value,
                                                            {"messages": [message]})
                    logger.warning(f"Session with id {session_id} blocked")
                    return
                logger.info(f"Session with id {session_id} validation result: {validation["decision"]}")

                classification, session_title = await asyncio.gather(self.ml_client.classify_message(user_question),
                                                                     self.llm_client(
                                                                         self.__form_title_messages(user_question),
                                                                         max_tokens=50))
                theme = classification["theme"]
                logger.info(f"Session with id {session_id} theme: {theme}")
                logger.info(f"Session with id {session_id} title: {session_title}")
                await SessionRepository.update_state(
                    session_id=session_id,
                    theme=theme,
                    title=session_title
                )

                await self.notifications.notify_session(session_id, EventType.THEME.value, {"theme": theme})
                await self.notifications.notify_session(session_id, EventType.TITLE.value, {"title": session_title})

                all_card_ids = list(range(78))

                chosen_ids = random.sample(all_card_ids, 3)
                await SessionRepository.update_state(
                    session_id=session_id,
                    prediction_cards=chosen_ids,
                )
                logger.info(f"Session with id {session_id} cards: {chosen_ids}")

                cards_data = []
                card_meanings = []
                card_titles: dict[int, str] = {}

                for card_id in chosen_ids:
                    card_info = await CardGraphRepository.get_card_data(card_id)

                    title = card_info["title"].strip('"') if card_info else f"Карта {card_id}"
                    meaning = card_info["meaning"].strip('"') if card_info else ""

                    card_titles[card_id] = title
                    cards_data.append({
                        "objectType": ObjectType.CARD.value,
                        "cardId": card_id,
                    })
                    card_meanings.append(
                        f"{title} : {meaning}"
                    )

                await self.notifications.notify_session(session_id, EventType.MESSAGE.value, {"messages": cards_data})

                combo_meanings: list[str] = []
                for i in range(len(chosen_ids)):
                    for j in range(i + 1, len(chosen_ids)):
                        id1, id2 = chosen_ids[i], chosen_ids[j]
                        combo = await CardGraphRepository.get_combination(id1, id2)
                        if combo:
                            combo_meanings.append(
                                f"{card_titles[id1]} + {card_titles[id2]}: {combo}")
                system_prompt = get_system_prompt(theme=theme, tone=tone.value)
                combo_block = (
                    f"\nСочетания карт: {'; '.join(combo_meanings)}"
                    if combo_meanings else ""
                )
                llm_messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Вопрос: {user_question}\n"
                            f"Карты: {', '.join(card_meanings)}"
                            f"{combo_block}"
                        ),
                    },
                ]
                prediction = await self.llm_client(messages=llm_messages)
                logger.info(f"Session with id {session_id} prediction: {prediction}")
                message_id = uuid.uuid7()
                await MessageRepository.create(
                    message_id=message_id,
                    session_id=session_id,
                    role=MessageRoleType.ASSISTANT,
                    content=prediction,
                )
                await self.notifications.notify_session(session_id, EventType.MESSAGE.value, {
                    "messages": [{"objectType": ObjectType.MESSAGE.value,"message_id": str(message_id)}]})
                logger.info(f"Session with id {session_id} completed")
                await SessionRepository.update_state(
                    session_id=session_id,
                    status=SessionStatusType.DONE,
                )
                await self.notifications.notify_session(session_id, EventType.DONE.value, {"done": 1})
            except Exception as e:
                error = {
                    "errorType": e.__class__.__name__,
                    "userMessage": str(e)
                }
                logger.exception(f"Error in prediction pipeline: {str(e)}")
                try:
                    await SessionRepository.update_state(
                        session_id=session_id,
                        status=SessionStatusType.FAILED,
                    )
                except Exception:  # noqa: BLE001
                    pass
                try:
                    await self.notifications.notify_session(session_id, EventType.ERROR.value, error)
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"Failed to notify: {str(exc)}")

    async def clarification_pipeline(self, session: SessionEntity, user_question: str, messages: list[MessageEntity]):
        async with session_lifespan(self.db):
            try:
                session_id = session.session_id
                await SessionRepository.update_state(
                    session_id=session_id,
                    status=SessionStatusType.IN_PROGRESS,
                )
                logger.info(f"Session with id {session_id} started clarification pipeline")
                validation = await self.ml_client.validate_message(user_question)
                if validation["decision"] == "blocked":
                    await SessionRepository.update_state(
                        session_id=session_id,
                        status=SessionStatusType.FAILED,
                    )
                    message = {"objectType": ObjectType.MESSAGE.value, "role": MessageRoleType.ASSISTANT.value,
                               "content": "Карты не могут ответить на этот вопрос. Попробуй спросить о чём-то личном"}
                    await self.notifications.notify_session(session_id, EventType.MESSAGE.value,
                                                            {"messages": [message]})
                    logger.warning(f"Session with id {session_id} blocked")
                    return
                logger.info(f"Session with id {session_id} validation result: {validation["decision"]}")

                all_card_ids = list(range(78))
                used_card_ids = list(session.prediction_cards or [])

                available = [c for c in all_card_ids if c not in used_card_ids]
                chosen_ids = random.sample(available, 1)
                await SessionRepository.update_state(
                    session_id=session_id,
                    clarification_card=chosen_ids[0],
                )
                logger.info(f"Session with id {session_id} cards: {chosen_ids}")

                cards_data = []
                card_meanings = []
                card_titles: dict[int, str] = {}

                for card_id in chosen_ids:
                    card_info = await CardGraphRepository.get_card_data(card_id)

                    title = card_info["title"].strip('"') if card_info else f"Карта {card_id}"
                    meaning = card_info["meaning"].strip('"') if card_info else ""

                    card_titles[card_id] = title
                    cards_data.append({
                        "objectType": ObjectType.CARD.value,
                        "cardId": card_id,
                    })
                    card_meanings.append(
                        f"{title} : {meaning}"
                    )

                await self.notifications.notify_session(session_id, EventType.MESSAGE.value, {"messages": cards_data})

                system_prompt = get_clarification_prompt(tone=session.tone.value)
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
                clarification = await self.llm_client(messages=llm_messages)
                logger.info(f"Session with id {session_id} clarification: {clarification}")
                message_id = uuid.uuid7()
                await MessageRepository.create(
                    message_id=message_id,
                    session_id=session_id,
                    role=MessageRoleType.ASSISTANT,
                    content=clarification,
                )
                await self.notifications.notify_session(session_id, EventType.MESSAGE.value, {
                    "messages": [{"objectType": ObjectType.MESSAGE.value, "message_id": str(message_id)}]})
                logger.info(f"Session with id {session_id} completed")
                await SessionRepository.update_state(
                    session_id=session_id,
                    status=SessionStatusType.DONE,
                )
                await self.notifications.notify_session(session_id, EventType.DONE.value, {"done": 1})
            except Exception as e:
                error = {
                    "errorType": e.__class__.__name__,
                    "userMessage": str(e)
                }
                logger.exception(f"Error in prediction pipeline: {str(e)}")
                try:
                    await SessionRepository.update_state(
                        session_id=session_id,
                        status=SessionStatusType.FAILED,
                    )
                except Exception:  # noqa: BLE001
                    pass
                try:
                    await self.notifications.notify_session(session_id, EventType.ERROR.value, error)
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"Failed to notify: {str(exc)}")
