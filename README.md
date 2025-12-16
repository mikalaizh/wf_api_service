# WorkFusion Task Monitor

A FastAPI-based web UI to configure credentials, monitor WorkFusion task UUIDs, and perform basic task actions (check status, abort, reassign, complete, and view variables) using the Task Management API.

## Features
- Configuration tab to set the WorkFusion API base URL and bearer token.
- Dashboard to add UUIDs to monitor and adjust their polling interval.
- Background scheduler to poll task status at the configured cadence per UUID.
- Process detail page with common actions mapped to Task Management endpoints: refresh status, start/stop, view variables, complete with variables, abort with a reason, and reassign to a different user.

## Getting started

### Prerequisites
- Python 3.11+

### Installation
1. Create and activate a virtual environment.
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies.
   ```bash
   pip install -r requirements.txt
   ```

### Running locally (IDE or terminal)
1. Ensure the `data/` directory is writable; configuration and monitors are stored there.
2. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```
3. Open http://127.0.0.1:8000 in your browser. Use the **Configuration** tab to set your WorkFusion API base URL (e.g., `https://<host>/workfusion/api`) and API key. These values are saved to `data/config.json`.
4. Add process UUIDs on the dashboard, set the polling interval, and use the process page to abort, reassign, complete, or load variables.

### Notes
- Polling is performed per UUID using APScheduler; minimum interval is 10 seconds.
- Variables for completion can be provided as `key=value&key2=value2` and are sent as a variables map in the completion payload.
- The UI uses bearer token authentication (Authorization: Bearer <token>) for outbound calls.

### TLS / SSL
- Outbound requests validate the server certificate by default. If you encounter `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate`, the WorkFusion endpoint is likely using a certificate issued by a custom corporate CA that is missing from your system trust store.
- You can provide a path to a custom CA bundle or temporarily disable verification on the **Configuration** page. Disabling verification should only be used for testing.
