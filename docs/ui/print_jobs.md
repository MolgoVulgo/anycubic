1) Structure logique des données

Tu reçois une liste de jobs. Chaque job est un objet “PrintTask”.
Champs imbriqués importants :
settings : string JSON (à parser) → contient les infos les plus “UI-ready” (filename, layers, state…)
slice_param / slice_result : string JSON (à parser) → contient paramètres d’impression détaillés, machine, volumes, etc.
👉 En UI, on s’alimente principalement via :
racine (progress, pause, remain_time, material…)
settings parsed (filename, curr_layer, total_layers, state…)
slice_param parsed (zthick, exposure_time, off_time, bott_time, bott_layers…)

2) Mapping UI → JSON (écran “Print Jobs”)
A. En-tête / navigation
Onglet actif “Print Jobs” : pas un champ, état de navigation.
“Print History” : autre endpoint/filtre, hors scope.
“Back to printer list” : navigation, hors data.
B. Panneau gauche : Printer info
Nom imprimante
UI: Anycubic Photon M3 Plus
JSON: printer_name (ou machine_name)
Printer Status (Busy / Idle / Offline / …)
Sources possibles :
device_status (ex: 1)
connect_status (ex: 0)
print_status (ex: 1)
settings.state (parsed) (ex: "printing")
Recommandation de logique (sans code) :
Si connect_status indique offline → “Offline”
Sinon si settings.state == "printing" ou print_status == 1 → “Busy”
Sinon si pause == 1 ou settings.state == "paused" → “Paused”
Sinon → “Idle”
Printer Type
UI: “Anycubic Photon M3 Plus”
JSON: machine_name (ou slice_param.machine_name)
Total Printing Time / Total Consumption Resin / Number of Prints / Binding Time / Firmware / Device CN / MAC
Ton JSON fourni est centré job, pas “printer stats”.
Tu as bien :
printer_id, device_status, machine_type, type, machine_class, key
Mais pas :
total cumul print, total résine cumulée, nb prints cumulés, firmware, mac, binding time (au sens UI)
➡️ Donc ces champs viennent probablement d’un autre endpoint “printer detail”.
(À noter : total_time: "printing..." n’est pas un total cumul imprimante, juste un placeholder job.)
Device CN
UI: “Device CN”
JSON: key ressemble à un identifiant device applicatif.
Device CN exact n’est pas explicitement présent ; si tu veux un identifiant affichable, tu peux utiliser key (ou un champ device non fourni ici).
C. Panneau central : Job viewer
Nom fichier
UI: T3d_skull_10_50_v3.pwmb
JSON:
settings (parsed) → filename
fallback : gcode_name + extension si connue
Image / preview
UI montre un rendu 3D, mais côté données tu as une preview image
JSON:
img ou image_id (URL)
settings (parsed) ne porte pas l’URL mais a model_hight etc.
Progress bar + %
UI: “13%” dans ta capture (exemple) ; ton JSON exemple a progress: 75
JSON:
progress (0–100)
settings.progress (parsed) (idem)
Boutons Pause / Stop
UI actions
JSON état :
Pause : pause (0/1)
Stop : pas un booléen direct, plutôt state, print_status, status, reason
Pour l’UI :
afficher “Pause” si pause==0 et état printing
afficher “Resume” si pause==1 ou settings.state=="paused"
“Stop” dispo si état printing/paused
D. Panneau droit : Job metrics
Elapsed Time
UI: “Elapsed Time 8m”
JSON:
print_time (ici 35) : probablement minutes ou secondes selon convention API
ou calculable via start_time et last_update_time (ms)
Vu tes valeurs :
start_time est en epoch seconds
last_update_time est en epoch ms
➡️ Le plus robuste : elapsed = now/last_update - start_time (en normalisant unités).
Remaining Time
UI: “Remaining Time 34m”
JSON:
remain_time (ici 9)
settings.remain_time (parsed) (ici 9)
Attention : unité probablement minutes (mais à confirmer côté API).
Layers (X / Y)
UI: 40 / 287
JSON:
settings.curr_layer (parsed) = 219
settings.total_layers (parsed) = 287
slice_param.layers = 287
➡️ UI: curr_layer / total_layers
Estimated Resin Volume
UI: “44.19ml”
JSON:
material = "44.192310333252" (string)
settings.supplies_usage = 44.19231 (parsed)
slice_param.supplies_usage = 44.19231 (parsed)
➡️ UI: arrondi 2 décimales + “ml”
Model Size
UI vide dans ta capture
JSON:
slice_param.size_x, size_y, size_z
ici size_x=0, size_y=0, size_z≈14.35
➡️ Si X/Y sont 0, tu peux :
afficher “—”
ou afficher seulement Z (ex: “Z: 14.35mm”)
ou masquer la ligne si non fourni
E. Print parameters (lecture seule + lien Modify)
Layer Thickness (mm)
UI: 0.050
JSON:
slice_param.zthick ≈ 0.05
settings.z_thick = 0.05
Normal Exposure Time (s)
UI: 1.500
JSON:
slice_param.exposure_time = 1.5
settings.settings.on_time = 1.5
Off Time (s)
UI: 0.500
JSON:
slice_param.off_time = 0.5
settings.settings.off_time = 0.5
Bottom Exposure Time (s)
UI: 23.000
JSON:
slice_param.bott_time = 23.0
settings.settings.bottom_time = 23
Bottom Layers
UI: 6
JSON:
slice_param.bott_layers = 6
settings.settings.bottom_layers = 6

3) Champs “état” utiles pour le rendu UI (normalisation)
Pour éviter un UI instable, tu peux normaliser côté backend en un état unique :
job_state : dérivé de settings.state (printing/paused/…)
is_online : dérivé de connect_status
is_printing : job_state=="printing" ou print_status==1
is_paused : pause==1 ou job_state=="paused"
progress_pct : progress (int)
layers_done/total : settings.curr_layer / settings.total_layers

4) Incohérences / points à cadrer (sinon bugs UI)
Unités temps
estimate = 3114 (secondes ? minutes ?)
remain_time = 9 (minutes ?)
print_time = 35 (minutes ?)
➡️ Il faut une convention claire sinon “Elapsed/Remaining” sera faux.
Multiples sources doublonnées
progress existe à la racine et dans settings.
supplies_usage/material idem.
➡️ Définis une priorité : settings (parsed) > racine > slice_param.
Champs imprimante vs champs job
Ton JSON ne suffit pas pour remplir le panneau gauche “stats cumulés imprimante”.
➡️ Prévoir endpoint printer-detail.