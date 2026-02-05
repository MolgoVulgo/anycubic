# 1 — Récupérer toutes les infos (API, auth, flux)

## Objectif

Cartographier **exactement** ce que fait la web UI Anycubic (cloud-universe.anycubic.com) : endpoints, schémas JSON, auth, cookies/session, headers, mécanismes d’upload/download, quotas.

## Prérequis

* Navigateur desktop (Chrome/Chromium ou Firefox).
* Accès au compte Anycubic (login OK).
* DevTools ouverts.
* Export de session/cookies possible.

## Méthode recommandée : “écoute” via DevTools (Network)

### A. Préparer la capture

1. Ouvrir DevTools → onglet **Network**.
2. Activer :

   * **Preserve log**
   * **Disable cache**
3. Filtrer : **Fetch/XHR** (et garder un œil sur **WS** si présent).
4. Cliquer sur “Clear” (icône ⃠) pour partir d’un log vide.

### B. Capturer le scénario complet (happy path)

Effectuer dans l’UI web, dans cet ordre, pour forcer tous les appels utiles :

1. **Login** (ou refresh session si déjà loggé)
2. Accès page **File** (listing)
3. **Refresh** listing (si bouton/refresh dispo)
4. Ouvrir **Details** d’un fichier
5. Lancer un **Download**
6. Faire un **Upload** (petit fichier test)
7. **Delete** du fichier test
8. Recharger la page pour vérifier cohérence

### C. Pour chaque requête pertinente, extraire le “pack complet”

Pour chaque call lié à : list / quota / upload / download / delete / auth :

* URL complète (host + path)
* Méthode (GET/POST/PUT/DELETE)
* Query params
* Request headers (notamment : Authorization, x-*, content-type, user-agent constraints)
* Request body (JSON / multipart / form-data)
* Response status
* Response headers
* Response body (JSON) + structure

**Astuce** : dans Network → clic droit sur une requête →

* **Copy → Copy as cURL** (ou “Copy request headers”)
* **Save all as HAR with content** (dump global)

## Dump recommandé : HAR

### A. Export HAR

* Network → menu (⋮) → “Save all as HAR with content”
* Conserver le fichier .har en local.

### B. Exploitation du HAR

Objectif : trouver :

* base URL API
* endpoints exacts
* payloads
* cookies/session

## Session / auth : quoi récupérer exactement

### A. Cookies

* DevTools → Application/Storage → Cookies
* Export (manuel) des cookies associés au domaine
* Noter : noms, domaines, path, expiration, Secure/HttpOnly/SameSite

### B. Session

Chercher :

* réponses de login contenant des identifiants de session
* localStorage/sessionStorage (Application → Local Storage)

### C. Vérifier CAPTCHA / anti-bot

Indices :

* appels à reCAPTCHA/hCaptcha
* headers variables type `x-signature`, `x-timestamp`
* réponses 401/403 conditionnelles

## Upload : déterminer le modèle exact

Cas possibles (à identifier) :

1. Upload simple multipart vers API (rare mais possible)
2. Upload en 2 étapes :

   * init → URL signée
   * PUT vers storage (S3/OSS) → complete
3. Upload chunké (multi-part)

À extraire :

* taille max
* endpoints init/complete
* champs requis (fileName, md5/sha, mime, size)
* type de storage (URL signée, TTL)

## Download : déterminer le modèle exact

Cas typiques :

* API retourne une **URL signée** temporaire
* ou stream direct via API

À extraire :

* endpoint “get download”
* forme de l’URL (signed)
* expiration

## Quota / espace restant

Trouver un call qui renvoie :

* `totalQuota` / `usedQuota` / `freeQuota`
* ou un ratio
* ou un endpoint “profile/account/storage”

## Livrables de cette phase (sorties attendues)

1. HAR complet du scénario
2. Tableau des endpoints :

   * Auth
   * List files
   * File details
   * Download URL / download
   * Upload init / upload / complete
   * Delete
   * Quota
3. Dictionnaire des headers obligatoires
4. Format exact des objets JSON (schémas)

## Critères de fin

* Tu peux reproduire “list files” via cURL.
* Tu peux obtenir une URL de download via cURL.
* Tu peux uploader un fichier test via cURL.
* Tu peux le supprimer via cURL.
* Tu sais où est le quota.

---

## Notes APK Anycubic 1.1.27 (vidéo)

### Ressources UI et toggles vidéo

Images:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/drawable-xxhdpi/common_video_on.webp`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/drawable-xxhdpi/common_video_off.webp`

Selector:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/drawable/common_video_checkbox_selector.xml`

Layouts utilisant le selector:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/layout/task_activity_fdm_details.xml` (`@id/cb_video_btn`)
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/layout/task_activity_lcd_details.xml` (`@id/switch_video`)
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/layout/main_activity_fdm_printer_details.xml` (`@id/switch_video`)
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/res/layout/main_activity_lcd_printer_details.xml` (`@id/switch_video`)

### Architecture flux vidéo (pas d’URL statique)

* Affichage via `ACPeerVideoView` (et `ACLargeVideoView` pour les écrans “main”).
* Connexion P2P/WebRTC + AWS Kinesis Video Signaling.
* Alternative Agora (Shengwang) possible.
* Aucun `rtsp://`/`m3u8` visible: le flux est négocié via credentials temporaires.

Fichiers clés:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/widget/ACPeerVideoView.smali`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/peer/PeerConfiguration.smali`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/widget/ACLargeVideoView.smali`

### Credentials vidéo (PeerCredentialsDataBean)

Classe:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/ac/cloud/publicbean/main/data/response/PeerCredentialsDataBean.smali`

Champs:
* `region`
* `awsAccessKey` (JSON: `tmpSecretId`)
* `awsSecretKey` (JSON: `tmpSecretKey`)
* `sessionToken`
* `agora_error_code`

### Schéma PeerVideoResponse (API)

Classe:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/ac/cloud/publicbean/main/data/response/PeerVideoResponse.smali`

Champs:
* `token` → `PeerCredentialsDataBean`
* `shengwang` → `ShengwangTokenBean`
* `msgid` → `String`

### Schéma ShengwangTokenBean (Agora)

Classe:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes3/ac/cloud/publicbean/main/data/response/ShengwangTokenBean.smali`

Champs:
* `rtc_token`
* `appid`
* `user_account`
* `channel`
* `uid` (int)
* `client_uid` (int)
* `encryption_mode`
* `encryption_key`
* `encryption_kdf_salt`

### Source des credentials (API)

* Les credentials viennent de l’API `sendCommandPeerVideo` et sont stockés dans l’Activity.
Chaîne (FDM):
* `FDMTaskDetailsActivity.I1()` observe `PeerVideoViewModel.getSendCommandResult()`.
* Callback `FDMTaskDetailsActivity$m` lit `PeerVideoResponse.getToken()` et fait `FDMTaskDetailsActivity.A0(activity, PeerCredentialsDataBean)` (stockage).
* Fichiers:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/FDMTaskDetailsActivity.smali`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/FDMTaskDetailsActivity$m.smali`

Chaîne (LCD):
* `LCDTaskDetailsActivity` → callback `LCDTaskDetailsActivity$f` → `PeerVideoResponse.getToken()` → `LCDTaskDetailsActivity.r0(...)`.
* Fichiers:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/LCDTaskDetailsActivity.smali`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/LCDTaskDetailsActivity$f.smali`

### API utilisée pour récupérer le token

Interface Retrofit:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/PeerVideoService.smali`

Endpoint:
* `POST api/work/operation/sendOrder`
* Params: `order_id`, `printer_id`

Appel:
* `PeerVideoViewModel.sendCommandPeer(...)` → `PeerVideoNetworkApi.getApiService().sendCommandPeerVideo(order_id, printer_id)`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes6/com/anycubic/lib/video/PeerVideoViewModel$sendCommandPeer$1.smali`

Dispatch côté base:
* `BaseMqttHandleActivity` relaie `PeerCredentials` pour order_id `0x3e9` vers `onMqttPrintVideoCaptureEvent(...)`.
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali/ac/cloud/common/base/BaseMqttHandleActivity.smali`

Dans `onMqttPrintVideoCaptureEvent`:
* Si `state == "initSuccess"`, l’Activity appelle `ACPeerVideoView.createConnection(credentials)` avec ceux stockés via l’API.
* Si `pushStopped`, `stopCapture`, `initFailed`, etc, l’UI affiche des erreurs ou fait `disconnect()`.
* Fichiers:
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/FDMTaskDetailsActivity.smali`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/LCDTaskDetailsActivity.smali`

### Point exact de `createConnection(...)` dans les Activities

FDM task:
* `FDMTaskDetailsActivity.onMqttPrintVideoCaptureEvent(...)` → `ACPeerVideoView.createConnection(credentials)` sur `initSuccess`.
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/FDMTaskDetailsActivity.smali`

LCD task:
* `LCDTaskDetailsActivity.onMqttPrintVideoCaptureEvent(...)` → `ACPeerVideoView.createConnection(credentials)` sur `initSuccess`.
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/task/activity/LCDTaskDetailsActivity.smali`

Main screens (grande vue):
* `FDMPrinterDetailsActivity` et `LCDPrinterDetailsActivity` utilisent `ACLargeVideoView.createConnection(...)`.
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/main/activity/printer/FDMPrinterDetailsActivity.smali`
* `/home/kaj/Downloads/Anycubic_1.1.27_apkcombo.com/smali_classes4/ac/cloud/workbench/main/activity/printer/LCDPrinterDetailsActivity.smali`

---

## Plan d’implémentation vidéo (inspiré APK)

1. UI: ajouter un toggle `video_on/off` (selector) avec 2 états.
2. Commande “start/stop”: appeler `POST api/work/operation/sendOrder` avec `order_id` et `printer_id`. Dans l’APK: start = `0x3e9` (1001) (FDM + LCD), stop = `0x3ea` (1002) utilisé côté LCD, côté FDM aucun `0x3ea` trouvé dans l’Activity (le “stop” semble être un `stopPull()` local, à confirmer si un autre écran envoie un stop).
3. Récupération credentials (API): lire `PeerVideoResponse.token` (type `PeerCredentialsDataBean`) et le stocker localement.
5. Connexion P2P: utiliser `awsAccessKey/awsSecretKey/sessionToken/region` pour init Kinesis Signaling et créer la peer connection.
6. Fallback Agora: si token Shengwang présent, initialiser `initAgoraJoinChannel`.
7. UX et résilience: désactiver le toggle pendant l’init, timeout si pas de `initSuccess`, retry court sur `initFailed`.
