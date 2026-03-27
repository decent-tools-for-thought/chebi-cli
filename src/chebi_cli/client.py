from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from chebi_cli.config import AppConfig

Method = Literal["GET", "POST"]


class ChebiError(Exception):
    """Base class for tool-level errors."""


class ApiError(ChebiError):
    """HTTP-level API failure with actionable context."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ResponseParseError(ChebiError):
    """Raised when response payload cannot be parsed as expected."""


@dataclass(frozen=True)
class RawResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


class ChebiClient:
    def __init__(self, config: AppConfig) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        cookies: dict[str, str] = {}

        auth: tuple[str, str] | None = None
        if config.auth.user and config.auth.password:
            auth = (config.auth.user, config.auth.password)
        if config.auth.session_id:
            cookies["sessionid"] = config.auth.session_id

        self._http = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=headers,
            auth=auth,
            cookies=cookies,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ChebiClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(
        self,
        method: Method,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        text_body: str | None = None,
        accept: str | None = None,
        content_type: str | None = None,
    ) -> httpx.Response:
        request_headers: dict[str, str] = {}
        if accept:
            request_headers["Accept"] = accept
        if content_type:
            request_headers["Content-Type"] = content_type

        content: bytes | None = text_body.encode("utf-8") if text_body is not None else None

        try:
            normalized_path = path.lstrip("/")
            response = self._http.request(
                method,
                normalized_path,
                params=params,
                json=json_body,
                content=content,
                headers=request_headers or None,
            )
        except httpx.TimeoutException as exc:
            raise ApiError("Request timed out") from exc
        except httpx.NetworkError as exc:
            raise ApiError(f"Network error: {exc}") from exc
        except httpx.HTTPError as exc:
            raise ApiError(f"HTTP transport error: {exc}") from exc

        if response.status_code == 401:
            raise ApiError("Authentication failed (401)", status_code=401)
        if response.status_code == 403:
            raise ApiError("Access forbidden (403)", status_code=403)
        if response.status_code == 429:
            raise ApiError("Rate limited by upstream API (429)", status_code=429)
        if response.status_code >= 400:
            detail = _error_detail(response)
            raise ApiError(
                f"Upstream API returned {response.status_code}: {detail}",
                status_code=response.status_code,
            )
        return response

    def get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = self._request("GET", path, params=params, accept="application/json")
        try:
            return response.json()
        except ValueError as exc:
            raise ResponseParseError("Expected JSON response but got non-JSON payload") from exc

    def post_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> Any:
        response = self._request(
            "POST", path, params=params, json_body=body, accept="application/json"
        )
        try:
            return response.json()
        except ValueError as exc:
            raise ResponseParseError("Expected JSON response but got non-JSON payload") from exc

    def post_text(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: str,
    ) -> str:
        response = self._request(
            "POST",
            path,
            params=params,
            text_body=body,
            accept="text/plain",
            content_type="text/plain;charset=UTF-8",
        )
        return response.text

    def get_text(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        accept: str = "text/plain",
    ) -> str:
        response = self._request("GET", path, params=params, accept=accept)
        return response.text

    def get_binary(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        accept: str = "application/octet-stream",
    ) -> RawResponse:
        response = self._request("GET", path, params=params, accept=accept)
        return RawResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
        )

    def post_binary(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: str,
        accept: str,
    ) -> RawResponse:
        response = self._request(
            "POST",
            path,
            params=params,
            text_body=body,
            accept=accept,
            content_type="text/plain;charset=UTF-8",
        )
        return RawResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
        )


def _error_detail(response: httpx.Response) -> str:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or "No detail"
        return str(payload)
    text = response.text.strip()
    return text or "No detail"
