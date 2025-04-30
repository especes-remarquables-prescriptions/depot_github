@echo off

REM Naviguer dans le répertoire du dépôt
cd .\depot_github

REM Mettre à jour le dépôt avec les dernières modifications
git pull origin main

echo Le dépôt a été mis à jour avec les dernières modifications depuis GitHub

REM Ajout des modifications
git add .

REM Commit des modifications avec un message de mise à jour
git commit -m "Mise à jour de l'application"

REM Push vers GitHub
git push origin main

REM Confirmation de la mise à jour
echo Les modifications ont été poussées vers GitHub.
pause