@ECHO OFF
SETLOCAL

:: Read port from port.txt
set PORT=
if exist "port.txt" (
    for /f "usebackq delims=" %%x in ("port.txt") do set PORT=%%x
)

:: Validate port
if "%PORT%"=="" (
    echo [ERROR] port.txt not found or empty
    pause
    exit /b 1
)

:LOOP
ECHO [INFO] Starting WireMock on port %PORT%...
ECHO.

title WireMock - Port %PORT%

REM Run WireMock with all regulated parameters
java -Xmx4G -Xms2G -server ^
-XX:+UseG1GC ^
-XX:+ExplicitGCInvokesConcurrent ^
-XX:MaxGCPauseMillis=500 ^
-jar wiremock-jre8-standalone-2.35.0.jar ^
--global-response-templating=true ^
--jetty-acceptor-threads=3000 ^
--container-threads=4000 ^
--async-response-enabled=true ^
--async-response-threads=2000 ^
--no-request-journal ^
--disable-request-logging ^
--port %PORT% ^
--verbose

ECHO.
CHOICE /C RQ /M "WireMock stopped. Press R to restart or Q to quit"

IF ERRORLEVEL 2 GOTO END
IF ERRORLEVEL 1 GOTO LOOP

:END
EXIT