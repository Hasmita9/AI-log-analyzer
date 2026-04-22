# ============================================================
#  AI Log Analyzer - Full API Test Script (PowerShell)
#  Run this from anywhere while your Flask server is running
# ============================================================

$BASE = "http://127.0.0.1:5000"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  AI LOG ANALYZER - API TEST SUITE" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ── STEP 1: Create a project ──────────────────────────────
Write-Host "STEP 1: Creating a test project..." -ForegroundColor Yellow

$project = Invoke-RestMethod `
    -Uri "$BASE/api/projects" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"name": "My Test App", "description": "Testing real log data"}'

Write-Host "✅ Project created!" -ForegroundColor Green
Write-Host "   API Key: $($project.api_key)`n"

$API_KEY = $project.api_key


# ── STEP 2: List all projects ─────────────────────────────
Write-Host "STEP 2: Listing all projects..." -ForegroundColor Yellow

$projects = Invoke-RestMethod -Uri "$BASE/api/projects" -Method GET
Write-Host "✅ Total projects: $($projects.Count)`n" -ForegroundColor Green


# ── STEP 3: Send realistic test logs ─────────────────────
Write-Host "STEP 3: Sending test logs (mixed levels)..." -ForegroundColor Yellow

$logs = @{
    logs = @(
        # --- Plain text logs ---
        "2024-01-15 10:00:01 ERROR Database connection failed: timeout after 30s"
        "2024-01-15 10:00:02 ERROR NullPointerException in UserService.getUser() at line 42"
        "2024-01-15 10:00:03 WARN  Retry attempt 3/5 for payment gateway"
        "2024-01-15 10:00:04 ERROR Database connection failed: timeout after 30s"
        "2024-01-15 10:00:05 INFO  Server started on port 8080"
        "2024-01-15 10:00:06 ERROR Authentication failed for user admin@test.com"
        "2024-01-15 10:00:07 ERROR Database connection failed: timeout after 30s"
        "2024-01-15 10:00:08 WARN  Memory usage at 87%, approaching limit"
        "2024-01-15 10:00:09 ERROR Unhandled exception: segfault in worker process"
        "2024-01-15 10:00:10 ERROR Payment service unavailable after 3 retries"
        "2024-01-15 10:00:11 FATAL Application crashed: out of memory"
        "2024-01-15 10:00:12 WARN  Slow query detected: 4200ms for getUserOrders()"
        "2024-01-15 10:00:13 ERROR NullPointerException in UserService.getUser() at line 42"
        "2024-01-15 10:00:14 ERROR Redis connection refused on localhost:6379"
        "2024-01-15 10:00:15 INFO  Cache cleared successfully"

        # --- JSON format logs ---
        '{"timestamp":"2024-01-15T10:01:00Z","level":"ERROR","message":"JWT token validation failed","service":"auth-service"}'
        '{"timestamp":"2024-01-15T10:01:01Z","level":"ERROR","message":"Disk write error: no space left on device","service":"storage-service"}'
        '{"timestamp":"2024-01-15T10:01:02Z","level":"WARN","message":"API rate limit approaching: 950/1000","service":"api-gateway"}'
        '{"timestamp":"2024-01-15T10:01:03Z","level":"ERROR","message":"JWT token validation failed","service":"auth-service"}'
        '{"timestamp":"2024-01-15T10:01:04Z","level":"INFO","message":"Deployment completed successfully","service":"deploy-service"}'
    )
} | ConvertTo-Json -Depth 3

$ingestResult = Invoke-RestMethod `
    -Uri "$BASE/api/ingest" `
    -Method POST `
    -ContentType "application/json" `
    -Headers @{ "X-API-Key" = $API_KEY } `
    -Body $logs

Write-Host "✅ Logs ingested: $($ingestResult.count) logs accepted`n" -ForegroundColor Green


# ── STEP 4: Get the project ID ────────────────────────────
Write-Host "STEP 4: Fetching project ID..." -ForegroundColor Yellow

$allProjects = Invoke-RestMethod -Uri "$BASE/api/projects" -Method GET
$projectId = ($allProjects | Where-Object { $_.api_key -eq $API_KEY }).id

Write-Host "✅ Project ID: $projectId`n" -ForegroundColor Green


# ── STEP 5: View detected errors ─────────────────────────
Write-Host "STEP 5: Viewing detected errors..." -ForegroundColor Yellow

$errors = Invoke-RestMethod -Uri "$BASE/api/projects/$projectId/errors" -Method GET

Write-Host "✅ Errors detected: $($errors.Count)" -ForegroundColor Green
$errors | ForEach-Object {
    $color = switch ($_.severity) {
        "Critical" { "Red" }
        "High"     { "DarkYellow" }
        "Medium"   { "Yellow" }
        default    { "Gray" }
    }
    Write-Host "   [$($_.severity)] (x$($_.count)) $($_.message)" -ForegroundColor $color
}
Write-Host ""


# ── STEP 6: Generate AI insights ─────────────────────────
Write-Host "STEP 6: Generating AI insights (calls Gemini)..." -ForegroundColor Yellow
Write-Host "   This may take a few seconds..." -ForegroundColor Gray

try {
    $insight = Invoke-RestMethod `
        -Uri "$BASE/api/projects/$projectId/insights/generate" `
        -Method POST `
        -ContentType "application/json"

    Write-Host "✅ AI Insight generated!`n" -ForegroundColor Green
    Write-Host "--- SUMMARY (first 300 chars) ---" -ForegroundColor Cyan
    Write-Host ($insight.summary.Substring(0, [Math]::Min(300, $insight.summary.Length)) + "...`n")
} catch {
    Write-Host "⚠️  AI insight failed (check your GEMINI_API_KEY in .env)`n" -ForegroundColor DarkYellow
}


# ── STEP 7: Fetch saved insights ─────────────────────────
Write-Host "STEP 7: Fetching saved insights from DB..." -ForegroundColor Yellow

$savedInsight = Invoke-RestMethod -Uri "$BASE/api/projects/$projectId/insights" -Method GET

if ($savedInsight.summary) {
    Write-Host "✅ Insights found in DB, created at: $($savedInsight.created_at)`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  No insights saved yet`n" -ForegroundColor DarkYellow
}


# ── DONE ─────────────────────────────────────────────────
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ALL TESTS COMPLETE " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nOpen your browser at: http://127.0.0.1:5000" -ForegroundColor White
Write-Host "Your project ID is  : $projectId" -ForegroundColor White
Write-Host "Your API key is     : $API_KEY`n" -ForegroundColor White
