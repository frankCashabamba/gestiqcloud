param(
    [string]$Model = "qwen2.5-coder:3b",
    [switch]$Ping,
    [switch]$Warmup,
    [switch]$AllowCloud,
    [switch]$StopOthers,
    [int]$TimeoutSec = 120,
    [int]$MinContextWarn = 16000
)

$ErrorActionPreference = "Stop"

function Write-Section([string]$Text) {
    Write-Host ""
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Test-OllamaInstalled {
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        throw "ollama not found in PATH."
    }
}

function Set-ClaudeEnvForOllama {
    $env:ANTHROPIC_AUTH_TOKEN = "ollama"
    $env:ANTHROPIC_API_KEY = ""
    $env:ANTHROPIC_BASE_URL = "http://localhost:11434"
}

function Assert-NotCloudModel([string]$ModelName, [switch]$Allow) {
    if (($ModelName -match ":cloud$") -and (-not $Allow)) {
        Write-Host ""
        Write-Host "WARNING: Cloud model detected: $ModelName" -ForegroundColor Red
        Write-Host "This may consume quota/billing." -ForegroundColor Red
        throw "Aborted to avoid cloud usage. Use a local model (no :cloud) or add -AllowCloud."
    }
}

function Get-OllamaPsLines {
    # Returns raw lines from `ollama ps`
    $lines = @(ollama ps 2>$null)
    return $lines
}

function Show-OllamaPs {
    Write-Section "ollama ps"
    ollama ps
}

function Get-LoadedModelNames {
    $lines = Get-OllamaPsLines
    if (-not $lines -or $lines.Count -lt 2) { return @() }

    $names = @()
    foreach ($line in $lines | Select-Object -Skip 1) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        # Split on 2+ spaces (table columns)
        $parts = $line -split '\s{2,}'
        if ($parts.Count -ge 1 -and -not [string]::IsNullOrWhiteSpace($parts[0])) {
            $names += $parts[0].Trim()
        }
    }
    return $names
}

function Stop-OtherLoadedModels([string]$KeepModel) {
    Write-Section "Stop other loaded models"
    $loaded = Get-LoadedModelNames
    if (-not $loaded -or $loaded.Count -eq 0) {
        Write-Host "No loaded models found."
        return
    }

    $stoppedAny = $false
    foreach ($m in $loaded) {
        if ($m -ne $KeepModel) {
            try {
                Write-Host "Stopping: $m" -ForegroundColor Yellow
                ollama stop $m | Out-Null
                $stoppedAny = $true
            } catch {
                Write-Warning "Could not stop $m"
            }
        }
    }

    if (-not $stoppedAny) {
        Write-Host "No other models to stop."
    }
}

function Get-ModelContextFromPs([string]$ModelName) {
    $lines = Get-OllamaPsLines
    if (-not $lines -or $lines.Count -lt 2) { return $null }

    foreach ($line in $lines | Select-Object -Skip 1) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line -split '\s{2,}'
        # Expected: NAME, ID, SIZE, PROCESSOR, CONTEXT, UNTIL
        if ($parts.Count -ge 5) {
            $name = $parts[0].Trim()
            $ctx  = $parts[4].Trim()
            if ($name -eq $ModelName) {
                if ($ctx -match '^\d+$') { return [int]$ctx }
                return $null
            }
        }
    }
    return $null
}

function Warn-IfLowContext([string]$ModelName, [int]$MinWarn) {
    $ctx = Get-ModelContextFromPs -ModelName $ModelName
    if ($null -eq $ctx) {
        Write-Host "Context check: could not determine context for $ModelName" -ForegroundColor Yellow
        return
    }

    if ($ctx -lt $MinWarn) {
        Write-Host ("WARNING: Context is low for Claude Code agent use: {0} (recommended test >= {1})" -f $ctx, $MinWarn) -ForegroundColor Yellow
        Write-Host "Tip: increase Ollama context length (try 16000, 32000, then 64000 if your machine can handle it)." -ForegroundColor Yellow
    } else {
        Write-Host ("Context check OK: {0}" -f $ctx) -ForegroundColor Green
    }
}

function Test-OllamaEndpointPing([string]$ModelName, [int]$Timeout) {
    Write-Section "Ping local Ollama /api/generate"

    $body = @{
        model = $ModelName
        prompt = "Reply exactly: OK"
        stream = $false
        options = @{
            num_predict = 2
            temperature = 0
        }
    } | ConvertTo-Json -Depth 5

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod `
            -Method Post `
            -Uri "http://localhost:11434/api/generate" `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec $Timeout

        $sw.Stop()
        Write-Host ("Ping OK in {0:N1}s" -f $sw.Elapsed.TotalSeconds) -ForegroundColor Green

        if ($null -ne $resp.response) {
            Write-Host ("Response: " + ($resp.response.Trim())) -ForegroundColor DarkGreen
        } else {
            Write-Host "Response received, but no 'response' field found." -ForegroundColor Yellow
        }
    }
    catch {
        $sw.Stop()
        Write-Host ("Ping FAILED after {0:N1}s" -f $sw.Elapsed.TotalSeconds) -ForegroundColor Red
        throw
    }
}

function Invoke-Warmup([string]$ModelName) {
    Write-Section "Warmup (optional; can be slow on CPU)"
    Write-Host "Model: $ModelName"
    ollama run $ModelName "Reply exactly: OK"
}

# Main
Write-Host "Claude Code + Ollama (local mode)" -ForegroundColor Green
Write-Host "Requested model: $Model"

Test-OllamaInstalled
Assert-NotCloudModel -ModelName $Model -Allow:$AllowCloud
Set-ClaudeEnvForOllama

Write-Host "BASE_URL: $env:ANTHROPIC_BASE_URL"

if ($Model -match ":cloud$") {
    Write-Host "Expected mode: CLOUD" -ForegroundColor Yellow
} else {
    Write-Host "Expected mode: LOCAL" -ForegroundColor Green
}

if ($StopOthers) {
    Stop-OtherLoadedModels -KeepModel $Model
}

if ($Ping) {
    Test-OllamaEndpointPing -ModelName $Model -Timeout $TimeoutSec
}

if ($Warmup) {
    Invoke-Warmup -ModelName $Model
}

Show-OllamaPs
Warn-IfLowContext -ModelName $Model -MinWarn $MinContextWarn

Write-Section "Launching Claude Code"
Write-Host "Command: ollama launch claude --model $Model" -ForegroundColor Yellow
ollama launch claude --model $Model
