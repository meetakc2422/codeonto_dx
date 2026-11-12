# Registers every collector service and job in Task Scheduler, under the folder \Codeonto collector\.
# Run from the collector folder, as the Windows user that is logged in on the server (logins open a browser):
#     powershell -ExecutionPolicy Bypass -File windows\register_tasks.ps1            # create / update all
#     powershell -ExecutionPolicy Bypass -File windows\register_tasks.ps1 -Remove    # remove all
#     ... register_tasks.ps1 -Skip "Zomato uptime","Zomato stock-outs"                # all but these (they run elsewhere)
#     ... register_tasks.ps1 -Only "All reviews","All complaints"                      # just these
# Edit $Jobs below to change what runs and when; running the script again updates the tasks in place.
param([switch]$Remove, [string[]]$Only = @(), [string[]]$Skip = @())
$ErrorActionPreference = "Stop"

$Collector = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $Collector ".venv\Scripts\python.exe"
$Folder = "\Codeonto collector\"

# Name, arguments to run.py (or "menu_proxy.py"), and when:
#   "logon"  starts when this user logs on and keeps running (the job repeats itself, e.g. --every 15)
#   "HH:MM"  once a day at that time
$Jobs = @(
    @{ Name = "Login refresh worker";   Args = "run.py worker";                    When = "logon" },
    @{ Name = "Zomato menu proxy";      Args = "menu_proxy.py";                    When = "logon" },
    @{ Name = "Zomato uptime";          Args = "run.py zomato uptime --headless";  When = "logon" },
    @{ Name = "Zomato stock-outs";      Args = "run.py zomato stockouts --headless"; When = "logon" },
    @{ Name = "Alerts";                 Args = "run.py alerts send --every 15";    When = "logon" },
    @{ Name = "Zomato reviews";         Args = "run.py zomato reviews --headless --every 60"; When = "logon" },
    @{ Name = "Swiggy reviews";         Args = "run.py swiggy reviews --headless --every 60"; When = "logon" },
    @{ Name = "All complaints";         Args = "run.py all complaints --headless --every 60"; When = "logon" },
    @{ Name = "All logins (daily)";     Args = "run.py all session";               When = "05:30" },
    @{ Name = "All outlets";            Args = "run.py all outlets --headless";    When = "06:00" },
    @{ Name = "Zomato business";        Args = "run.py zomato business --headless"; When = "06:30" },
    @{ Name = "Swiggy business";        Args = "run.py swiggy business --headless"; When = "06:40" },
    @{ Name = "Zomato item sales";      Args = "run.py zomato item_sales --headless"; When = "06:45" },
    @{ Name = "Zomato orders";          Args = "run.py zomato orders --headless";  When = "06:15" },
    @{ Name = "Zomato timings";         Args = "run.py zomato timings --headless"; When = "07:00" },
    @{ Name = "Zomato payouts";         Args = "run.py zomato payouts --headless"; When = "12:00" },
    @{ Name = "Swiggy payouts";         Args = "run.py swiggy payouts --headless"; When = "12:05" },
    @{ Name = "All ratings";            Args = "run.py all ratings --headless";    When = "07:45" },
    @{ Name = "Google performance";     Args = "run.py google performance --headless"; When = "08:00" },
    @{ Name = "Google profile";         Args = "run.py google profile --headless"; When = "08:15" }
)

if ($Remove) {
    Get-ScheduledTask -TaskPath $Folder -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    Write-Host "Removed every task in $Folder"
    return
}
if (-not (Test-Path $Python)) { throw "No .venv yet: run windows\setup.ps1 first." }

$known = $Jobs | ForEach-Object { $_.Name }
foreach ($n in $Only + $Skip) { if ($known -notcontains $n) { throw "No job named '$n'. Names: $($known -join ', ')" } }
if ($Only.Count) { $Jobs = $Jobs | Where-Object { $Only -contains $_.Name } }
if ($Skip.Count) { $Jobs = $Jobs | Where-Object { $Skip -notcontains $_.Name } }

$User = "$env:USERDOMAIN\$env:USERNAME"
foreach ($job in $Jobs) {
    $action = New-ScheduledTaskAction -Execute $Python -Argument $job.Args -WorkingDirectory $Collector
    if ($job.When -eq "logon") {
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $User
        $limit = [TimeSpan]::Zero                      # services: no time limit
    } else {
        $trigger = New-ScheduledTaskTrigger -Daily -At $job.When
        $limit = New-TimeSpan -Hours 3                 # daily jobs: stop one that hangs
    }
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit $limit `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskPath $Folder -TaskName $job.Name -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal -Force | Out-Null
    Write-Host ("{0,-24} {1,-6} python {2}" -f $job.Name, $job.When, $job.Args)
}
Write-Host ""
Write-Host "Registered in Task Scheduler under $Folder. Start the logon services now without logging off:"
Write-Host "    Get-ScheduledTask -TaskPath '$Folder' | Where-Object { `$_.Triggers[0].CimClass.CimClassName -like '*Logon*' } | Start-ScheduledTask"
