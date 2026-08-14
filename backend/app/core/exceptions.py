"""Application-level exception + the standardized error codes it carries
(Part 5 §63). Routes/services raise `FlamesAPIError` when they need a
specific error code; the global handler in app/main.py catches it (plus
FastAPI's own HTTPException/RequestValidationError) and always responds
with the ErrorResponse envelope — never a raw stack trace.
"""

from __future__ import annotations

from flames_shared.enums import ErrorCode


class FlamesAPIError(Exception):
    def __init__(self, status_code: int, error_code: ErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)
