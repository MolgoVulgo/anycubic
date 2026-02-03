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
