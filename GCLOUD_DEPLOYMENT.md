# Google Cloud Deployment Guide (Full Project)

This guide runs the full project compute stack on Google Cloud using a single Compute Engine VM:

- FastAPI backend (`src.api.main:app`)
- Celery worker
- Redis broker/backend
- Optional frontend (build + static serve)

## 1) Why this path

For this repository, `docker-compose.yml` already defines `api`, `worker`, and `redis`. A single VM is the fastest way to run everything with minimal refactoring.

## 2) Prerequisites

On your local machine:

- Install Google Cloud CLI (`gcloud`)
- Run:

```powershell
gcloud auth login
gcloud auth application-default login
```

- Ensure this repo exists locally at your workspace path.

## 3) Quick deploy (recommended)

From the repo root, run:

```powershell
.\scripts\deploy_gcloud_vm.ps1 `
  -ProjectId "YOUR_GCP_PROJECT_ID" `
  -Zone "us-central1-a" `
  -InstanceName "poison-guard-vm" `
  -MachineType "n1-standard-8" `
  -BootDiskGb 200 `
  -UseGpu `
  -GpuType "nvidia-tesla-t4" `
  -ApiKey "CHANGE_ME_TO_A_LONG_RANDOM_VALUE" `
  -CopySource
```

What this script does:

1. Enables required GCP APIs
2. Creates a VM (optionally with GPU)
3. Opens firewall ports `8000` (API) and `3000` (frontend)
4. Installs Docker + Docker Compose plugin on VM
5. Copies this repository to the VM
6. Writes `.env` with your `API_KEY`
7. Builds and starts the compose stack
8. Optionally starts frontend static serving on port `3000`

## 4) Manual deployment commands (if you prefer)

### Create VM

```powershell
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud services enable compute.googleapis.com

gcloud compute instances create poison-guard-vm `
  --zone us-central1-a `
  --machine-type n1-standard-8 `
  --boot-disk-size 200GB `
  --image-family ubuntu-2204-lts `
  --image-project ubuntu-os-cloud `
  --tags poison-guard `
  --accelerator type=nvidia-tesla-t4,count=1 `
  --maintenance-policy TERMINATE `
  --metadata install-nvidia-driver=True
```

### Open ports

```powershell
gcloud compute firewall-rules create poison-guard-allow-web `
  --allow tcp:8000,tcp:3000 `
  --target-tags poison-guard `
  --description "Poison Guard API + frontend"
```

### Copy code and install runtime

```powershell
gcloud compute scp --recurse . poison-guard-vm:~/Mini-Project --zone us-central1-a

gcloud compute ssh poison-guard-vm --zone us-central1-a --command "sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin && sudo systemctl enable --now docker"
```

### Start stack

```powershell
gcloud compute ssh poison-guard-vm --zone us-central1-a --command "cd ~/Mini-Project && echo API_KEY=CHANGE_ME > .env && mkdir -p logs cache checkpoints results && sudo docker compose up -d --build"
```

## 5) Verify deployment

Get VM external IP:

```powershell
gcloud compute instances describe poison-guard-vm --zone us-central1-a --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

Then test:

- `http://VM_IP:8000/health`
- `http://VM_IP:8000/ready`

## 6) Frontend options

### Option A (quick): run frontend on same VM

The helper script can install Node and run:

- `npm install`
- `npm run build`
- `npx serve -s dist -l 3000`

Set frontend env before build:

- `VITE_API_URL=http://VM_IP:8000`
- `VITE_API_KEY=<same API key as backend>`

### Option B (cleaner): deploy frontend static build to Cloud Storage/Firebase Hosting

Use `frontend/dist` as artifact and point API URL to your VM/API domain.

## 7) GPU and cost notes

- If you don't need GPU initially, omit `-UseGpu` for lower cost.
- Stop VM when not in use:

```powershell
gcloud compute instances stop poison-guard-vm --zone us-central1-a
```

- Start again:

```powershell
gcloud compute instances start poison-guard-vm --zone us-central1-a
```

## 8) Production hardening checklist

- Use HTTPS load balancer + managed certificate
- Move Redis to Memorystore
- Store secrets in Secret Manager (not plain `.env`)
- Add monitoring/alerts (Cloud Monitoring)
- Restrict firewall CIDRs
