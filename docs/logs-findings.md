# Logs — endpoints utiles (extraits)

Source : `docs/logs/*.log`

## Base API

- `https://cloud-universe.anycubic.com/p/p/workbench/api`

## Printer (v2)

- `GET /p/p/workbench/api/v2/printer/info?id=<printer_id>`
  - Exemple vu : `id=42859`
  - Réponse : objet riche (machine_data, firmware, status, etc.)

## Printers list

- `GET /p/p/workbench/api/work/printer/getPrinters?limit=1000&page=1&type=LCD`

## Fichiers (listing)

- `POST /p/p/workbench/api/work/index/userFiles`
  - Réponse : liste de fichiers avec `thumbnail`, `gcode_id`, etc.

## Projects / jobs

- `GET /p/p/workbench/api/work/project/getProjects?limit=10&page=1&print_status=1&printer_id=<printer_id>`
- `GET /p/p/workbench/api/v2/project/info?id=<project_id>`

## Messages

- `GET /p/p/workbench/api/v2/message/getMessageCount?`
- `POST /p/p/workbench/api/v2/message/getMessages`

## Messages

- `GET /p/p/workbench/api/v2/message/getMessageCount?`
- `POST /p/p/workbench/api/v2/message/getMessages`

## Projets / impressions

- `GET /p/p/workbench/api/work/project/report?id=<task_id>`
- `GET /p/p/workbench/api/v2/project/printHistory?limit=50&page=1&printer_id=<printer_id>`

## QR / App download

- `https://cdn.cloud-universe.anycubic.com/application/android.png`
- `https://cdn.cloud-universe.anycubic.com/application/ios.png`

## OAuth / Auth

- `https://uc.makeronline.com/login/oauth/authorize`
- `https://uc.makeronline.com/api/logout`

## Download service

- `https://api.makeronline.com/file/fileService/download`

## Environnement

- `https://workbentch.s3.us-east-2.amazonaws.com/workshop/environment.ini`

## MQTT

- `mqtt.anycubic.com:8883` (CN)
- `mqtt-universe.anycubic.com:8883` (EN)

### MQTT observations (cloud_Log.log)

- Client ID seen: `pc_eddf9dc9ece959c70ffb8fae7d76bbf1`.
- Payloads are truncated in logs (single-line prefix only), so full JSON bodies are not available.
- Inbound PUBLISH payload types observed:
  - `{"type":"lastWill", ...}` (payload len 180) around `2026-02-02 11:17:06`.
  - `{"type":"status", ...}` (payload len 159) around `2026-02-02 11:17:06` and `2026-02-02 11:18:33`.
  - `{"type":"print", ...}` (payload len 525) repeated at `11:18:34`, `11:19:06`, `11:19:37`, `11:20:07`, `11:20:38`, `11:21:08`, `11:21:39`, `11:22:09`, `11:22:18`.
- Each inbound message is followed by an outbound publish with a small `{"msgid":"..."}` payload (len 49), likely an ACK/receipt.
- No explicit MQTT topics appear in logs (no `SUBSCRIBE`/`topic=` lines).
