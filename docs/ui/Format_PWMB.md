Format PWMB – Extraction de l’image Preview

1. Contexte
Le format .pwmb est un conteneur propriétaire utilisé par certaines imprimantes résine Anycubic pour stocker :
Les données de couches (layers UV)
Les paramètres de slicing (exposition, résolution, nombre de couches, etc.)
Une ou plusieurs images de prévisualisation (preview)
La structure complète du format n’est pas documentée publiquement.
L’extraction de la preview ne doit pas dépendre d’une compréhension complète du conteneur.
Objectif : extraire et afficher l’image preview dans une application interne sans parser l’intégralité du format propriétaire.

2. Hypothèse de travail
Observation empirique :
La preview est généralement stockée comme image standard encodée directement dans le flux binaire.
Le plus fréquent : JPEG
Plus rare : PNG
Un fichier peut contenir plusieurs previews (ex : miniature + preview principale).
Conséquence : il n’est pas nécessaire d’implémenter un parser PWMB complet pour récupérer la preview.

3. Stratégie d’extraction
Principe
Scanner le flux binaire du fichier .pwmb à la recherche de signatures de formats d’image standards, puis extraire les blocs correspondants.
Signatures à détecter
JPEG
Début (SOI)
Fin (EOI)
PNG
Signature PNG standard
Chunk terminal IEND + CRC
Processus
Lecture binaire du fichier.
Recherche des signatures d’images.
Extraction de chaque bloc image complet.
Validation minimale (cohérence interne du format image).
Sélection de la preview pertinente.

4. Sélection de la bonne preview
Un fichier peut contenir plusieurs images.
Critères recommandés pour sélectionner la preview principale :
Ordre de priorité :
Image avec la plus grande résolution (largeur × hauteur).
À défaut : image avec la plus grande taille binaire.
Éviter de supposer que la première occurrence est la bonne.

5. Architecture recommandée (app interne)
Module dédié : pwmb_preview_extractor
Responsabilités :
Lecture fichier binaire
Détection signatures image
Extraction bloc image
Validation basique format
Retour image sous forme buffer / stream
Ce module ne doit pas :
Parser les layers
Modifier le fichier
Réécrire le conteneur
Dépendre d’une structure interne du header PWMB

6. Gestion des erreurs
Cas à gérer explicitement :
Aucune signature d’image détectée
Signature trouvée mais bloc incomplet
Image corrompue
Plusieurs images détectées
Comportement recommandé :
Logger les occurrences détectées
Retourner null / erreur structurée si aucune preview valide
Ne jamais bloquer l’application principale

7. Performance
Les fichiers PWMB peuvent être volumineux.
Recommandations :
Scanner en flux (stream) si nécessaire
Éviter de charger intégralement en mémoire si > 200 MB
Limiter le nombre d’images extraites à un seuil raisonnable

8. Limites connues
Le format PWMB étant propriétaire, Anycubic peut modifier l’implémentation interne.
Il n’existe aucune garantie que la preview restera toujours stockée sous forme JPEG/PNG brute.
Cette approche repose sur un comportement observé, non contractuel.

9. Conclusion opérationnelle
Pour une application maison, la méthode la plus robuste consiste à :
Ignorer la structure propriétaire PWMB
Extraire les images embarquées via signatures standards
Sélectionner dynamiquement la meilleure preview
Cela garantit :
Implémentation simple
Maintenance faible
Indépendance vis-à-vis des évolutions internes du format