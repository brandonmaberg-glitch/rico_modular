from core.base_skill import BaseSkill


class ConversationSkill(BaseSkill):
    """
    Lightweight wrapper for conversation handling.
    The actual memory-aware conversation logic lives in run_rico._conversation_with_memory().
    """

    def __init__(self, name: str, description: str, handler):
        super().__init__(name, description)
        self.handler = handler

    def run(self, query: str, **kwargs):
        # Delegate to the memory-aware handler provided by run_rico
        return self.handler(query)
