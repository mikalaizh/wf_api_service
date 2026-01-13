from __future__ import annotations

import asyncio
import httpx
import logging
from typing import Any, Dict, Optional

from .config import AppConfig


logger = logging.getLogger(__name__)


class WorkFusionClient:
    def __init__(self, config: AppConfig):
        self.config = config
        verify: Optional[bool | str] = config.verify_ssl
        if config.ca_bundle:
            verify = config.ca_bundle
        self.verify = verify
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"), verify=self.verify
        )
        self._csrf_token: Optional[str] = None
        self._csrf_header_name: Optional[str] = None
        self._login_lock = asyncio.Lock()

    async def _login(self) -> None:
        if not self.config.username or not self.config.password:
            raise ValueError("WorkFusion username/password are required")
        payload = {
            "j_username": self.config.username,
            "j_password": self.config.password,
        }
        logger.info("Authenticating with WorkFusion form login")
        response = await self._client.post(
            "/dologin",
            params=payload,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        self._csrf_token = data.get("csrfToken")
        self._csrf_header_name = data.get("csrfHeaderName")
        if not self._csrf_token or not self._csrf_header_name:
            raise ValueError("Login response missing CSRF token details")
        logger.info(
            "Login successful. CSRF header: %s, token length: %s, cookies: %s",
            self._csrf_header_name,
            len(self._csrf_token),
            list(self._client.cookies.keys()),
        )

    async def _ensure_session(self) -> None:
        if not self._csrf_token or not self._csrf_header_name:
            async with self._login_lock:
                if not self._csrf_token or not self._csrf_header_name:
                    await self._login()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if self._csrf_header_name and self._csrf_token:
            headers[self._csrf_header_name] = self._csrf_token
        return headers

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        logger.info("Outgoing %s %s", method.upper(), path)
        base_headers = self._headers()
        extra_headers = dict(kwargs.pop("headers", {}) or {})
        if "json" in kwargs:
            logger.info("Payload: %s", kwargs.get("json"))
            base_headers.pop("Content-Type", None)
        base_headers.update(extra_headers)
        logger.info("SSL verify setting: %s", self.verify)
        await self._ensure_session()
        response = await self._client.request(method, path, headers=base_headers, **kwargs)
        if response.status_code in {401, 403}:
            logger.info("Session expired, re-authenticating")
            await self._login()
            base_headers = self._headers()
            if "json" in kwargs:
                base_headers.pop("Content-Type", None)
            base_headers.update(extra_headers)
            response = await self._client.request(method, path, headers=base_headers, **kwargs)
        logger.info("Response %s for %s %s", response.status_code, method.upper(), path)
        logger.info("Response URL: %s", response.request.url)
        # Log a short preview of the body to help debug unexpected statuses
        preview = response.text[:1000]
        if preview:
            logger.info("Response body preview: %s", preview)
        response.raise_for_status()
        return response

    async def get_definition_instances(
        self,
        definition_uuid: str,
        page: int = 0,
        size: int = 10,
        sort: str = "START_DATE",
        sort_direction: str = "ASC",
    ) -> Dict[str, Any]:
        params = {
            "page": page,
            "size": size,
            "sort": sort,
            "sortDirection": sort_direction,
        }
        response = await self._request(
            "GET",
            f"/v1/definitions/{definition_uuid}/instances",
            params=params,
        )
        return response.json()

    async def start_bp(self, bp_uuid: str) -> None:
        await self._request("POST", f"/v1/bp-instances/{bp_uuid}/start")

    async def stop_bp(self, bp_uuid: str, reason: str = "") -> None:
        payload = {"reason": reason} if reason else None
        kwargs = {"json": payload} if payload else {}
        await self._request("POST", f"/v1/bp-instances/{bp_uuid}/stop", **kwargs)

    async def close(self) -> None:
        await self._client.aclose()
