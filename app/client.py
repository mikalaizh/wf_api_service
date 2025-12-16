from __future__ import annotations

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

    def _headers(self) -> dict[str, str]:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        logger.info("Outgoing %s %s", method.upper(), path)
        if "json" in kwargs:
            logger.info("Payload: %s", kwargs.get("json"))
        logger.info("SSL verify setting: %s", self.verify)
        response = await self._client.request(method, path, headers=self._headers(), **kwargs)
        logger.info("Response %s for %s %s", response.status_code, method.upper(), path)
        # Log a short preview of the body to help debug unexpected statuses
        preview = response.text[:1000]
        if preview:
            logger.info("Response body preview: %s", preview)
        response.raise_for_status()
        return response

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        response = await self._request("GET", f"/tasks/{task_id}")
        return response.json()

    async def get_task_variables(self, task_id: str) -> Dict[str, Any]:
        response = await self._request("GET", f"/tasks/{task_id}/variables")
        return response.json()

    async def complete_task(self, task_id: str, variables: Optional[dict[str, Any]] = None) -> None:
        payload: Dict[str, Any] = {"variables": variables or {}}
        await self._request("POST", f"/tasks/{task_id}/complete", json=payload)

    async def abort_task(self, task_id: str, reason: str = "") -> None:
        payload = {"reason": reason}
        await self._request("POST", f"/tasks/{task_id}/abort", json=payload)

    async def stop_task(self, task_id: str, reason: str = "") -> None:
        payload = {"reason": reason}
        await self._request("POST", f"/tasks/{task_id}/stop", json=payload)

    async def start_task(self, task_id: str) -> None:
        await self._request("POST", f"/tasks/{task_id}/start")

    async def reassign_task(self, task_id: str, assignee: str) -> None:
        payload = {"assignee": assignee}
        await self._request("PUT", f"/tasks/{task_id}/assignee", json=payload)

    async def close(self) -> None:
        await self._client.aclose()
