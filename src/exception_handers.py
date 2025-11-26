from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.response import ResponseStructure


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    errors = []

    for err in exc.errors():
        print(err)
        loc = ".".join(str(x) for x in err["loc"] if x != "body")
        errors.append({"field": loc or None, "message": err["msg"]})

    return JSONResponse(
        status_code=422,
        content={
            "status": 422,
            "message": "Validation failed",
            "errors": errors,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    content = ResponseStructure(
        status=exc.status_code, message=exc.detail, data=None
    ).model_dump()
    return JSONResponse(content=content, status_code=exc.status_code)
