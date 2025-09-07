# Stops the Agent Brain process (agent_main.py) and its child PowerShell if launched by our shortcut.

Write-Host "Stopping Agent Brain…" -ForegroundColor Cyan

# 1) Try to stop the exact python that launched agent_main.py
$procs = Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'python.exe' -or $_.Name -match 'py.exe') -and
  ($_.CommandLine -match 'agent_main\.py')
}

if ($procs) {
  foreach ($p in $procs) {
    try {
      Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
      Write-Host "Stopped python (PID $($p.ProcessId))" -ForegroundColor Green
    } catch {
      Write-Warning "Failed to stop python (PID $($p.ProcessId)): $_"
    }
  }
} else {
  Write-Host "No agent_main.py processes found." -ForegroundColor Yellow
}

# 2) Optional: close the PowerShell window that launched the agent via our shortcut
#    (looks for a PowerShell that has -File scripts\start_agent.ps1 in its command line)
$launchers = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'powershell.exe' -and ($_.CommandLine -match 'scripts\\start_agent\.ps1')
}
foreach ($p in $launchers) {
  try {
    Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
    Write-Host "Closed launcher PowerShell (PID $($p.ProcessId))" -ForegroundColor Green
  } catch {
    Write-Warning "Failed to close launcher (PID $($p.ProcessId)): $_"
  }
}

Write-Host "Done." -ForegroundColor Cyan
