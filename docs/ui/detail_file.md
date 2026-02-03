1) Layout global
Fenêtre = page unique “File details” avec 2 cartes (cards) empilées verticalement :
Card A — Header + Preview + Meta
Card B — “Slicing details” (détails de slicing, en 2 colonnes)
Fond gris très clair, cards blanches avec coins arrondis + ombre légère. Marges généreuses.

2) Card A — Détails fichier (haut)

A1. Barre de titre (dans la card)
Titre (gauche) : cat_skull-grand_5_v4.pwmb (font un peu plus gros, semi-bold)
Badge (droite) : “Slice file” (petit pill gris clair)
Mapping JSON :
Titre = name
Badge = dérivé de type logique (ici fichier slice)

A2. Corps en 2 colonnes (split horizontal)
Colonne gauche (≈ 65%) : Preview
Un grand bloc de preview centré (rectangle clair)
À l’intérieur, une image carrée (rendu slice/thumbnail)
Pas d’outils visibles dans ta capture : donc preview “passive” (option : clic pour agrandir)
Mapping JSON :
Image = image_id (URL S3) en priorité
Fallback = img (endpoint apitest) si image_id absent
Colonne droite (≈ 35%) : Meta en liste key/value
4 lignes max, espacées :
File name: cat_skull-grand_5_v4.pwmb
Type: Slice file
Size: 115.22 MB
Time uploaded: 2026-02-01 19:16:47
Mapping JSON + conversions :
File name = name
Type = constant UI (“Slice file”) ou dérivé (TYPE_LCD_SLICE_FILE_PARSE_RESP → slice)
Size = size (bytes) → affichage MB (base 1024 ou 1000, mais ta capture ressemble à 115.22 MB donc conversion cohérente à caler)
Time uploaded = create_time (epoch) ou timestamp → format YYYY-MM-DD HH:MM:SS

3) Card B — “Slicing details” (bas)
B1. En-tête
Icône “gear” (petite) + label “Slicing details”
Ligne de séparation fine en dessous

B2. Grille de paramètres en 2 colonnes (key/value)
Chaque colonne est une pile de lignes “Label: Value”.
Les labels sont en gris moyen, valeurs en noir.
Colonne gauche (comme sur la capture)
Printer type: Anycubic Photon M3 Plus
→ slice_param.machine_name (ou machine_name)
Print size: -
→ afficher “-” si size_x == 0 et size_y == 0 (ou données absentes)
→ sinon X × Y × Z mm (Z = size_z)
Estimated printing time: 03:06:58
→ slice_param.estimate secondes → HH:MM:SS
Thickness (mm): 0.05
→ slice_param.zthick arrondi 2 décimales
Lights off time(s): 0.50
→ slice_param.off_time (2 décimales)
Number of bottom layers: 6
→ slice_param.bott_layers
Z Axis lifting speed(mm/s): 6.00
→ slice_param.zup_speed (2 décimales)
Colonne droite (comme sur la capture)
Consumables: Resin
→ slice_param.material_type (“Resin”)
Slice layers: 1223
→ slice_param.layers
Estimated amount of consumables: 162.58ml
→ slice_param.supplies_usage + material_unit (ml), arrondi 2 décimales
Exposure time(s): 1.50
→ slice_param.exposure_time (2 décimales)
Bottom exposure time(s): 23.00
→ slice_param.bott_time (2 décimales)
Z Axis lifting distance(mm): 6.00
→ slice_param.zup_height (2 décimales)
Z Axis fallback speed(mm/s): 6.00
→ slice_param.zdown_speed (2 décimales)

4) Règles d’affichage (pour coller au rendu Anycubic)

Unités collées comme dans la capture : 162.58ml (pas d’espace) et mm/s, time(s)
Arrondis :
vitesses/hauteurs/temps : 2 décimales
épaisseur : 2 décimales
Valeur manquante : afficher - (pas “N/A”, pas “null”)
Valeurs doubles : tu as slice_param et slice_result quasi identiques → choisir une source unique (reco : slice_param en priorité, fallback slice_result).

5) États UI nécessaires (toujours côté visuel)
Loading (card A et/ou B) : skeleton / spinner discret dans la card, pas une popup.
Erreur image : placeholder gris + icône broken-image, sans stacktrace.
Erreur data : conserver l’écran, afficher - et un bandeau discret “Some data unavailable”.

6) Ce que je ne mettrais pas (pour rester fidèle à ta capture)
Pas de barre d’actions (Download/Delete) visible dans cet écran si tu veux coller strictement au visuel fourni.
Pas de tables, pas de tabs, pas de sidebar : c’est du card + key/value.