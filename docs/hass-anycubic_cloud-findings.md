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
