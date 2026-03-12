$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$releaseRoot = Join-Path $projectRoot 'release-output'
$packageDir = Join-Path $releaseRoot 'windows-green'
$zipPath = Join-Path $releaseRoot 'bilibili-video-downloader-windows-green.zip'

function Copy-RequiredPath {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Missing required path: $Source"
    }

    Copy-Item -Path $Source -Destination $Destination -Recurse -Force
}

if (-not (Test-Path (Join-Path $projectRoot 'dist'))) {
    throw 'Missing dist directory. Run "npm run build" first.'
}

if (-not (Test-Path (Join-Path $projectRoot 'runtime'))) {
    throw 'Missing runtime directory. Green package requires the embedded Python runtime.'
}

if (Test-Path $packageDir) {
    Remove-Item -Path $packageDir -Recurse -Force
}

if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

New-Item -ItemType Directory -Path $packageDir -Force | Out-Null

Copy-RequiredPath -Source (Join-Path $projectRoot 'api.py') -Destination $packageDir
Copy-RequiredPath -Source (Join-Path $projectRoot 'start.bat') -Destination $packageDir
Copy-RequiredPath -Source (Join-Path $projectRoot 'README-green.md') -Destination $packageDir
Copy-RequiredPath -Source (Join-Path $projectRoot 'dist') -Destination $packageDir
Copy-RequiredPath -Source (Join-Path $projectRoot 'runtime') -Destination $packageDir

Compress-Archive -Path (Join-Path $packageDir '*') -DestinationPath $zipPath -Force

Write-Host "Green package directory: $packageDir"
Write-Host "Green package zip: $zipPath"
