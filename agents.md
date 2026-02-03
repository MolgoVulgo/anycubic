# Agent Codex — Anycubic Cloud Web Client (Python, GUI)

## Contexte d’utilisation

Ce fichier définit le cadre de fonctionnement d’un **agent Codex (extension VS Code)** pour un projet **Python** visant à implémenter un client Anycubic Cloud répliquant les appels de la web UI `cloud-universe.anycubic.com`, avec **interface graphique (GUI)**.

---

## Contraintes générales

* Objectif : **outil utilisable**, stable, prédictible.
* Modifications : **minimales et localisées**.
* Texte réduit : **code en priorité**.
* Questionner **uniquement** si une ambiguïté bloque l’implémentation.
* **Toujours répondre en français.**

---

## Objectifs prioritaires

1. **Fonctionnement correct sur un compte réel** (session valide)
2. **Stabilité réseau** (timeouts, retry/backoff, pas de crash)
3. **Sécurité** (ne jamais exposer secrets)
4. **Lisibilité / maintenabilité** (architecture claire, modèles)
5. **Modifications minimales** (si dépôt existant)

---

## Mission

Implémenter un client Python qui accède au cloud Anycubic via les mêmes endpoints que la web UI `cloud-universe.anycubic.com`.

Fonctions :
- lister (fichiers cloud)
- quota (total/used/free + %)
- infos fichier (id, name, size, date, type)
- télécharger (pull)
- uploader (push)
- supprimer (rm)

---

## Interface (GUI)

* L’application est pilotée via une **GUI** (pas de CLI).
* La GUI doit rester **fine** :
  - pas de logique API dans les widgets
  - appels centralisés dans une couche `api`
* La GUI doit gérer :
  - états “loading”
  - messages d’erreur exploitables
  - annulation (si possible) des opérations longues (download/upload)

---

## Modes d’authentification

### Mode A (prioritaire) : session importée

* Entrée : cookies exportés depuis navigateur.
* But : bypass CAPTCHA / anti-bot.

### Mode B (optionnel) : login direct

* Entrée : email/password.
* À implémenter seulement si l’API le permet **sans challenge**.

---

## Contraintes de sécurité (obligatoires)

* Ne jamais logger :
  - cookies
  - headers `Authorization`
  - URLs signées complètes si elles contiennent des paramètres sensibles
* Masquer/redacter systématiquement les secrets dans les logs.
* Stockage local de session :
  - format explicite
  - permissions raisonnables (éviter world-readable)
  - chemin configurable

---

## Comportement réseau (obligatoire)

* Client HTTP : `httpx` recommandé.
* Timeouts configurables.
* User-Agent configurable.
* Retry/backoff pour :
  - 429
  - 5xx
  - erreurs transitoires réseau
* Support des **URLs signées** (TTL court) si c’est le modèle.
* Support upload :
  - direct multipart **ou**
  - init → signed URL → complete (selon observation)

---

## Entrées attendues (nécessaires pour implémenter)

Le projet doit inclure une source de vérité sur l’API observée :
- soit `endpoints.py`
- soit `api_map.json` (préféré)

Doit contenir :
* Base URL API
* Endpoints exacts + méthodes (list/quota/info/download/upload/delete/auth)
* Headers obligatoires
* Schémas JSON request/response (au moins champs essentiels)
* Paramètres pagination (page/size ou cursor)

Si ces infos ne sont pas disponibles, l’agent :
- n’invente pas,
- indique exactement ce qui manque (URL/méthode/headers/payload/réponse).

---

## Architecture cible (imposée)

* `accloud/`
  * `client.py` : session HTTP + auth + redaction logs
  * `api.py` : fonctions haut niveau (list, quota, info, download, upload, delete)
  * `models.py` : dataclasses (FileItem, Quota, etc.)
* `session_store.py` : import/export session
  * `utils.py` : logging, retry, format bytes, helpers
* `gui/` (ou `accloud/gui/`)
  * `app.py` : bootstrap GUI
  * `views/` : écrans (files list, file details, quota, settings/auth)
  * `widgets/` : composants réutilisables
  * `state.py` : état UI + modèles de view (si pattern MVVM/MVC)

---

## Debug et logs (obligatoire)

* Toujours implémenter un système de logs.
* Logs activables/désactivables sans modifier le code fonctionnel :
  - variable env (ex: `ACCLOUD_DEBUG=1`)
  - et/ou option dans la GUI (toggle “Debug logs”)
* Format log clair :
  - module tag
  - niveau
  - message
* Redaction systématique des secrets (cookies/Authorization).

---

## Check-list de validation (rapide)

* Auth import :
  - cookies chargés
  - requêtes authentifiées confirmées (ex: quota OK)
* `quota` :
  - total/used/free + %
  - cohérent avec UI
* liste :
  - pagination OK
  - affichage stable (tri/filtre côté UI si nécessaire)
* download :
  - fichier intègre (taille/hash si possible)
* upload :
  - upload OK + visible dans la liste
* delete :
  - suppression OK + absent de la liste
* Aucun log de secrets.

---

## Politique de modification du code

* **Exécuter immédiatement** la solution la plus probable.
* **Aucune discussion** tant que le code :
  - fonctionne,
  - gère les erreurs proprement,
  - n’expose pas de secrets.
* Pas de complexité inutile.
* Pas d’effets de bord : chaque changement doit être traçable.

---

## Structure de réponse attendue (quand tu rends un changement)

* Constat technique
* Action(s) appliquée(s)
* Indication de validation (comment vérifier sur compte réel)
* Hypothèses (si nécessaire)
* Après toute génération ou modification de code :
  - analyser le diff réel et les fichiers impactés
  - produire un message de commit en anglais, à l’impératif, reflétant l’intention principale du changement
