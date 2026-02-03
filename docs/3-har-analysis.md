# 3 — Analyse du HAR (cloud-universe.anycubic.com)

Ce document résume les endpoints observés dans `docs/uc.makeronline.com.har`.
Les valeurs sensibles (cookies, URLs signées) sont volontairement omises.

## 3.1 Vue d’ensemble

Host API principal : `https://cloud-universe.anycubic.com`

Flux global observé :

1. Flux d’authentification interne -> session (détails sensibles omis)
2. Login applicatif -> session
3. Calls API : quota, listing, infos, download, upload, delete
4. Upload réel via URL S3 signée

## 3.2 Auth / session

Les détails de l’authentification sont volontairement omis.

**Note**: Dans le HAR, les appels suivants ne montraient pas d’`Authorization` explicite.
La session semble établie côté serveur (probablement cookie + état serveur).

## 3.3 Quota

- `POST /p/p/workbench/api/work/index/getUserStore`
- Réponse : `used_bytes`, `total_bytes`, `used`, `total`

## 3.4 Listing fichiers

- `POST /p/p/workbench/api/work/index/files`
- Body JSON (exemple) : `{ "page": 1, "limit": 10 }`
- Réponse : array d’objets fichier

Champs observés (extraits) :

- `id`, `old_filename`, `filename`, `size`, `time`
- `md5`, `file_extension`, `file_type`
- `url` (CDN), `thumbnail` (S3)
- `gcode_id` (utilisé par la page Details)
- `bucket`, `region`, `path`

## 3.5 Détails fichier (gcode)

- `GET /p/p/workbench/api/api/work/gcode/info?id=<gcode_id>`
- Réponse : objet gcode (paramètres slicing, machine, matériau, etc.)

`gcode_id` est obtenu après upload via `getUploadStatus` **ou** directement depuis le listing `files`.

## 3.6 Download

- `POST /p/p/workbench/api/work/index/getDowdLoadUrl`
- Body JSON : `{ "id": <file_id> }`
- Réponse : URL signée S3 (GET direct)

## 3.7 Upload (multi-étapes)

1. **Lock storage**
   - `POST /p/p/workbench/api/v2/cloud_storage/lockStorageSpace`
   - Body JSON : `{ "name": "<filename>", "size": <bytes>, "is_temp_file": 0 }`
   - Réponse : `data.preSignUrl` (PUT signé) + `data.id` (lock_id)

2. **PUT S3**
   - `PUT <preSignUrl>`
   - Body : bytes du fichier

3. **Register upload**
   - `POST /p/p/workbench/api/v2/profile/newUploadFile`
   - Body JSON : `{ "user_lock_space_id": <lock_id> }`
   - Réponse : `data.id` (file_id)

4. **Get upload status**
   - `POST /p/p/workbench/api/work/index/getUploadStatus`
   - Body JSON : `{ "id": <file_id> }`
   - Réponse : `data.gcode_id`

5. **Unlock storage**
   - `POST /p/p/workbench/api/v2/cloud_storage/unlockStorageSpace`
   - Body JSON : `{ "id": <lock_id>, "is_delete_cos": 0 }`

## 3.8 Delete / rename

- Delete : `POST /p/p/workbench/api/work/index/delFiles`
  - Body JSON : `{ "idArr": [<file_id>] }`
- Rename : `POST /p/p/workbench/api/work/index/renameFile`
  - Body JSON : `{ "id": <file_id>, "name": "<new_name>" }`

## 3.9 Headers observés

Commun :
- `Accept: application/json, text/plain, */*`
- `Origin: https://cloud-universe.anycubic.com`
- `Referer: https://cloud-universe.anycubic.com/file` (ou `fileDetail`)
- `User-Agent: <browser>`

JSON :
- `Content-Type: application/json`

## 3.10 Fichiers générés

- `api_map.json` : mapping structuré des endpoints
- `endpoints.py` : constantes Python pour l’implémentation
