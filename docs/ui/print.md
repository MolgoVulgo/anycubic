Fenêtre principale – “Remote Print” (dialog modal)

Nature et comportement
Fenêtre de type boîte de dialogue modale, centrée, taille fixe, avec un en-tête et une zone de contenu principale. Fond global clair, style moderne et arrondi.

1. En-tête (Header)
En haut de la fenêtre :
Titre :  "Print”, aligné à gauche.
Bouton de fermeture (X) : situé en haut à droite, icône standard de fermeture de fenêtre.

2. Champ “Task name”
Juste sous le header :
Label : “Task name:”
Champ texte contenant “catskull”.
C’est une ligne horizontale simple, avec texte.

3. Zone de prévisualisation (Preview panel)
Bloc central dominant visuellement :
Grand rectangle aux coins arrondis.
Fond bleu-vert sombre uniforme.
Centré à l’intérieur : un rendu 3D du modèle (objet “skull” stylisé, couleur turquoise, avec supports visibles).
Pas de bordure visible, uniquement le contraste avec le fond de la fenêtre.
Ce composant agit comme un viewer statique de prévisualisation, sans contrôles visibles (pas de boutons de rotation, zoom, etc.).

4. Ligne d’informations d’impression
Sous la prévisualisation, sur une seule ligne horizontale :
Trois informations, séparées visuellement par de l’espace :
Icône + texte imprimante : “Anycubic Photon M3 Plus”
Icône horloge + durée estimée : “1h26m14s”
Icône goutte + volume de résine : “4.165 ml”
C’est une barre d’infos compacte, typiquement un layout horizontal avec icônes + labels.

5. Sélecteur d’imprimante (Printer selection panel)
Bloc légèrement séparé, style “carte” :
À gauche :
Icône cloud / connexion (bleue), suggérant une imprimante connectée.
À droite :
Nom affiché en gras : “Anycubic Photon M3 Plus”
Sous-texte (plus léger) : répète “Anycubic Photon M3 Plus”
À l’extrême droite :
Icône de menu / options (≡ ou lignes empilées), indiquant des réglages ou une liste déroulante possible.
Ce bloc correspond à un sélecteur d’imprimante connectée, probablement cliquable.

6. Barre de boutons (Footer actions)
Tout en bas, alignés à droite :
Bouton “Cancel”
Style secondaire, contour ou fond clair.
Bouton “Start Printing”
Style primaire (bleu), plus visuel, indiquant l’action principale.
Les deux boutons sont de taille standard, alignés horizontalement avec un léger espacement.
Hiérarchie visuelle (résumé)
Si tu devais le formaliser en couches :
Dialog "Print”
Header (titre + close)
Task name (label)
Preview panel (objet 3D)
Info bar (printer | time | volume)
Printer selector card
Action buttons (Cancel / Start Printing)

Cache images (preview)
Pour limiter les accès réseau, les images de preview téléchargées sont mises en cache (mémoire + disque).
Variables d’environnement disponibles :
- `ACCLOUD_IMAGE_CACHE` : active/désactive le cache (défaut `true`)
- `ACCLOUD_IMAGE_CACHE_DIR` : dossier de cache (défaut = temp système)
- `ACCLOUD_IMAGE_CACHE_MEM` : nombre d’images en mémoire (défaut `64`)
- `ACCLOUD_IMAGE_CACHE_ITEMS` : nombre d’images sur disque (défaut `256`)
- `ACCLOUD_IMAGE_CACHE_MB` : taille max du cache disque en Mo (défaut `128`)
