"""
Shared response envelope schemas.

Per Appendix B of the API design doc, every endpoint across
the whole API (not just Authentication) returns a standard
envelope on success:

    {
        "success": true,
        "message": "...",
        "data": {...},
        "meta": {...}
    }

`data` holds whatever the endpoint's actual payload is (a
token pair, a user profile, or nothing for a plain
confirmation message). `meta` is for pagination info on list
endpoints — none of the current endpoints paginate, so it's
always omitted (None) for now, but the field exists so list
endpoints in later modules don't need a different envelope
shape.

The matching error envelope is NOT a schema here — it's built
directly as a dict in app/core/exception_handlers.py, since
FastAPI exception handlers return a JSONResponse rather than
going through a route's response_model/Pydantic validation.
"""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class SuccessResponse(BaseModel, Generic[DataT]):
    """
    Standard success envelope.

    Usage:
        SuccessResponse[UserResponse](message="...", data=user)
        SuccessResponse[None](message="...")  # no data to return
    """

    success: bool = True
    message: str
    data: Optional[DataT] = None
    meta: Optional[dict] = None