#Requires -RunAsAdministrator

# Agregar opción 'Copiar Ruta de Acceso' al menú contextual para archivos
New-Item -Path "HKCR:\*\shell\CopiarRutaAcceso" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\*\shell\CopiarRutaAcceso" -Name "(Default)" -Value "Copiar Ruta de Acceso"
New-Item -Path "HKCR:\*\shell\CopiarRutaAcceso\command" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\*\shell\CopiarRutaAcceso\command" -Name "(Default)" -Value 'cmd /c echo "%1" | clip'

# Agregar opción 'Copiar Ruta de Acceso' al menú contextual para carpetas
New-Item -Path "HKCR:\Directory\shell\CopiarRutaAcceso" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\Directory\shell\CopiarRutaAcceso" -Name "(Default)" -Value "Copiar Ruta de Acceso"
New-Item -Path "HKCR:\Directory\shell\CopiarRutaAcceso\command" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\Directory\shell\CopiarRutaAcceso\command" -Name "(Default)" -Value 'cmd /c echo "%1" | clip'

# Agregar opción 'Copiar Ruta de Acceso' al menú contextual del fondo de carpetas
New-Item -Path "HKCR:\Directory\Background\shell\CopiarRutaAcceso" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\Directory\Background\shell\CopiarRutaAcceso" -Name "(Default)" -Value "Copiar Ruta de Acceso"
New-Item -Path "HKCR:\Directory\Background\shell\CopiarRutaAcceso\command" -Force | Out-Null
Set-ItemProperty -Path "HKCR:\Directory\Background\shell\CopiarRutaAcceso\command" -Name "(Default)" -Value 'cmd /c echo "%V" | clip'

Write-Host "Opción 'Copiar Ruta de Acceso' agregada al menú contextual del Explorador de Windows."
Write-Host "Reinicia el Explorador de Windows o cierra la sesión para que los cambios surtan efecto."