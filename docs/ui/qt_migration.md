Plan de migration UI (Tkinter -> PySide6/Qt)

1) Cartographie des ecrans existants
- Onglet Fichiers (files_tab): liste fichiers, quota, upload/download/delete, details.
- Fenetre File Details: details fichier + slicing.
- Onglet Printer: infos imprimante, job viewer, job metrics.
- Onglets Print / LOG: utilitaires (pas de spec UI).
- Menus Import HAR / Aide.

2) Mapping des specs UI
- docs/ui/file.md -> Onglet Fichiers.
- docs/ui/detail_file.md -> Fenetre File Details.
- docs/ui/print_jobs.md -> Onglet Printer (Print Jobs).
- Pas de spec pour Print / LOG.

3) Architecture Qt proposee
- accloud/ui/qt_main.py: point d'entree PySide6.
- accloud/ui/qt_app.py: MainWindow + QTabWidget + menu.
- accloud/ui/state.py: etat UI (client, session, cache).
- accloud/ui/threads.py: wrapper QRunnable + signaux.
- accloud/ui/views/files_tab.py: onglet Fichiers (spec file.md).
- accloud/ui/views/file_details.py: fenetre details (spec detail_file.md).
- accloud/ui/views/printer_tab.py: onglet Printer (spec print_jobs.md).
- accloud/ui/views/print_tab.py / log_tab.py: placeholders propres.

4) Strategie de portage
- Etape 1: structure Qt + FilesTab (fonctionnel).
- Etape 2: FileDetailsWindow (base info + slicing details).
- Etape 3: PrinterTab (job viewer + metrics).
- Etape 4: placeholders Print/LOG.
- Conserver Tkinter en parallele pour rollback.

5) Points techniques
- Asynchrone: QThreadPool + QRunnable (equivalent _run_task).
- Reutiliser accloud.api et accloud.client sans modification.
- UI basee sur docs/ui (cards, labels, badges, actions).
