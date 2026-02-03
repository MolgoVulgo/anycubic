# hass-anycubic_cloud — Infos utiles

Source : `hass-anycubic_cloud/custom_components/anycubic_cloud/anycubic_cloud_api/*`

## Endpoints HTTP (base `/p/p/workbench/api`)

- Authentification : détails omis
- Fichiers:
  - `POST /work/index/files`
  - `POST /work/index/getUserStore`
  - `POST /work/index/delFiles`
- Imprimantes:
  - `GET /work/printer/getPrinters`
  - `GET /work/printer/printersStatus`
  - `GET /v2/printer/info`
  - `GET /v2/printer/status`
  - `GET /v2/printer/functions`
  - `GET /v2/printer/tool`
  - `GET /v2/printer/all`
- Projets:
  - `GET /work/project/getProjects`
  - `GET /v2/project/info`
  - `GET /v2/project/monitor`
  - `GET /v2/project/printHistory`

**Important (print)**  
Le composant HA utilise :  
`POST /work/operation/sendOrder`  
et non `.../work/send_order`.

## MQTT (structure + topics)

Host/port :
- `mqtt-universe.anycubic.com:8883`

Topic prefix :
- `anycubic/anycubicCloud/v1`

Topics observés (const/mqtt.py) :
- Subscribe printer:
  - `anycubic/anycubicCloud/v1/printer/app/<machine_type>/<device_id>/#`
  - `anycubic/anycubicCloud/v1/+/public/<machine_type>/<device_id>/#`
- Publish printer:
  - `anycubic/anycubicCloud/v1/printer/public/<machine_type>/<device_id>/<endpoint>`
- User topics:
  - `anycubic/anycubicCloud/v1/server/app/<user_id>/<user_id_md5>/slice/report`
  - `anycubic/anycubicCloud/v1/server/app/<user_id>/<user_id_md5>/fdmslice/report`
- Slicer hint:
  - `anycubic/anycubicCloud/v1/pc/printer/<machine_type>/<device_id>/#`

## MQTT Payloads (types gérés)

Le parser MQTT gère des types/états :
- `status`, `print`, `download`, `checking`
- `temperature`, `fan`
- `ota_printer`, `ota_multicolorbox`
- `multicolorbox`, `shelves`, `file`, `peripherals`

Source :
- `anycubic_cloud_api/api/mqtt.py`
- `anycubic_cloud_api/data_models/printer.py`
