from enum import Enum


class ArcanaType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"


class ToneType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SessionStatusType(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class SessionStageType(str, Enum):
    PREDICTION = "prediction"
    CLARIFICATION = "clarification"


class ThemeType(str, Enum):
    CAREER = "career"
    LOVE = "love"
    SELF = "self"
    SOCIAL = "social"
    OTHER = "other"
    HEALTH = "health"


class MessageRoleType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class UIThemeType(str, Enum):
    PINK = "pink"
    GOLD = "gold"