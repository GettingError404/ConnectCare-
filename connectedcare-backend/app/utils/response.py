from typing import Any, Generic, TypeVar
from pydantic import BaseModel


T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    success: bool = True
    data: Any | None = None
    error: str | None = None
