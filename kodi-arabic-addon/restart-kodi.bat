@echo off
REM Kodi Restart Script - kills Kodi, waits, then relaunches it
REM Uses schtasks to launch Kodi in the interactive user session (works over SSH)
REM Usage: restart-kodi.bat

echo Restarting Kodi...

REM Kill Kodi if running
taskkill /im kodi.exe /f 2>nul
if %ERRORLEVEL%==0 (
    echo Kodi killed. Waiting 3 seconds...
    ping 127.0.0.1 -n 4 >nul 2>&1
) else (
    echo Kodi was not running.
)

REM Create a one-shot scheduled task that runs in the interactive session
REM This launches Kodi in the user's desktop session, not the SSH session
echo Creating launch task...
schtasks /create /tn "KodiRestart" /tr "\"C:\Program Files\Kodi\kodi.exe\"" /sc once /st 00:00 /f >nul 2>&1
schtasks /run /tn "KodiRestart" >nul 2>&1
echo Kodi launch task triggered.

REM Wait for web server to come up
echo Waiting for Kodi web server...
set /a attempts=0
:waitloop
set /a attempts+=1
ping 127.0.0.1 -n 3 >nul 2>&1
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8080/jsonrpc' -Method POST -Headers @{'Authorization'='Basic a29kaTprb2Rp';'Content-Type'='application/json'} -Body '{\"jsonrpc\":\"2.0\",\"method\":\"JSONRPC.Ping\",\"id\":1}' -TimeoutSec 5 -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" 2>nul
if %ERRORLEVEL%==0 (
    echo Kodi web server is up! (attempt %attempts%)
    REM Clean up the task
    schtasks /delete /tn "KodiRestart" /f >nul 2>&1
    exit /b 0
)
if %attempts% LSS 20 (
    goto waitloop
)
echo WARNING: Kodi web server did not respond after %attempts% attempts.
echo Kodi may still be starting. Check the TV screen.
schtasks /delete /tn "KodiRestart" /f >nul 2>&1
exit /b 1