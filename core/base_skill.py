class BaseSkill:
    """
    Base class for all skills.
    Accepts optional name and description so that skills may either:
    - pass explicit metadata, OR
    - rely on defaults for auto-loaded skills.
    """

    def __init__(self, name: str = None, description: str = None):
        self.name = name or self.__class__.__name__
        self.description = description or "No description provided."
