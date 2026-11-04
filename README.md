# Student Result Prediction — MLOps CI/CD and Monitoring

A containerized Student Result Prediction ML application with automated model quality checks, application tests, GitHub Container Registry (GHCR) publishing, Render deployment support, request/error logging, and Prometheus/Grafana monitoring.

## Project workflow

```text
Source code
   |
   v
GitHub Actions
   |-- Train the deterministic classroom model
   |-- Run the model quality gate
   |-- Run ML and API unit tests
   |-- Build and smoke-test the Docker image
   v
GitHub Container Registry
   |
   v
Render Web Service
   |-- / and /health
   |-- /docs and /openapi.json
   |-- /predict
   |-- /metrics
   |
   +--> Render runtime logs
   |
   +--> Prometheus --> Grafana dashboard and alert rules
```

## Application details

This repository's existing serving application uses **Flask**, not FastAPI. The practicals' logging, deployment, API documentation, and monitoring tasks have been adapted to the Flask application so the existing prediction interface and tests remain compatible.

| Item | Value |
|---|---|
| Model artifact | `student_result_model.pkl` |
| Model training script | `train_model.py` |
| Quality gate | `quality_gate.py` |
| Local default port | `5000` |
| Container image | `ghcr.io/nandagopika/student-result-ml:latest` |
| Health endpoint | `/health` |
| Interactive API docs | `/docs` |
| OpenAPI document | `/openapi.json` |
| Prometheus metrics | `/metrics` |

The workflow creates the model and `metrics.json` before building the Docker image. These generated artifacts are intentionally not committed to source control.

## Prediction request

Send a JSON POST request to `/predict`:

```json
{
  "attendance": 90,
  "internal_marks": 85,
  "assignment_marks": 88,
  "previous_score": 80
}
```

The response contains the predicted class (`PASS` or `FAIL`) and its numeric code. Missing or non-numeric fields return HTTP 400. The request ID is returned in the `X-Request-ID` response header.

## Run locally

Use Python 3.11 or later.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Generate the model artifacts expected by app.py and Dockerfile.
python train_model.py
python quality_gate.py

# Run the automated tests.
python -m unittest test_ml_pipeline.py test_app.py -v

# Start the API.
python app.py
```

Open these local URLs:

- http://127.0.0.1:5000/
- http://127.0.0.1:5000/health
- http://127.0.0.1:5000/docs
- http://127.0.0.1:5000/metrics

The Swagger UI page loads its front-end assets from the Swagger UI public CDN; the OpenAPI JSON is served by this application at `/openapi.json`.

## Docker

Run model training and the quality gate before building locally, because the Dockerfile copies the generated `student_result_model.pkl` and `metrics.json` files.

```powershell
python train_model.py
python quality_gate.py
docker build -t student-result-ml:local .
docker run --rm -p 5000:5000 --name student-result-api student-result-ml:local
```

Then test:

```powershell
curl http://localhost:5000/health
curl http://localhost:5000/metrics
```

The application binds to `0.0.0.0` and reads the port from the `PORT` environment variable. It defaults to port 5000 for local and CI use; Render can provide its own `PORT` value.

## GitHub Actions and GHCR

The `.github/workflows/docker-publish.yml` workflow runs on pushes to `main` and manual dispatch. It trains the model, checks the quality threshold, runs the unit tests, builds and smoke-tests the container, and only then publishes the tested image to GHCR.

Published image:

```text
ghcr.io/nandagopika/student-result-ml:latest
ghcr.io/nandagopika/student-result-ml:sha-<commit-sha>
```

The package visibility must allow Render to pull the image. For a private GHCR package, create a GitHub Personal Access Token (classic) with only the `read:packages` permission and add it as a registry credential in Render. Never commit or screenshot the token.

## Render deployment (Practical 10)

1. In Render, create a **Web Service** and select **Existing Image**.
2. Use `ghcr.io/nandagopika/student-result-ml:latest`.
3. Add a GHCR registry credential only when the package is private.
4. Set the health-check path to `/health`.
5. The server binds to the `PORT` environment variable supplied by the platform. The local default is 5000.
6. Deploy and wait for the service to become live.
7. Open the assigned public service URL and verify `/`, `/health`, `/docs`, `/openapi.json`, `/predict`, and `/metrics`.

After a later GHCR push, use Render's **Manual Deploy → Deploy latest reference** for an image-backed service unless an automatic deploy hook has separately been configured. Record the actual Render URL in your practical record; it is assigned by Render and cannot be inferred from the repository name.

## Logging and error tracking (Practical 11)

Application logs are written to standard output and include timestamp, log level, event, request ID, HTTP method, path, status, and request duration. Prediction events log approved feature names, not raw student records. Validation failures and inference exceptions are logged without copying the request body or secrets.

Useful log events include:

- `event=model_loaded`
- `event=http_request`
- `event=validation_error`
- `event=prediction_success`
- `event=prediction_failed`
- `event=route_not_found`

To demonstrate logging, send one valid prediction, one invalid request (for example, omit a required field), and one request to a missing route. Inspect the application output locally or the service Logs page in Render.

## Prometheus and Grafana (Practical 12)

Monitoring configuration is in the `monitoring/` directory:

```text
monitoring/
|-- prometheus.yml
|-- student_api_alerts.yml
|-- docker-compose.yml
|-- grafana/
    |-- dashboards/student-result-api.json
    |-- provisioning/datasources/prometheus.yml
    |-- provisioning/dashboards/dashboard.yml
```

### 1. Configure the Render target

Edit `monitoring/prometheus.yml` and replace `YOUR-RENDER-SERVICE.onrender.com` with the hostname assigned to your Render service. Do not include `https://` in the target entry.

### 2. Start the monitoring stack

In PowerShell, from the repository root:

```powershell
$env:GRAFANA_ADMIN_PASSWORD = "choose-a-strong-local-password"
docker compose -f monitoring/docker-compose.yml up -d
```

For Bash:

```bash
export GRAFANA_ADMIN_PASSWORD='choose-a-strong-local-password'
docker compose -f monitoring/docker-compose.yml up -d
```

### 3. Verify Prometheus

- Prometheus: http://localhost:9090
- Targets: http://localhost:9090/targets

The `student-result-api` target should show **UP**. If it is DOWN, first open the Render `/metrics` URL directly and check the hostname and Render service status.

### 4. Open Grafana

- Grafana: http://localhost:3000
- Username: `admin` unless `GRAFANA_ADMIN_USER` is changed.
- Password: the `GRAFANA_ADMIN_PASSWORD` environment value used to start Compose.

The Prometheus data source and the Student Result Prediction dashboard are provisioned automatically. Open the **MLOps Monitoring** folder and select **Student Result Prediction API**.

### 5. Useful PromQL queries

```promql
sum(rate(student_api_http_requests_total[1m]))
sum(rate(student_api_http_requests_total{status=~"4..|5.."}[5m]))
sum(student_api_predictions_total{result="success"})
sum(student_api_predictions_total{result="error"})
student_api_model_loaded
up{job="student-result-api"}
histogram_quantile(0.95, sum by (le) (rate(student_api_http_request_duration_seconds_bucket[5m])))
```

The alert rules cover repeated 4xx responses, 5xx responses, and a failed scrape target. Model readiness is displayed separately in the Grafana dashboard. Prometheus evaluates and displays alert states; notification delivery requires a separately configured Alertmanager/receiver.

### 6. Stop the local monitoring stack

```powershell
docker compose -f monitoring/docker-compose.yml down
```

Add `-v` only when you also want to delete the local Prometheus and Grafana data volumes.

## Important notes

- Do not retrain or replace the model just to add logging or monitoring.
- Keep the input feature names and order consistent with the existing model pipeline.
- Do not log student names, registration numbers, raw request bodies, passwords, tokens, or other sensitive information.
- The API currently uses HTTP 400 for invalid/missing prediction fields, matching the repository's Flask API contract and existing tests. The supplied practical handout describes FastAPI's HTTP 422 behavior; that status code is not used by this Flask implementation.
- The Render URL, GHCR package visibility/credential, and live cloud deployment status must be confirmed in the corresponding accounts; they are not stored in this repository.
