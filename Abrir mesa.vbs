Option Explicit
Dim shell, files, folder
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.Environment("PROCESS")("APURACAO_OCULTO") = "1"
shell.Run Chr(34) & folder & "\Iniciar pesquisa.cmd" & Chr(34), 0, False
