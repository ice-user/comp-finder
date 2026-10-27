@echo off
rem Starts the dashboard in the background (no window). Tailscale serve forwards to it.
cd /d "%~dp0"
start "" pythonw server.py
