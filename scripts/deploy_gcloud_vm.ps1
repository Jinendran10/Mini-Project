param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Zone = "us-central1-a",
    [string]$InstanceName = "poison-guard-vm",
    [string]$MachineType = "n1-standard-8",
    [int]$BootDiskGb = 200,

    [switch]$UseGpu,
    [string]$GpuType = "nvidia-tesla-t4",

    [string]$ApiKey = "change_me_in_production",

    [string]$SourcePath = ".",
    [switch]$CopySource,
    [switch]$SetupFrontend
)

$ErrorActionPreference = "Stop"
$gcloud = "gcloud.cmd"

Write-Host "[1/7] Setting active GCP project..." -ForegroundColor Cyan
& $gcloud config set project $ProjectId | Out-Host

Write-Host "[2/7] Enabling required APIs..." -ForegroundColor Cyan
& $gcloud services enable compute.googleapis.com | Out-Host

Write-Host "[3/7] Creating VM if it does not exist..." -ForegroundColor Cyan
$existing = & $gcloud compute instances list --filter="name=('$InstanceName') AND zone:('$Zone')" --format="value(name)"

if (-not $existing) {
    $createArgs = @(
        "compute", "instances", "create", $InstanceName,
        "--zone", $Zone,
        "--machine-type", $MachineType,
        "--boot-disk-size", "${BootDiskGb}GB",
        "--image-family", "ubuntu-2204-lts",
        "--image-project", "ubuntu-os-cloud",
        "--tags", "poison-guard"
    )

    if ($UseGpu) {
        $createArgs += @(
            "--accelerator", "type=$GpuType,count=1",
            "--maintenance-policy", "TERMINATE",
            "--metadata", "install-nvidia-driver=True"
        )
    }

    & $gcloud @createArgs | Out-Host
}
else {
    Write-Host "VM already exists: $InstanceName" -ForegroundColor Yellow
}

Write-Host "[4/7] Creating firewall rule for ports 8000/3000 (if missing)..." -ForegroundColor Cyan
$fwName = "poison-guard-allow-web"
$fwExists = & $gcloud compute firewall-rules list --filter="name=('$fwName')" --format="value(name)"
if (-not $fwExists) {
    & $gcloud compute firewall-rules create $fwName `
        --allow tcp:8000,tcp:3000 `
        --target-tags poison-guard `
        --description "Poison Guard API + frontend" | Out-Host
}
else {
    Write-Host "Firewall rule already exists: $fwName" -ForegroundColor Yellow
}

Write-Host "[5/7] Installing Docker + Compose plugin on VM..." -ForegroundColor Cyan
$installCmd = @"
sudo apt-get update &&
sudo apt-get install -y docker.io docker-compose-plugin curl git &&
sudo systemctl enable --now docker
"@
& $gcloud compute ssh $InstanceName --zone $Zone --command $installCmd | Out-Host

if ($CopySource) {
    Write-Host "[6/7] Copying repository to VM (this can take time)..." -ForegroundColor Cyan
    & $gcloud compute scp --recurse $SourcePath "$InstanceName`:~/Mini-Project" --zone $Zone | Out-Host
}
else {
    Write-Host "[6/7] Skipping source copy. Ensure code exists at ~/Mini-Project on VM." -ForegroundColor Yellow
}

Write-Host "[7/7] Starting Docker Compose stack..." -ForegroundColor Cyan
$runCmd = @"
set -e
cd ~/Mini-Project
printf "API_KEY=$ApiKey\n" > .env
mkdir -p logs cache checkpoints results
sudo docker compose down || true
sudo docker compose up -d --build
"@
& $gcloud compute ssh $InstanceName --zone $Zone --command $runCmd | Out-Host

if ($SetupFrontend) {
    Write-Host "Setting up frontend static server on port 3000..." -ForegroundColor Cyan
    $frontendCmd = @"
set -e
cd ~/Mini-Project/frontend
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
echo "VITE_API_URL=http://127.0.0.1:8000" > .env.production
echo "VITE_API_KEY=$ApiKey" >> .env.production
npm install
npm run build
sudo npm install -g serve
nohup serve -s dist -l 3000 >/tmp/frontend.log 2>&1 &
"@
    & $gcloud compute ssh $InstanceName --zone $Zone --command $frontendCmd | Out-Host
}

$ip = & $gcloud compute instances describe $InstanceName --zone $Zone --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "API health: http://$ip`:8000/health" -ForegroundColor Green

if ($SetupFrontend) {
    Write-Host "Frontend: http://$ip`:3000" -ForegroundColor Green
}
