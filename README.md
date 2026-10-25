# Lightweight FastAPI on Compute Engine

Python 3.12 recommended. No database, Docker, or cloud SDK dependency inside the application. Exactly three application endpoints; FastAPI also supplies /docs, /redoc and /openapi.json.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | / | Welcome response |
| GET | /health | Process liveness and UTC timestamp |
| POST | /echo | Validate and return a message and character count |

Echo strips surrounding whitespace, rejects empty or over-1000-character messages and unknown fields with HTTP 422. Health indicates process liveness only.

## Run locally

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000/docs.

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/echo \
  -H 'Content-Type: application/json' -d '{"message":"Hello GCP"}'
```

The echo response is `{"message":"Hello GCP","length":9}`.

## Deploy on GCP Compute Engine

Prerequisites: a project with billing, Compute Engine API enabled, gcloud CLI authenticated, and permissions to create VMs and firewall rules. Commands create billable resources. This example assumes an existing default VPC/subnet with SSH access. For a custom VPC specify its network/subnet on VM creation and the same network on the firewall rule.

### 1. Create an Ubuntu VM

Run from your computer or Cloud Shell. Replace YOUR_PROJECT_ID; choose a zone suited to you.

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable compute.googleapis.com
gcloud compute instances create fastapi-vm \
  --zone=asia-south1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --network=default \
  --tags=fastapi-demo \
  --boot-disk-size=10GB \
  --no-service-account --no-scopes
```

### 2. Copy this project and connect

Run from the parent directory containing `fastapi-gce`. Copy before creating a local .venv, or remove/exclude it from the upload.

```bash
gcloud compute scp --recurse fastapi-gce fastapi-vm:~/ --zone=asia-south1-a
gcloud compute ssh fastapi-vm --zone=asia-south1-a
```

### 3. Install and start (inside the VM)

Use a fresh project directory at /opt/fastapi-gce for the initial install.

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
sudo useradd --system --user-group --no-create-home --shell /usr/sbin/nologin fastapi
sudo mkdir -p /opt/fastapi-gce
sudo cp -r ~/fastapi-gce/. /opt/fastapi-gce/
sudo python3 -m venv /opt/fastapi-gce/.venv
sudo /opt/fastapi-gce/.venv/bin/pip install -r /opt/fastapi-gce/requirements.txt
sudo chown -R root:root /opt/fastapi-gce
sudo chmod -R a+rX /opt/fastapi-gce
sudo cp /opt/fastapi-gce/deploy/fastapi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fastapi
curl --fail http://127.0.0.1:8000/health
```

The service runs as an unprivileged account, starts on boot and restarts on failure. One worker keeps memory usage small. No reload flag is used on the VM.

### 4. Permit access to port 8000

Back on your computer/Cloud Shell, replace YOUR_PUBLIC_IP with your actual public IPv4 address. This allows only your address to reach the tagged VM. Add other client CIDRs as needed.

```bash
gcloud compute firewall-rules create allow-fastapi-demo \
  --network=default --direction=INGRESS --allow=tcp:8000 \
  --source-ranges=YOUR_PUBLIC_IP/32 --target-tags=fastapi-demo
gcloud compute instances describe fastapi-vm --zone=asia-south1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

Use the returned EXTERNAL_IP:

```bash
curl --fail http://EXTERNAL_IP:8000/health
curl -X POST http://EXTERNAL_IP:8000/echo \
  -H 'Content-Type: application/json' -d '{"message":"Hello GCP"}'
```

Swagger UI: http://EXTERNAL_IP:8000/docs. An ephemeral external IP may change after stopping/starting the VM; reserve a static address if a stable endpoint is needed.

This is a small HTTP demo with no authentication. Before accepting sensitive traffic or opening access to all internet clients, add HTTPS using a reverse proxy or an HTTPS load balancer and any required authentication. Keep port 8000 private when using a proxy. If UFW is enabled, it must also allow the chosen source/port.

### Logs and updates

```bash
sudo systemctl status fastapi --no-pager
sudo journalctl -u fastapi -n 100 --no-pager
sudo systemctl restart fastapi
```

After changing code or installing dependencies, restart the service. Requirements use compatible ranges rather than a fully pinned lockfile; record a tested environment with `pip freeze` before reproducible deployments.

### Clean up (on your computer/Cloud Shell)

```bash
gcloud compute instances delete fastapi-vm --zone=asia-south1-a
gcloud compute firewall-rules delete allow-fastapi-demo
```

Remove separately reserved IPs or other resources if you created them.

## References

- https://fastapi.tiangolo.com/deployment/manually/
- https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create
- https://docs.cloud.google.com/sdk/gcloud/reference/compute/firewall-rules/create
