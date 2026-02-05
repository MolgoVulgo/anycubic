# Processus d'impression (extrait des logs)

Ce document décrit le flux observé **depuis la sélection d'un fichier jusqu'au lancement de l'impression**, en listant les **requêtes HTTP (GET/POST)** visibles dans `docs/logs`.

## 1) Sélection du fichier (liste des fichiers)

- **HTTP POST**  
  `/p/p/workbench/api/work/index/userFiles`  
  Retourne la liste des fichiers avec `id` (file_id) et `gcode_id`, ex :  
  - `old_filename: cat_skull-grand_5_v4.pwmb` → `id=49777814`, `gcode_id=69368651`
  - `old_filename: T3d_skull_10_50_v3.pwmb` → `id=30553490`, `gcode_id=44306216`
  
  (Vu dans `docs/logs/cloud_Log.log`.)

## 2) Envoi de la commande d'impression (HTTP)

La commande d'impression observée est un **POST form-data** vers :

```
POST /p/p/workbench/api/work/operation/sendOrder
```

Payload (vu dans `docs/logs/cloud_Log.log`, format URL-encoded) :

```
data=%7B%22file_id%22%3A%2230553490%22%2C%22matrix%22%3A%22%22%2C%22filetype%22%3A0%2C%22project_type%22%3A1%2C%22template_id%22%3A-2074360784%7D
&is_delete_file=0
&order_id=1
&printer_id=42859
&project_id=0
```

Décodé :

```json
{
  "printer_id": 42859,
  "project_id": 0,
  "order_id": 1,
  "is_delete_file": 0,
  "data": {
    "file_id": "30553490",
    "matrix": "",
    "filetype": 0,
    "project_type": 1,
    "template_id": -2074360784
  }
}
```

**Correspondance application :**
- `file_id` = ID du fichier cloud
- `printer_id` = imprimante cible
- `order_id=1` (commande “start”)
- `project_id=0` (non utilisé ici)
- `is_delete_file=0` (ne pas supprimer après impression)

**Important :**  
Le champ `file_id` est **le modèle cloud** (ex: `30553490`).  

## 3) Retour serveur / création de tâche

Après `sendOrder`, les logs montrent :

- **HTTP GET**
  `/p/p/workbench/api/work/project/getProjects?limit=10&page=1&print_status=1&printer_id=42859`
  - Retourne un **taskid** et le **gcode_id** en cours

- **HTTP GET**
  `/p/p/workbench/api/v2/printer/info?id=42859`
  - Retourne l’état de l’imprimante et le projet en cours

Dans `docs/logs/application_Log.log`, on voit également :

- `printStart` → `fileId = 30553490`
- `ctrlPrint` → `order = 1`
- `onCtrlPrinterResult` → `taskId = 70271310`


## 5) Résumé de la “commande” d’impression

La **commande d’impression** que l’on peut extraire des logs est :

```
POST /p/p/workbench/api/work/operation/sendOrder
```

avec le form-data suivant :

```
printer_id=<id>
project_id=0
order_id=1
is_delete_file=0
data={"file_id":"<file_id>","matrix":"","filetype":0,"project_type":1,"template_id":-2074360784}
```

Le suivi s’effectue ensuite par :

- `GET /work/project/getProjects` (tâche + gcode_id + status)
- `GET /v2/printer/info` (état machine)
