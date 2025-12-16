from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

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
        )

    def add_monitor(self, uuid: str, interval_seconds: int) -> MonitorConfig:
        monitor = MonitorConfig(uuid=uuid, interval_seconds=interval_seconds)
        self.monitors[uuid] = monitor
        self._schedule_monitor(monitor)
        self._persist()
        return monitor

    def remove_monitor(self, uuid: str) -> None:
        if uuid in self.monitors:
            self.monitors.pop(uuid)
        if self.scheduler.get_job(uuid):
            self.scheduler.remove_job(uuid)
        self._persist()

    def update_interval(self, uuid: str, interval_seconds: int) -> Optional[MonitorConfig]:
        monitor = self.monitors.get(uuid)
        if not monitor:
            return None
        monitor.interval_seconds = interval_seconds
        self._schedule_monitor(monitor)
        self._persist()
        return monitor

    def _persist(self):
        self.store.save(list(self.monitors.values()))

    async def _check_status(self, uuid: str) -> None:
        monitor = self.monitors.get(uuid)
        if not monitor:
            return
        client: WorkFusionClient = self.client_factory()
        try:
            payload = await client.get_task(uuid)
            monitor.last_status = payload.get("status") or payload.get("state") or "unknown"
        except Exception:
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
