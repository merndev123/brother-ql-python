# Brother QL Label Printer (FastAPI)

This repository provides a small FastAPI app that generates a PNG label and sends it to a Brother QL printer using `brother-ql`.

Files:
- `app.py` — FastAPI app with POST /print endpoint.
- `requirements.txt` — Python dependencies.
- `Procfile` — for Railway deployment.
- `render.yaml` — sample Render service config.

Environment variables
- `PRINTER` (required) — e.g. `tcp://192.0.2.10:9100` (printer reachable by the host).
- `MODEL` (optional) — Brother model, default `QL-1060N`.
- `LABEL` (optional) — label type, default `102x152`.

Quick local test

1. Create a virtualenv and install deps:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. Run locally:

```powershell
$env:PRINTER = "tcp://50.191.67.238:9100"; uvicorn app:app --reload
```

3. Send a print request:

```powershell
curl -X POST "http://127.0.0.1:8000/print" -H "Content-Type: application/json" -d '{"text": "Hello from cloud", "font_size": 80}'
```

Deployment notes and caveats

- Railway: add the repo, set the start command to `uvicorn app:app --host 0.0.0.0 --port $PORT` and set the `PRINTER` env var in the Railway dashboard. A `Procfile` is provided.

- Railway quick steps:

  1. Push this repo to GitHub and create a new Railway project from the repo.
  2. In Railway's Service settings set the start command (or rely on `Procfile`):
	  `uvicorn app:app --host 0.0.0.0 --port $PORT`
  3. Add the following environment variables in Railway's dashboard:
	  - `PRINTER` = `tcp://<printer-ip>:9100`
	  - (optional) `API_KEY` = a strong secret to protect the /print endpoint
	  - (optional) `MODEL` and `LABEL` if you want non-default values
  4. Deploy. Use the generated service URL and include the `x-api-key` header when calling POST /print if you set `API_KEY`.

- Render: a sample `render.yaml` is included. Deploy it or create a new Web Service, set env vars (PRINTER, MODEL, LABEL), and use the start command above.

Important network constraints

- Cloud platforms may not be able to reach a printer on your local network. If your printer is on a private LAN behind NAT, the cloud service will not reach it directly.

- Outbound port 9100 may be blocked by the host provider. Test connectivity before relying on cloud deployment.

Alternatives if direct network printing from cloud fails

- Run this service locally on a Raspberry Pi or small always-on machine on the same network as the printer.
- Use an SSH reverse tunnel from a machine on your network to the cloud host.
- Use a VPN or cloud VM with a static IP in the same network (advanced).

Security

- Don't expose printer URIs or other secrets publicly. Use platform environment variables and restrict access to the service.

If you want, I can:
- Create a Dockerfile and instructions for both platforms.
- Add authentication to the HTTP endpoint.
- Modify the app to accept file uploads or templates.
