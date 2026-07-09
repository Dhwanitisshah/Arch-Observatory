$base = "http://localhost:8000"

Write-Host "`n--- happy path ---" -ForegroundColor Cyan
$r = Invoke-RestMethod -Method Post -Uri "$base/analyze" -ContentType "application/json" -Body '{"url":"https://github.com/psf/requests"}'
$r
Write-Host "polling..." -ForegroundColor Cyan
do {
  Start-Sleep -Seconds 2
  $run = Invoke-RestMethod -Uri "$base/runs/$($r.run_id)"
  Write-Host "status = $($run.status)"
} while ($run.status -in @("pending","running"))
$run | ConvertTo-Json -Depth 4

Write-Host "`n--- phase 3: dependency graph summary ---" -ForegroundColor Cyan
Write-Host "modules = $($run.dependency_nodes.Count), edges = $($run.dependency_edges.Count)"
Write-Host "scc_count (cyclic clusters) = $($run.scc_count)"
Write-Host "most_depended_on (top ca):"
$run.most_depended_on | ForEach-Object { Write-Host "  $($_.module)  ca=$($_.ca)" }
Write-Host "most_unstable (I>0.7, ce>0):"
$run.most_unstable | ForEach-Object { Write-Host "  $($_.module)  I=$($_.instability)  ce=$($_.ce)" }

Write-Host "`n--- health + top smells ---" -ForegroundColor Cyan
Write-Host "health score: $($run.health_score)"
$run.smell_counts
$run.smells | Select-Object -First 8 | Format-Table type, severity, target, title

Write-Host "`n--- rejection tests (all should error 400) ---" -ForegroundColor Cyan
foreach ($bad in @('{"url":"http://github.com/a/b"}','{"url":"https://evil.com/a/b"}','{"url":"https://github.com/a/b/c/d"}')) {
  try { Invoke-RestMethod -Method Post -Uri "$base/analyze" -ContentType "application/json" -Body $bad; Write-Host "NOT REJECTED: $bad" -ForegroundColor Red }
  catch { Write-Host "rejected ok: $bad" -ForegroundColor Green }
}

Write-Host "`n--- temp cleanup (should be empty) ---" -ForegroundColor Cyan
Get-ChildItem $env:TEMP -Filter "archobs*"
