# Output schema for Stage 2. This is the contract downstream code consumes.
# Field descriptions go to the model with structured outputs; they are not comments.
# Optional fields stay optional so missing owners or dates are not invented as "".
# Priority is an enum so free-form urgency words cannot leak into the JSON.

from enum import StrEnum

from pydantic import BaseModel, Field


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class Task(BaseModel):
    title: str = Field(description="One actionable item, short and specific.")
    owner: str | None = Field(
        default=None,
        description="Person responsible, if the notes name one.",
    )
    due: str | None = Field(
        default=None,
        description="Due date or time phrase from the notes, otherwise null.",
    )
    priority: Priority = Field(
        default=Priority.medium,
        description="high only when the notes mark urgency; otherwise medium or low.",
    )


class MeetingTasks(BaseModel):
    meeting_title: str | None = Field(
        default=None,
        description="Meeting topic if it is clear; otherwise null.",
    )
    tasks: list[Task] = Field(
        description="Action items found in the notes. Empty if there are none.",
    )
