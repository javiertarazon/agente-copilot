@echo off
set OPENCLAW_CONFIG_PATH=E:\javie\agente coplit tipo open claw con skill\.openclaw\openclaw.json
set OPENCLAW_STATE_DIR=E:\javie\agente coplit tipo open claw con skill\.openclaw\state
start "" /min "C:\Program Files\nodejs\node.exe" "E:\javie\agente coplit tipo open claw con skill\OPEN CLAW\openclaw.mjs" gateway run --port 18789
