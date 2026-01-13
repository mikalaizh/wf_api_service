from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, Optional

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .client import WorkFusionClient
from .config import MonitorConfig, MonitorStore


class MonitoringManager:
    def __init__(self, client_factory, store: MonitorStore):
        self.client_factory = client_factory
        self.store = store
        self.scheduler = AsyncIOScheduler()
        self.scheduler.configure(timezone="UTC")
        self.monitors: Dict[str, MonitorConfig] = {m.uuid: m for m in store.load()}
        self.logger = logging.getLogger(__name__)

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
        for monitor in self.monitors.values():
            self._schedule_monitor(monitor)

    def _schedule_monitor(self, monitor: MonitorConfig):
        trigger = IntervalTrigger(seconds=max(10, monitor.interval_seconds))
        self.scheduler.add_job(
            self._check_status,
            trigger=trigger,
            args=[monitor.uuid],
            id=monitor.uuid,
            replace_existing=True,
            next_run_time=datetime.utcnow(),
        )

    def add_monitor(self, uuid: str, interval_seconds: int) -> MonitorConfig:
        monitor = MonitorConfig(uuid=uuid, interval_seconds=interval_seconds)
        self.monitors[uuid] = monitor
        self._schedule_monitor(monitor)
        self._persist()
        if asyncio.get_event_loop().is_running():
            asyncio.create_task(self.check_now(uuid))
        self.logger.info("Added monitor for %s with interval %s", uuid, interval_seconds)
        return monitor

    def remove_monitor(self, uuid: str) -> None:
        if uuid in self.monitors:
            self.monitors.pop(uuid)
        if self.scheduler.get_job(uuid):
            self.scheduler.remove_job(uuid)
        self._persist()
        self.logger.info("Removed monitor for %s", uuid)

    def update_interval(self, uuid: str, interval_seconds: int) -> Optional[MonitorConfig]:
        monitor = self.monitors.get(uuid)
        if not monitor:
            return None
        monitor.interval_seconds = interval_seconds
        self._schedule_monitor(monitor)
        self._persist()
        self.logger.info("Updated monitor %s interval to %s", uuid, interval_seconds)
        return monitor

    def _persist(self):
        self.store.save(list(self.monitors.values()))

    async def _check_status(self, uuid: str) -> None:
        monitor = self.monitors.get(uuid)
        if not monitor:
            return
        client: WorkFusionClient = self.client_factory()
        try:
            payload = await client.get_definition_instances(uuid)
            instances = payload.get("content", []) if isinstance(payload, dict) else []
            self.logger.info(
                "Definition %s instances: total=%s page=%s size=%s returned=%s",
                uuid,
                payload.get("totalElements") if isinstance(payload, dict) else "unknown",
                payload.get("number") if isinstance(payload, dict) else "unknown",
                payload.get("size") if isinstance(payload, dict) else "unknown",
                len(instances),
            )
            monitor.recent_instances = [self._summarize_instance(item) for item in instances]
            latest = monitor.recent_instances[0] if monitor.recent_instances else None
            monitor.name = (
                (latest or {}).get("definition_title")
                or (latest or {}).get("title")
                or monitor.name
            )
            monitor.last_status = (latest or {}).get("status") or "no instances"
            self.logger.info("Monitor %s status update: %s", uuid, monitor.last_status)
        except Exception as exc:
            self.logger.exception("Failed to update status for %s: %s", uuid, exc)
            monitor.last_status = "error"
        finally:
            monitor.last_checked = datetime.utcnow().isoformat()
            await client.close()
            self._persist()

    async def check_now(self, uuid: str) -> Optional[MonitorConfig]:
        await self._check_status(uuid)
        return self.monitors.get(uuid)

    def serialize(self) -> Dict[str, Dict]:
        return {uuid: asdict(monitor) for uuid, monitor in self.monitors.items()}

    def _summarize_instance(self, instance: Dict) -> Dict:
        start_ms = instance.get("startDate")
        end_ms = instance.get("endDate")
        return {
            "uuid": instance.get("uuid"),
            "base_uuid": instance.get("baseUUID"),
            "definition_uuid": instance.get("definitionUUID"),
            "title": instance.get("title"),
            "definition_title": instance.get("definitionTitle"),
            "status": instance.get("businessProcessStatus") or instance.get("status"),
            "author": instance.get("author"),
            "start_date": self._format_timestamp(start_ms),
            "end_date": self._format_timestamp(end_ms),
        }

    def _format_timestamp(self, timestamp_ms: Optional[int]) -> Optional[str]:
        if timestamp_ms is None:
            return None
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
