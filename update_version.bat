@echo off
REM Auto-update VERSION file with current timestamp (YYYYMMDDHHMMSS format)
REM Run this script before each git commit

echo Updating VERSION file with current timestamp...

REM Get current date and time in YYYYMMDDHHMMSS format
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set version=%datetime:~0,4%%datetime:~4,2%%datetime:~6,2%%datetime:~8,2%%datetime:~10,2%%datetime:~12,2%

REM Write version to VERSION file
echo %version% > VERSION

echo VERSION file updated to: %version%
echo.
echo You can now commit your changes with the new version number.
