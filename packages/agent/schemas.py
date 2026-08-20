from pydantic import BaseModel, Field


class Subtask(BaseModel):
    type: str
    description: str = ""
    params: dict = Field(default_factory=dict)


class Plan(BaseModel):
    subtasks: list[Subtask] = Field(default_factory=list)


class CriticVerdict(BaseModel):
    passed: bool
    reason: str = ""
    should_replan: bool = False
