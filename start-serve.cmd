@echo off
rem Hidden opencode worker launcher. Run by Task Scheduler (no window ever).
rem Edit the two SET lines below, then lock this file to your user only.
cd /d "%~dp0"
set OPENCODE_SERVER_USERNAME=opencode
set OPENCODE_SERVER_PASSWORD=REPLACE-ME-WITH-A-STRONG-PASSWORD
opencode serve --port 4096 --hostname 0.0.0.0 >> "%~dp0serve.log" 2>&1
