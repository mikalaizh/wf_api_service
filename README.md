# WorkFusion Task Monitor

A FastAPI-based web UI to configure credentials, monitor WorkFusion Business Process UUIDs, and perform basic start/stop actions using the WorkFusion REST API.

## Features
- Configuration tab to set the WorkFusion API base URL and Control Tower credentials.
- Dashboard to add Business Process definition UUIDs to monitor and adjust their polling interval.
- Background scheduler to poll task status at the configured cadence per UUID.
- Process detail page with actions mapped to Business Process endpoints: refresh status and start/stop.

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
3. Open http://127.0.0.1:8000 in your browser. Use the **Configuration** tab to set your WorkFusion API base URL (e.g., `https://<host>/workfusion/api`) and Control Tower credentials. These values are saved to `data/config.json`.
4. Add Business Process definition UUIDs on the dashboard, set the polling interval, and use the process page to refresh status and view recent instances.

### Notes
- Polling is performed per UUID using APScheduler; minimum interval is 10 seconds.
- The UI uses WorkFusion form-based authentication and includes the CSRF token returned by the login endpoint on each request.

### TLS / SSL
- Outbound requests validate the server certificate by default. If you encounter `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate`, the WorkFusion endpoint is likely using a certificate issued by a custom corporate CA that is missing from your system trust store.
- You can provide a path to a custom CA bundle or temporarily disable verification on the **Configuration** page. Disabling verification should only be used for testing.
