from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ResponseStructure(BaseModel):
    status: int
    message: str
    data: Any


class ApiResponse(JSONResponse):
    def __init__(self, content: Any, status_code: int = 200, *args, **kwargs):
        message = ""
        data = content if status_code < 400 else None

        if status_code >= 400:
            if isinstance(content, dict):
                message = content.get("detail") or content.get("message") or "Error"
            else:
                message = str(content)

        payload = ResponseStructure(status=status_code, data=data, message=message).model_dump()
        super().__init__(content=payload, status_code=status_code, *args, **kwargs)
