from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

from .config import AppConfig


class WorkFusionClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self._client = httpx.AsyncClient(base_url=config.base_url.rstrip("/"))

    def _headers(self) -> dict[str, str]:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        response = await self._client.get(f"/tasks/{task_id}", headers=self._headers())
        response.raise_for_status()
        return response.json()

    async def get_task_variables(self, task_id: str) -> Dict[str, Any]:
        response = await self._client.get(
            f"/tasks/{task_id}/variables", headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    async def complete_task(self, task_id: str, variables: Optional[dict[str, Any]] = None) -> None:
        payload: Dict[str, Any] = {"variables": variables or {}}
        response = await self._client.post(
            f"/tasks/{task_id}/complete", json=payload, headers=self._headers()
        )
        response.raise_for_status()

    async def abort_task(self, task_id: str, reason: str = "") -> None:
        payload = {"reason": reason}
        response = await self._client.post(
            f"/tasks/{task_id}/abort", json=payload, headers=self._headers()
        )
        response.raise_for_status()

    async def stop_task(self, task_id: str, reason: str = "") -> None:
        payload = {"reason": reason}
        response = await self._client.post(
            f"/tasks/{task_id}/stop", json=payload, headers=self._headers()
        )
        response.raise_for_status()

    async def start_task(self, task_id: str) -> None:
        response = await self._client.post(
            f"/tasks/{task_id}/start", headers=self._headers()
        )
        response.raise_for_status()

    async def reassign_task(self, task_id: str, assignee: str) -> None:
        payload = {"assignee": assignee}
        response = await self._client.put(
            f"/tasks/{task_id}/assignee", json=payload, headers=self._headers()
        )
        response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()
