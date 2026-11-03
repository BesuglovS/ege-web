<#
.SYNOPSIS
  Build and deploy static site to remote server via SSH.
.DESCRIPTION
  Reads config from .env, runs python build_site.py, packs the project
  and syncs it to the remote server via tar over SSH. Dev files (.git,
  IDE files, .env, deploy script, caches) are excluded.
.PARAMETER DryRun
  Show commands without executing.
.PARAMETER SkipBuild
  Skip the build step and deploy the current files.
.EXAMPLE
  .\deploy.ps1
  .\deploy.ps1 -DryRun
  .\deploy.ps1 -SkipBuild
#>

param(
  [switch]$DryRun,
  [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'

# --- Deploy marker: writes version.json into the deployed payload ---
# Records commit/branch/tree/dirty/deployedAt/via so the deployed content can be
# compared with the local repository later (see na-web/check-deploy.ps1).
function New-DeployMarker {
  param(
    [Parameter(Mandatory)][string]$ProjectDir,
    [Parameter(Mandatory)][string]$OutFile,
    [string]$Via = 'deploy.ps1'
  )
  $commit = $null; $branch = $null; $tree = $null; $dirty = $null; $changed = $null
  if (Test-Path (Join-Path $ProjectDir '.git')) {
    $prevEap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try {
      $commit  = (& git -C $ProjectDir rev-parse HEAD 2>$null)
      $branch  = (& git -C $ProjectDir rev-parse --abbrev-ref HEAD 2>$null)
      $tracked   = @(& git -C $ProjectDir diff HEAD --numstat 2>$null)
      $untracked = @(& git -C $ProjectDir ls-files -o --exclude-standard 2>$null)
      $changed   = $tracked.Count + $untracked.Count
      $dirty     = ($changed -gt 0)
      if ($dirty) {
        $stash = (& git -C $ProjectDir stash create 2>$null)
        if ($stash) { $tree = (& git -C $ProjectDir rev-parse "$($stash.Trim())^{tree}" 2>$null) }
      } else {
        $tree = (& git -C $ProjectDir rev-parse 'HEAD^{tree}' 2>$null)
      }
    } finally { $ErrorActionPreference = $prevEap }
  }
  $marker = [ordered]@{
    project    = Split-Path -Leaf $ProjectDir
    commit     = if ($commit) { $commit.Trim() } else { $null }
    branch     = if ($branch) { $branch.Trim() } else { $null }
    tree       = if ($tree)   { $tree.Trim() }   else { $null }
    dirty      = $dirty
    dirtyFiles = $changed
    deployedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    deployedBy = $env:USERNAME
    via        = $Via
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutFile) | Out-Null
  [System.IO.File]::WriteAllText($OutFile, ($marker | ConvertTo-Json -Depth 3),
    (New-Object System.Text.UTF8Encoding($false)))
}

# ─── 1. Load .env ───
$envFile = Join-Path $PSScriptRoot '.env'
if (Test-Path $envFile) {
  # Читаем явно как UTF-8: PowerShell 5.1 использует ANSI и портит кириллицу.
  foreach ($line in [System.IO.File]::ReadAllLines($envFile, [System.Text.Encoding]::UTF8)) {
    if ($line -match '^\s*([^#=]+?)\s*=\s*(.*?)\s*$') {
      $key = $matches[1]
      $val = $matches[2]
      if ($val.Length -ge 2 -and
          (($val[0] -eq '"' -and $val[-1] -eq '"') -or ($val[0] -eq "'" -and $val[-1] -eq "'"))) {
        $val = $val.Substring(1, $val.Length - 2)
      }
      [Environment]::SetEnvironmentVariable($key, $val)
    }
  }
}

$sshHost    = [Environment]::GetEnvironmentVariable('DEPLOY_SSH_HOST')
$sshPort    = [Environment]::GetEnvironmentVariable('DEPLOY_SSH_PORT')
if (-not $sshPort) { $sshPort = '22' }
$sshUser    = [Environment]::GetEnvironmentVariable('DEPLOY_SSH_USER')
$remotePath = [Environment]::GetEnvironmentVariable('DEPLOY_REMOTE_PATH')
if ($remotePath) { $remotePath = $remotePath.TrimEnd('/') }

if (-not $sshHost -or -not $sshUser -or -not $remotePath) {
  Write-Host "ERROR: Set DEPLOY_SSH_HOST, DEPLOY_SSH_USER and DEPLOY_REMOTE_PATH in .env" -ForegroundColor Red
  exit 1
}

# Guard: the deploy wipes remotePath, allow only the project webroot.
$expectedPath = '/var/www/ege.nayanovaacademy.ru/public'
if ($remotePath -ne $expectedPath) {
  Write-Host ("ERROR: wrong DEPLOY_REMOTE_PATH=$remotePath, expected=$expectedPath. Deploy aborted.") -ForegroundColor Red
  exit 1
}

$identityFile = [Environment]::GetEnvironmentVariable('DEPLOY_SSH_KEY')
# Относительный путь к ключу разрешаем от каталога скрипта, а не от CWD.
if ($identityFile -and -not [System.IO.Path]::IsPathRooted($identityFile)) {
  $identityFile = Join-Path $PSScriptRoot $identityFile
}
if ($identityFile) {
  if (-not (Test-Path $identityFile)) {
    Write-Host "ERROR: SSH key not found: $identityFile" -ForegroundColor Red
    exit 1
  }
  $identityFile = (Resolve-Path $identityFile).Path
}
$identityArg = if ($identityFile) { "-i `"$identityFile`"" } else { '' }

$remote = "${sshUser}@${sshHost}"
# Внимание: ssh принимает порт как `-p`, а scp — как `-P` (разные ключи).
$sshPortArg = if ($sshPort -ne '22') { "-p $sshPort" } else { '' }
$scpPortArg = if ($sshPort -ne '22') { "-P $sshPort" } else { '' }

# ─── Fix SSH key permissions (Windows OpenSSH requires restrictive ACLs) ───
if ($identityFile -and (Test-Path $identityFile)) {
  $identityFullPath = (Resolve-Path $identityFile).Path
  icacls $identityFullPath /reset 2>$null | Out-Null
  icacls $identityFullPath /inheritance:r 2>$null | Out-Null
  icacls $identityFullPath /grant "${env:USERNAME}:(R)" 2>$null | Out-Null
}

# ─── 2. Build ───
if (-not $SkipBuild) {
  Write-Host "`n==> Building project..." -ForegroundColor Cyan
  if ($DryRun) {
    Write-Host "  [DryRun] python build_site.py" -ForegroundColor Yellow
  } else {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
      Write-Host "ERROR: python not found in PATH" -ForegroundColor Red
      exit 1
    }
    Push-Location $PSScriptRoot
    try {
      & python build_site.py
      if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed" -ForegroundColor Red
        exit 1
      }
    } finally {
      Pop-Location
    }
  }
}

# Проверяем, что сборка создала обязательные страницы.
$requiredFiles = @('index.html', 'documents.html', 'tasks/index.html')
foreach ($rel in $requiredFiles) {
  $full = Join-Path $PSScriptRoot $rel
  if (-not (Test-Path $full)) {
    Write-Host "ERROR: required file not found: $rel" -ForegroundColor Red
    if (-not $DryRun) { exit 1 }
  }
}

# ─── 3. Pack & deploy via tar + scp + ssh ───
$deployId = [guid]::NewGuid().ToString('N')
$markerDir = Join-Path $env:TEMP "ege-marker-$deployId"
$targz = Join-Path $env:TEMP "ege-deploy-$deployId.tar.gz"
$remoteArchive = "/tmp/ege-deploy-$deployId.tar.gz"

New-DeployMarker -ProjectDir $PSScriptRoot -OutFile (Join-Path $markerDir 'version.json')

$excludeArgs = @(
  '--exclude=.git',
  '--exclude=.gitignore',
  '--exclude=.gitattributes',
  '--exclude=.vscode',
  '--exclude=.idea',
  '--exclude=.pytest_cache',
  '--exclude=node_modules',
  '--exclude=__pycache__',
  '--exclude=*.pyc',
  '--exclude=*.pyo',
  '--exclude=*.log',
  '--exclude=*.tar.gz',
  '--exclude=*.swp',
  '--exclude=*.swo',
  '--exclude=*~',
  '--exclude=Thumbs.db',
  '--exclude=.DS_Store',
  '--exclude=Desktop.ini',
  '--exclude=.env',
  '--exclude=deploy.ps1',
  '--exclude=ege.nayanovaacademy.ru'
)

$tarArgs = @('-czf', $targz, '-C', $PSScriptRoot) + $excludeArgs + @('.', '-C', $markerDir, 'version.json')
$remoteScript = "rm -rf $remotePath/* $remotePath/.[!.]* 2>/dev/null; " +
  "mkdir -p $remotePath; " +
  "tar -xzf $remoteArchive -C $remotePath && " +
  "chmod -R a+rX $remotePath && " +
  "rm -f $remoteArchive"
$scpCmd = "scp $scpPortArg $identityArg `"$targz`" ${remote}:$remoteArchive"
$sshCmd = "ssh $sshPortArg $identityArg $remote `"$remoteScript`""

Write-Host "`n==> Deploying to ${remote}:${remotePath} ..." -ForegroundColor Cyan

if ($DryRun) {
  Write-Host "  [DryRun] tar $($tarArgs -join ' ')" -ForegroundColor Yellow
  Write-Host "  [DryRun] $scpCmd" -ForegroundColor Yellow
  Write-Host "  [DryRun] $sshCmd" -ForegroundColor Yellow
  Remove-Item -Recurse -Force $markerDir -ErrorAction SilentlyContinue
  Write-Host "`n==> Deploy complete (dry run)" -ForegroundColor Green
  exit 0
}

$deployFailed = $false
try {
  Write-Host "  Archiving..." -ForegroundColor Gray
  & tar @tarArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Archive creation failed (exit code $LASTEXITCODE)"
  }

  Write-Host "  Uploading..." -ForegroundColor Gray
  cmd /c $scpCmd
  if ($LASTEXITCODE -ne 0) {
    throw "Upload failed (exit code $LASTEXITCODE)"
  }

  Write-Host "  Extracting..." -ForegroundColor Gray
  cmd /c $sshCmd
  if ($LASTEXITCODE -ne 0) {
    throw "Remote extraction failed (exit code $LASTEXITCODE); archive kept at $remoteArchive"
  }

  Write-Host "  Done." -ForegroundColor Green
} catch {
  Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
  $deployFailed = $true
} finally {
  Remove-Item -Force $targz -ErrorAction SilentlyContinue
  Remove-Item -Recurse -Force $markerDir -ErrorAction SilentlyContinue
}
if ($deployFailed) { exit 1 }

# ─── 4. Deploy nginx config (optional, only if a local config exists) ───
$nginxSite = 'ege.nayanovaacademy.ru'
$nginxLocal = Join-Path $PSScriptRoot $nginxSite

if (Test-Path $nginxLocal) {
  Write-Host "`n==> Deploying nginx config ($nginxSite) ..." -ForegroundColor Cyan
  $scpNginxCmd = "scp $scpPortArg $identityArg `"$nginxLocal`" ${remote}:/tmp/nginx-$nginxSite"
  $sshNginxCmd = "ssh $sshPortArg $identityArg $remote `"sudo -n /usr/local/sbin/deploy-nginx.sh $nginxSite`""
  cmd /c $scpNginxCmd
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  Nginx config scp failed" -ForegroundColor Red
    exit 1
  }
  cmd /c $sshNginxCmd
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  Nginx config install/reload failed" -ForegroundColor Red
    exit 1
  }
  Write-Host "  Done." -ForegroundColor Green
}

# ─── 5. Smoke check ───
$siteUrl = [Environment]::GetEnvironmentVariable('SITE_URL')
if (-not $siteUrl) { $siteUrl = 'https://ege.nayanovaacademy.ru/' }

Write-Host "`n==> Smoke check..." -ForegroundColor Cyan
try {
  $resp = Invoke-WebRequest -Uri $siteUrl -Method Head -TimeoutSec 30 -UseBasicParsing
  if ($resp.StatusCode -eq 200) {
    Write-Host "  Site responds with HTTP 200." -ForegroundColor Green
  } else {
    Write-Host "  WARNING: site responded with HTTP $($resp.StatusCode)" -ForegroundColor Yellow
  }
} catch {
  Write-Host "  WARNING: smoke check failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n==> Deploy complete" -ForegroundColor Green
