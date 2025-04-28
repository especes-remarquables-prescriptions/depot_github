@echo off
REM Création de l'environnement virtuel
python -m venv venv

REM Activation de l'environnement virtuel (pour Windows)
call venv\Scripts\Activate.ps1

REM Installation des dépendances via requirements.txt
pip install -r requirements.txt

REM Confirmer que l'environnement est prêt
echo L'environnement virtuel est configuré et les dépendances sont installées.
pause