from __future__ import annotations

from typing import Dict, Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .client import WorkFusionClient
from .config import AppConfig, MonitorStore
from .monitor import MonitoringManager

app = FastAPI(title="WorkFusion Monitor")
templates = Jinja2Templates(directory="templates")

config = AppConfig.load()
monitor_store = MonitorStore()


def get_client() -> WorkFusionClient:
    return WorkFusionClient(config)


monitoring_manager = MonitoringManager(client_factory=get_client, store=monitor_store)


@app.on_event("startup")
async def startup_event():
    monitoring_manager.start()


@app.get("/")
async def index(request: Request):
    monitors = monitoring_manager.monitors.values()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "monitors": monitors, "config": config},
    )


@app.get("/config")
async def get_config(request: Request):
    return templates.TemplateResponse(
        "config.html", {"request": request, "config": config}
    )


@app.post("/config")
async def update_config(
    request: Request,
    base_url: str = Form(...),
    api_key: str = Form(...),
):
    config.base_url = base_url.rstrip("/")
    config.api_key = api_key.strip()
    config.save()
    return RedirectResponse(url="/config", status_code=303)


@app.post("/monitor")
async def add_monitor(uuid: str = Form(...), interval_seconds: int = Form(60)):
    monitoring_manager.add_monitor(uuid, interval_seconds)
    return RedirectResponse(url="/", status_code=303)


@app.post("/monitor/{uuid}/remove")
async def remove_monitor(uuid: str):
    monitoring_manager.remove_monitor(uuid)
    return RedirectResponse(url="/", status_code=303)


@app.post("/monitor/{uuid}/interval")
async def update_interval(uuid: str, interval_seconds: int = Form(...)):
    monitor = monitoring_manager.update_interval(uuid, interval_seconds)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return RedirectResponse(url="/", status_code=303)


@app.post("/monitor/{uuid}/refresh")
async def refresh_monitor(uuid: str):
    await monitoring_manager.check_now(uuid)
    return RedirectResponse(url=f"/process/{uuid}", status_code=303)


@app.get("/process/{uuid}")
async def process_detail(request: Request, uuid: str):
    monitor = monitoring_manager.monitors.get(uuid)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return templates.TemplateResponse(
        "process.html",
        {"request": request, "monitor": monitor, "config": config},
    )


async def _perform_action(uuid: str, action):
    client = get_client()
    try:
        await action(client)
    finally:
        await client.close()
    await monitoring_manager.check_now(uuid)


@app.post("/process/{uuid}/abort")
async def abort_process(uuid: str, reason: str = Form("")):
    async def action(client: WorkFusionClient):
        await client.abort_task(uuid, reason)

    await _perform_action(uuid, action)
    return RedirectResponse(url=f"/process/{uuid}", status_code=303)


@app.post("/process/{uuid}/complete")
async def complete_process(uuid: str, variables: Optional[str] = Form("")):
    parsed_vars: Dict[str, str] = {}
    if variables:
        try:
            parsed_vars = {k: v for k, v in [pair.split("=") for pair in variables.split("&")]}
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Variables must be in key=value&key2=value2 format",
            )

    async def action(client: WorkFusionClient):
        await client.complete_task(uuid, parsed_vars)

    await _perform_action(uuid, action)
    return RedirectResponse(url=f"/process/{uuid}", status_code=303)


@app.post("/process/{uuid}/reassign")
async def reassign_process(uuid: str, assignee: str = Form(...)):
    async def action(client: WorkFusionClient):
        await client.reassign_task(uuid, assignee)

    await _perform_action(uuid, action)
    return RedirectResponse(url=f"/process/{uuid}", status_code=303)


@app.get("/process/{uuid}/variables")
async def process_variables(request: Request, uuid: str):
    client = get_client()
    variables = {}
    error = None
    try:
        variables = await client.get_task_variables(uuid)
    except Exception as exc:  # pragma: no cover - display only
        error = str(exc)
    finally:
        await client.close()
    monitor = monitoring_manager.monitors.get(uuid)
    return templates.TemplateResponse(
        "process.html",
        {
            "request": request,
            "monitor": monitor,
            "variables": variables,
            "variables_error": error,
            "config": config,
        },
    )
