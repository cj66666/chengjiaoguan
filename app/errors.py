from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            payload = detail
        else:
            payload = {"code": str(exc.status_code), "message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": payload})


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})

