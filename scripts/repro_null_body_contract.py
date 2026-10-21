"""Isolated reproduction of /v1/verify JSON-null validation across dependency versions.

This script intentionally does not import the project, read fixtures, or mutate files.
It compares the v0.4.0 typed-body route with the v0.5.0 Any/Body + manual
Pydantic validation route using a synthetic request model.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import fastapi
import pydantic
from fastapi import Body, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, ValidationError


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claims: list[str]


def v040_style_app() -> FastAPI:
    app = FastAPI()

    @app.post("/v1/verify")
    def verify(request: VerificationRequest) -> dict[str, bool]:
        return {"ok": bool(request.claims)}

    return app


def v050_style_app() -> FastAPI:
    app = FastAPI()

    @app.post("/v1/verify")
    def verify(payload: Annotated[Any, Body()]) -> dict[str, bool]:
        if payload is None:
            # Match the current API guard that preserves the frozen r1-a null-body contract.
            raise RequestValidationError(
                [
                    {
                        "type": "missing",
                        "loc": ("body",),
                        "msg": "Field required",
                        "input": None,
                    }
                ],
                body=payload,
            )
        version = payload.get("schema_version", "r1-a") if isinstance(payload, dict) else "r1-a"
        if version == "r2-a":
            return {"ok": True}
        try:
            request = VerificationRequest.model_validate(payload, from_attributes=True)
        except ValidationError as exc:
            errors = [
                {
                    **{key: value for key, value in error.items() if key != "url"},
                    "loc": ("body", *error["loc"]),
                }
                for error in exc.errors()
            ]
            raise RequestValidationError(errors, body=payload) from exc
        return {"ok": bool(request.claims)}

    return app


def main() -> int:
    print(f"FastAPI={fastapi.__version__} Pydantic={pydantic.__version__}")
    for name, app in (
        ("v0.4.0-style", v040_style_app()),
        ("v0.5.0-style", v050_style_app()),
    ):
        response = TestClient(app).post(
            "/v1/verify",
            content="null",
            headers={"content-type": "application/json"},
        )
        body = response.json()
        detail = body.get("detail", [{}])[0]
        error_type = detail.get("type", "<no-validation-error>")
        print(
            f"{name}: status={response.status_code} "
            f"type={error_type} "
            f"loc={json.dumps(detail.get('loc', []), ensure_ascii=False)}"
        )
        if name == "v0.5.0-style" and (
            response.status_code != 422 or error_type != "missing"
        ):
            raise AssertionError("v0.5.0-style must preserve HTTP 422 type=missing for JSON null")
    try:
        VerificationRequest.model_validate(None, from_attributes=True)
    except ValidationError as exc:
        print(f"pydantic-from-attributes-null: type={exc.errors()[0]['type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
