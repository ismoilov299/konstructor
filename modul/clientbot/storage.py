from typing import Dict, Set
from datetime import datetime


class MessageStore:
    def __init__(self):
        self._processed_messages: Dict[int, Set[int]] = {}
        self._last_action_time: Dict[int, float] = {}

    def is_processed(self, user_id: int, message_id: int) -> bool:
        return message_id in self._processed_messages.get(user_id, set())

    def mark_processed(self, user_id: int, message_id: int):
        if user_id not in self._processed_messages:
            self._processed_messages[user_id] = set()
        self._processed_messages[user_id].add(message_id)

    def can_process(self, user_id: int) -> bool:
        now = datetime.now().timestamp()
        last_time = self._last_action_time.get(user_id, 0)
        if now - last_time < 1.0:
            return False
        self._last_action_time[user_id] = now
        return True


message_store = MessageStore()