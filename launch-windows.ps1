#Requires -Version 5.1
<#
  Одиссея - нативный запуск на Windows (без Docker).

  Создаёт виртуальное окружение, устанавливает зависимости, выполняет
  первичную настройку и запускает сервер. Безопасно запускать повторно.

  Использование:
    powershell -ExecutionPolicy Bypass -File .\launch-windows.ps1
    powershell -ExecutionPolicy Bypass -File .\launch-windows.ps1 -Port 7000 -BindHost 127.0.0.1
#>
param(
    [int]$Port = 7000,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host ""; Write-Host ("==> " + $msg) -ForegroundColor Cyan }
function Fail($msg) {
    Write-Host ""
    Write-Host ("ОШИБКА: " + $msg) -ForegroundColor Red
    Write-Host ""
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

function Find-GitBash {
    $cmd = Get-Command bash -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $roots = @()
    foreach ($name in @("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LocalAppData")) {
        $base = [Environment]::GetEnvironmentVariable($name)
        if ($base) { $roots += (Join-Path $base "Git") }
    }
    $roots += @("C:\Program Files\Git", "C:\Program Files (x86)\Git")

    foreach ($root in ($roots | Select-Object -Unique)) {
        foreach ($relative in @("bin\bash.exe", "usr\bin\bash.exe")) {
            $candidate = Join-Path $root $relative
            if (Test-Path $candidate) { return $candidate }
        }
    }
    return $null
}

# 1. Поиск интерпретатора Python (требуется 3.11+)
Write-Step "Проверка Python"
function Get-PythonVersionText($launcher, $launcherArgs) {
    try {
        return (& $launcher @launcherArgs -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null).Trim()
    } catch {
        return $null
    }
}

$pyExe = $null
$pyArgs = @()
$pyVersion = $null

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    foreach ($v in @("-3.13", "-3.12", "-3.11")) {
        $ver = Get-PythonVersionText $pyLauncher.Source @($v)
        if ($ver) {
            $pyExe = $pyLauncher.Source
            $pyArgs = @($v)
            $pyVersion = $ver
            break
        }
    }
}

if (-not $pyExe) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $ver = Get-PythonVersionText $pythonCmd.Source @()
        if ($ver) {
            $versionParts = $ver.Split('.')
            $major = [int]$versionParts[0]
            $minor = [int]$versionParts[1]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                $pyExe = $pythonCmd.Source
                $pyVersion = $ver
            }
        }
    }
}

if (-not $pyExe) {
    Fail "Python 3.11+ не найден. Установите с https://www.python.org/downloads/ и запустите скрипт снова."
}
$pythonLabel = ("Используется Python {0}: {1} {2}" -f $pyVersion, $pyExe, ($pyArgs -join ' ')).TrimEnd()
Write-Host $pythonLabel

# 2. Создание виртуального окружения
$venvPy = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Step "Создание виртуального окружения (venv)"
    & $pyExe @pyArgs -m venv venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPy)) { Fail "Не удалось создать виртуальное окружение." }
} else {
    Write-Host "Виртуальное окружение уже существует — пропуск."
}

# 3. Установка зависимостей
Write-Step "Установка зависимостей (первый запуск может занять несколько минут)"
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "Установка зависимостей завершилась с ошибкой. Прокрутите вверх для просмотра ошибки pip." }

# 4. Первичная настройка
Write-Step "Первичная настройка"
& $venvPy setup.py
if ($LASTEXITCODE -ne 0) { Fail "setup.py завершился с ошибкой." }

# 5. Проверка Git Bash
if (-not (Find-GitBash)) {
    Write-Host ""
    Write-Host "ПРИМЕЧАНИЕ: Git Bash (bash.exe) не найден." -ForegroundColor Yellow
    Write-Host "  Для полного функционала Каталога моделей и shell-агента" -ForegroundColor Yellow
    Write-Host "  установите Git for Windows: https://git-scm.com/download/win" -ForegroundColor Yellow
}

# 6. Запуск сервера
Write-Step ("Запуск Одиссеи: http://{0}:{1}" -f $BindHost, $Port)
Write-Host "Для остановки нажмите Ctrl+C."
Write-Host ""
& $venvPy -m uvicorn app:app --host $BindHost --port $Port