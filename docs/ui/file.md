Description fonctionnelle de l’interface

1. Conteneur principal (fenêtre)
Type : fenêtre unique, orientation verticale.
Disposition générale : colonne principale avec deux zones :
une barre supérieure d’actions,
une liste de fichiers scrollable en dessous.

2. Barre supérieure
Elle est alignée horizontalement en haut de l’écran.
Éléments :
Bouton “Upload file” (gauche)
Icône : nuage avec flèche vers le haut.
Texte : “Upload file”.
Style : bouton bleu clair, coins arrondis.
Action : ouvre une boite de dialogue d’upload.
Contenu de la boite de dialogue :
- Un bouton “File” permettant de choisir le fichier.
- Une case a cocher pour “selectionner l’imprimante” et permettre de lancer l’impression directement apres l’upload.
- Une case a cocher pour supprimer le fichier apres impression.
Indicateur d’espace de stockage (centre)
Texte : Space use: 1.06GB/2.00GB
Police : discrète, gris moyen.
Fonction : affiche l’espace utilisé vs total.
Bouton d’action secondaire (droite)
Icône : flèche vers le haut (upload alternatif) ou symbole d’ajout.
Style : bouton minimaliste, fond clair, bordure légère.
Rôle : action rapide d’import.

3. Liste des fichiers (zone principale)
Zone verticale scrollable, contenant des cartes de fichiers empilées.
Chaque carte de fichier a la même structure :
3.1 Carte de fichier (item individuel)
Disposition : ligne horizontale, hauteur fixe.
A. Miniature (gauche)
Image carrée (ratio 1:1), fond bleu foncé.
Au centre : rendu 3D stylisé du fichier .pwmb.
En bas à gauche de l’image : petit badge “pwmb”.
B. Métadonnées du fichier (centre)
Bloc vertical avec trois éléments :
Nom du fichier (ligne 1)
Exemples :
cat_skull-grand_5_v4.pwmb
raven_skull_grand.pwmb
skull_cut_25_15_v3.pwmb
Police : plus marquée que le reste.
Taille (ligne 2)
Format : Size : XXX.XX MB
Texte gris.
Date d’ajout (ligne 3)
Format : Add time : YYYY-MM-DD HH:MM:SS
Texte gris.
Lien “Details” (ligne 4, optionnel)
Petit lien cliquable en bleu.
Ouvre une vue détaillée du fichier.
C. Actions sur le fichier (droite)
Deux boutons alignés horizontalement :
Delete
Bouton gris clair, texte “Delete”.
Action : suppression du fichier après confirmation.
Download
Bouton bleu, texte “Download”.
Action : téléchargement du fichier.

4. Comportement global attendu
La liste doit :
supporter le scroll vertical,
rester responsive quand on ajoute/supprime un fichier,
rafraîchir la taille totale utilisée en haut.
Chaque carte doit être :
indépendante (composant réutilisable),
cliquable sur “Details” sans affecter le reste de l’interface,
capable d’afficher une miniature différente selon le fichier.

5. Modélisation minimale (logique)
Tu peux conceptualiser l’interface ainsi :
Fenêtre
Header (Upload + usage disque)
FileList (scrollable)
FileCard × N
Thumbnail
Metadata (name, size, time, details)
Actions (delete, download)
