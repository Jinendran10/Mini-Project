# Test JIE Detection API
# Quick smoke test to verify API is working

Write-Host "=== JIE API Smoke Test ===" -ForegroundColor Cyan

# Load API key from .env
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^API_KEY=(.+)$') {
            $API_KEY = $matches[1]
        }
    }
}

if (-not $API_KEY) {
    Write-Host "❌ API_KEY not found in .env" -ForegroundColor Red
    exit 1
}

$BASE_URL = "http://localhost:8000"

# Test 1: Health check
Write-Host "`n1. Testing /health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/health" -Method Get
    Write-Host "✓ Health check passed: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Readiness check
Write-Host "`n2. Testing /ready..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/ready" -Method Get
    Write-Host "✓ Readiness check passed: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Readiness check failed (checkpoints may be missing): $_" -ForegroundColor Yellow
}

# Test 3: Detection (sync mode)
Write-Host "`n3. Testing /api/detect (sync mode)..." -ForegroundColor Yellow
$headers = @{
    "X-API-Key" = $API_KEY
    "Content-Type" = "application/json"
}

$body = @{
    samples = @(
        @{
            sample_id = "test1"
            text = "This is a test training sample."
        }
    )
    target_samples = @(
        @{
            sample_id = "target1"
            text = "This is a test target prompt."
        }
    )
    mode = "sync"
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/detect" -Method Post -Headers $headers -Body $body
    Write-Host "✓ Detection completed in $($response.processing_time_ms)ms" -ForegroundColor Green
    Write-Host "  Results: $($response.results.Count) samples processed" -ForegroundColor Cyan
    
    foreach ($result in $response.results) {
        Write-Host "  - Sample $($result.sample_id): JIE=$($result.jie_score), Weight=$($result.mitigation_weight)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Detection failed: $_" -ForegroundColor Red
    Write-Host "  This is expected if checkpoints are not configured" -ForegroundColor Yellow
}

# Test 4: Detection (async mode)
Write-Host "`n4. Testing /api/detect (async mode)..." -ForegroundColor Yellow
$body = @{
    samples = @(
        @{
            sample_id = "test1"
            text = "This is a test training sample."
        }
    )
    target_samples = @(
        @{
            sample_id = "target1"
            text = "This is a test target prompt."
        }
    )
    mode = "async"
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/api/detect" -Method Post -Headers $headers -Body $body
    $job_id = $response.job_id
    Write-Host "✓ Job queued: $job_id" -ForegroundColor Green
    
    # Poll for result
    Write-Host "  Polling for result..." -ForegroundColor Yellow
    $max_retries = 12
    $retry = 0
    
    while ($retry -lt $max_retries) {
        Start-Sleep -Seconds 5
        $status = Invoke-RestMethod -Uri "$BASE_URL/api/jobs/$job_id" -Method Get -Headers $headers
        
        Write-Host "  Status: $($status.status), Progress: $($status.progress)%" -ForegroundColor Cyan
        
        if ($status.status -eq "completed") {
            Write-Host "✓ Async job completed!" -ForegroundColor Green
            Write-Host "  Results: $($status.results.Count) samples" -ForegroundColor Cyan
            break
        } elseif ($status.status -eq "failed") {
            Write-Host "❌ Job failed: $($status.error)" -ForegroundColor Red
            break
        }
        
        $retry++
    }
    
    if ($retry -eq $max_retries) {
        Write-Host "⚠️  Job did not complete within timeout" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Async detection failed: $_" -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
