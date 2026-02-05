# 2 — Cahier des charges : app Python d’accès au cloud Anycubic (web)

## 2.1 Objectif produit

Développer un client Python (CLI prioritaire, lib optionnelle) permettant d’interagir avec le cloud Anycubic **comme la web UI** :

* Lister les fichiers
* Récupérer détails + quota (espace utilisé/restant)
* Télécharger un fichier
* Uploader un fichier
* Supprimer un fichier

## 2.2 Hypothèse structurante

L’authentification et les endpoints sont ceux observés via DevTools/HAR.
Le produit ne suppose pas l’app mobile.

## 2.3 Périmètre fonctionnel

### A. Authentification

Deux modes (priorité à la robustesse) :

1. **Mode session importée** (recommandé)

   * Entrée : cookies exportés (depuis navigateur)
   * Avantage : évite CAPTCHA/anti-bot
2. **Mode login direct** (optionnel)

   * Entrée : email+password
   * Contraintes : peut échouer si CAPTCHA ou device-binding

### B. Fonctions “core”

1. **List files**

   * Sortie : liste paginée + champs utiles
   * Filtres : tri (date/taille/nom), recherche (substring)
2. **Get file details**

   * Sortie : métadonnées complètes (id, nom, taille, date, type)
3. **Get quota**

   * Sortie : used / total / free + unités + pourcentage
4. **Download**

   * Support :

     * via URL signée
     * ou stream via API
   * Sortie : fichier écrit sur disque
5. **Upload**

   * Support :

     * upload direct
     * ou init→signed URL→complete
     * ou chunk/multipart
   * Sortie : id du fichier créé + métadonnées
6. **Delete**

   * Suppression par id
   * Option “dry-run”

## 2.4 Exigences non-fonctionnelles

### A. Robustesse

* Gestion des erreurs HTTP (401/403/429/5xx)
* Retry contrôlé (backoff) pour 429/5xx
* Timeout configurables

### B. Sécurité

* Ne pas logger les cookies en clair
* Stockage des secrets :

  * fichier local avec permissions strictes (0600)
  * ou variables d’environnement

### C. Traçabilité

* Log niveaux : ERROR / WARN / INFO / DEBUG
* DEBUG affiche : endpoint + status + latence, sans secrets
* `accloud_http.log` : journalier, rotation 7 jours, archives `.tar.gz`

### D. Portabilité

* Python 3.11+ (ou 3.10+ selon contraintes)
* Linux-first, compatible Windows

## 2.5 Interface & UX (outil)

### A. GUI (prioritaire)

* Import HAR pour créer `.accloud/session.json`
* Liste / quota / upload / download / delete

#### Procédure HAR (GUI)

1) Ouvrir https://cloud-universe.anycubic.com dans le navigateur  
2) Se connecter  
3) Ouvrir DevTools → Network  
4) Recharger la page  
5) Clic droit dans la liste → **Save all as HAR**  
6) Dans l’app, menu **Import HAR** → sélectionner le fichier

### B. Sorties

* Sortie par défaut : lisible humain
* Option `--json` sur ls/quota/info

## 2.6 Modèle de données minimal (à aligner sur l’API réelle)

### FileItem

* id (string)
* name (string)
* size_bytes (int)
* created_at (iso string)
* type (ex: pwmb)
* preview_url (optionnel)

### Quota

* total_bytes
* used_bytes
* free_bytes
* used_percent

## 2.7 Configuration

* Fichier `config.toml` (ou `yaml`) :

  * base_url
  * timeouts
  * retry policy
  * paths session (cookies)
  * user-agent (si requis)

## 2.8 Tests & validation

### A. Tests unitaires

* parsing JSON
* calcul quota
* construction requêtes

### B. Tests d’intégration (réels)

* liste → download → upload → delete
* vérification quota avant/après upload

## 2.9 Contraintes / risques

* CAPTCHA : bloque login direct → priorité session importée
* endpoints instables : prévoir abstraction + mapping par config
* URL signées à TTL court : téléchargement immédiat
* upload chunké : complexité → implémentation progressive

## 2.10 Critères d’acceptation

* Avec une session importée valide :

  * `quota` renvoie des valeurs cohérentes
  * `ls` affiche la liste correcte
  * `pull` télécharge un fichier intègre
  * `push` upload et le fichier apparaît dans `ls`
  * `rm` supprime et le fichier disparaît

## 2.11 Hors périmètre

* Pilotage imprimante
* Monitoring impression
* Gestion multi-comptes
* Interface CLI
