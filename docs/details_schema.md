# Détails fichier (gcode/info) — Schéma synthétique

Source : `docs/details.json.md` (exemple réel).

## 1) Base info (listing)

- `id` : string (file_id)
- `name` : string
- `size` : string (format lisible, ex: "115.22MB")
- `created_at` : string (YYYY-MM-DD HH:MM:SS)
- `type` : int (type fichier)
- `md5` : string
- `thumbnail` : string (URL image associée)
- `url` : string (URL CDN du fichier)
- `gcode_id` : string (identifiant pour gcode/info)

## 2) GCode info (gcode/info?id=<gcode_id>)

### Identité / liens
- `id` : int (gcode_id)
- `user_id` : int
- `name` : string
- `model` : int (file_id)
- `img` : string (URL image)
- `image_id` : string (URL image S3)

### Slicing (paramètres principaux)
Regroupés dans `slice_param` et/ou `slice_result` (doublon fréquent).

- `machine_name` : string
- `material_name` : string
- `material_type` : string
- `material_unit` : string
- `layers` : int
- `estimate` : int (temps total)
- `size_x` / `size_y` / `size_z` : float (dimensions)
- `zthick` : float (épaisseur couche)
- `exposure_time` : float
- `off_time` : float
- `supplies_usage` : float (consommation)
- `sliced_md5` : string

### Contrôles avancés (extraits)
- `advanced_control.bott_0` / `bott_1` / `normal_0` / `normal_1`
  - `down_speed`, `up_speed`, `z_up_speed`, `height`
- `transition_layercount` : int

### Statut / méta
- `progress` : int (0–100)
- `code` : int
- `desc` : string
- `create_time` / `end_time` / `timestamp` : int (epoch seconds)
- `status` : int
- `size` : int (taille bytes)

### Champs parfois null/vides
- `slice_support`, `support_param`, `req`, `hollow_param`, `punching_param`
- `ams_settings`, `plate_info`, `sliced_id`, `dispatch_id`

## 3) Résumé minimal recommandé (UI)

- `name`, `machine_name`, `material_name`
- `layers`, `estimate`, `size_z`, `zthick`
- `exposure_time`, `off_time`, `supplies_usage`
- `thumbnail` / `image_id` (aperçu)
