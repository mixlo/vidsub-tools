function InstallScript([Parameter(Mandatory=$true)][string]$PyScript)
{
    $scriptFile = Get-Item $PyScript
    $removables = @(
        "$($scriptFile.Directory.FullName)\__pycache__",
        ".\$($scriptFile.BaseName).spec",
        ".\build",
        ".\dist"
    )

    python3 -m PyInstaller --log-level WARN --onefile $scriptFile.FullName
    Move-Item -Path .\dist\$($scriptFile.BaseName).exe C:\tools\ -Force
    Remove-Item -Path $removables -Recurse -Force
}

Get-ChildItem -Filter:.\source\*.py | % { 
    Write-Host "Installing: $_"
    InstallScript -PyScript:$_.FullName 
    Write-Host
}
