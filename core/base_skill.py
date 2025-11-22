class BaseSkill:
    """Base class for skills.

    Attributes:
        name: A short identifier for the skill.
        description: A human-readable description of the skill.
    """

    name: str = ""
    description: str = ""

    def run(self, *args, **kwargs):
        """Execute the skill.

        Subclasses should override this method to provide functionality.
        """
        raise NotImplementedError("Subclasses must implement the run method")
