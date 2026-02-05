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
