"""Standard API response envelope (Part 5 §57). Every endpoint returns one
of these — clients never have to guess the response shape.

Every route sets `response_model=SuccessResponse[X]` and returns a
`SuccessResponse(message=..., data=...)` — that keeps the OpenAPI schema
accurate (Part 5 §64 requires documented response schemas per endpoint,
which a generic response-wrapping middleware would hide). Failures never
go through routes at all: `app/main.py`'s exception handlers build
`ErrorResponse` for every raised exception.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from flames_shared.enums import ErrorCode
from pydantic import BaseModel, Field

# Plain Generic/TypeVar rather than PEP 695 syntax — see base_repository.py.
T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: ErrorCode
    detail: str


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T
    meta: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: list[ErrorDetail]
