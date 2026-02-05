# Anycubic Cloud GUI (Python)

## English

### Overview
A lightweight desktop GUI that interacts with Anycubic Cloud using the same API calls as the web UI. The app focuses on file management, printer/job visibility, MQTT log tailing, and print order submission (when a valid session is available).

### Key Features
- Import session from a HAR file (browser capture)
- File list with thumbnails, size, and date
- File details view with slicing parameters
- Upload / Download / Delete files
- Printer view with current job summary and task list
- MQTT log tail (local log file)
- Send print order
- Centralized in-app log tab (no CLI required)

### Requirements
- Python 3.10+
- Packages listed in `requirements.txt`

### Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run
```bash
python -m accloud.gui
```

### Authentication (HAR Import)
The app uses a session created from a HAR file exported from your browser.

Steps:
1) Open `https://cloud-universe.anycubic.com` in your browser
2) Log in
3) Open DevTools → Network
4) Refresh the page
5) Right click the list → **Save all as HAR**
6) In the app: menu **Connection → Import HAR** and select the file

The session is saved locally to `.accloud/session.json` (ignored by git).

### UI Tabs
- **Files**: list, upload, download, delete, and file info window
- **Printer**: printer selection + job summary + task list
- **MQTT**: tail of local MQTT log file (if available)
- **Print**: manual print order form + result log
- **LOG**: application logs

### Project Structure
```
accloud/
  api.py          # high-level API calls
  client.py       # HTTP client + auth/session
  gui.py          # desktop GUI
  models.py       # dataclasses
  session_store.py# session import/export
  utils.py        # helpers

docs/
  print_flow.md           # print flow analysis
  api_endpoints.yaml      # endpoint inventory
  ui/                     # UI specs
```

### Security / Privacy
- Do not commit HAR, logs, or session files.
- `.gitignore` already excludes local secrets and logs.
- Avoid sharing cookies, headers, or signed URLs.

### Troubleshooting
- If API calls fail, re-import a fresh HAR session.
- Ensure you are logged in in the browser before exporting HAR.
- MQTT tab depends on local log file existence.
- `accloud_http.log` rotates daily and keeps 7 days of `.tar.gz` archives.

---

## Français

### Aperçu
Une GUI desktop légère qui interagit avec le cloud Anycubic via les mêmes appels API que la web UI. L’app se concentre sur la gestion des fichiers, la visibilité des jobs, le suivi MQTT, et l’envoi de commandes d’impression (avec session valide).

### Fonctionnalités principales
- Import de session via HAR (capture navigateur)
- Liste des fichiers avec thumbnails, taille, date
- Fenêtre “File Details” avec paramètres de slicing
- Upload / Download / Delete
- Vue imprimantes + résumé job + task list
- Lecture (tail) des logs MQTT locaux
- Envoi d’ordre d’impression
- Logs centralisés dans l’onglet LOG (pas de CLI)

### Prérequis
- Python 3.10+
- Dépendances listées dans `requirements.txt`

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Lancement
```bash
python -m accloud.gui
```

### Authentification (Import HAR)
La session est créée à partir d’un HAR exporté depuis le navigateur.

Étapes :
1) Ouvrir `https://cloud-universe.anycubic.com`
2) Se connecter
3) Ouvrir DevTools → Network
4) Recharger la page
5) Clic droit → **Save all as HAR**
6) Dans l’app : menu **Connection → Import HAR**

La session est sauvegardée localement dans `.accloud/session.json` (ignoré par git).

### Onglets UI
- **Files** : liste, upload, download, delete, détails fichier
- **Printer** : sélection imprimante + résumé job + task list
- **MQTT** : lecture des logs MQTT locaux (si présents)
- **Print** : formulaire d’impression + log
- **LOG** : logs applicatifs

### Structure du projet
```
accloud/
  api.py
  client.py
  gui.py
  models.py
  session_store.py
  utils.py

docs/
  print_flow.md
  api_endpoints.yaml
  ui/
```

### Sécurité / confidentialité
- Ne pas versionner les HAR, logs, sessions.
- `.gitignore` couvre déjà les fichiers sensibles locaux.
- Ne jamais partager cookies, headers ou URLs signées.

### Dépannage
- Si les appels échouent, réimporter un HAR récent.
- Vérifier que la session navigateur est valide avant l’export.
- L’onglet MQTT dépend de la présence des logs locaux.
- `accloud_http.log` est journalier et conserve 7 jours d’archives `.tar.gz`.
