# $workingDir = "C:\Users\prajal.patel\source\repos\CollabollamaLLMToAPI"

# # Setup command to run python -m uvicorn main:app minimized
# $cmdLine = "cmd.exe /c start /min python.exe -m uvicorn main:app --app-dir `"$workingDir`""

# # Register in HKCU Run registry path (no admin privileges needed)
# $registryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
# $name = "Windows-Scheduler-Local-API"

# Set-ItemProperty -Path $registryPath -Name $name -Value $cmdLine

# Write-Host "Successfully registered $name in user startup registry ($registryPath)."
# Write-Host "The application will now start automatically (minimized) whenever you log in."
# Write-Host "To launch it immediately, run the following in PowerShell:"
# Write-Host "Start-Process cmd.exe -ArgumentList '/c start /min python.exe -m uvicorn main:app --app-dir `\"$workingDir`\"'"
