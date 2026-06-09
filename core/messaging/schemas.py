"""Message schema definitions for persona dialogue.

Defines: dissent, observation, alternative, confirmation messages.
All messages are JSON with timestamp, author, and audit trail fields.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List

@dataclass
class PersonaMessage:
    """Base message class."""
    from_persona: str
    to_personas: List[str]  # can broadcast to multiple
    msg_type: str  # 'dissent' | 'observation' | 'alternative' | 'confirmation'
    content: str
    timestamp: str
    requires_ack: bool = False
    message_id: Optional[str] = None
    context: Optional[dict] = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def dissent(cls, from_persona: str, to_personas: List[str], concern: str, context: dict = None):
        """Create a dissent message (requires acknowledgment)."""
        return cls(
            from_persona=from_persona,
            to_personas=to_personas,
            msg_type="dissent",
            content=concern,
            timestamp=datetime.now(timezone.utc).isoformat(),
            requires_ack=True,  # Critical messages need ack
            context=context or {}
        )

    @classmethod
    def observation(cls, from_persona: str, to_personas: List[str], note: str, context: dict = None):
        """Create an observation message (no ack required)."""
        return cls(
            from_persona=from_persona,
            to_personas=to_personas,
            msg_type="observation",
            content=note,
            timestamp=datetime.now(timezone.utc).isoformat(),
            requires_ack=False,
            context=context or {}
        )

    @classmethod
    def alternative(cls, from_persona: str, to_personas: List[str], proposal: str, context: dict = None):
        """Create an alternative/proposal message."""
        return cls(
            from_persona=from_persona,
            to_personas=to_personas,
            msg_type="alternative",
            content=proposal,
            timestamp=datetime.now(timezone.utc).isoformat(),
            requires_ack=False,
            context=context or {}
        )

    @classmethod
    def confirmation(cls, from_persona: str, decision_id: str, vote: bool):
        """Create a confirmation/vote message."""
        return cls(
            from_persona=from_persona,
            to_personas=["system"],  # goes to audit log
            msg_type="confirmation",
            content=f"Decision {decision_id}: {'approved' if vote else 'rejected'}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            requires_ack=False,
            context={"decision_id": decision_id, "vote": vote}
        )
