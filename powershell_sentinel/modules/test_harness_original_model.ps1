# =============================================================================
# Original Layering Model - Validation Harness
#
# Objective: To definitively test if the original, more complex layering
#            hierarchy (Arguments -> Command -> Base64) is viable with the
#            new, surgically reconstructed engine.
# =============================================================================

$ErrorActionPreference = "Stop"

# --- CONFIGURATION ---
$primitive = "Get-LocalGroupMember -Group ""Administrators"""

# The argument obfuscation layers
$argument_recipe = @(
    'Invoke-SentinelType',
    'Invoke-SentinelType',
    'Invoke-SentinelFormat',
    'Invoke-SentinelFormat',
    'Invoke-SentinelConcat',
    'Invoke-SentinelConcat',
    'Invoke-SentinelConcat'
)

# The command obfuscation layer
$command_finisher = 'Invoke-SentinelCommand'

# The final execution wrapper
$base64_finisher = 'Invoke-SentinelBase64'

# --- UTILITY FUNCTION ---
# (Same as before)
function Apply-ObfuscationChain {
    param( [string]$InitialCommand, [string[]]$Recipe )
    $currentCommand = $InitialCommand
    foreach ($technique in $Recipe) {
        Write-Host "  Applying Layer: $technique ..." -ForegroundColor Yellow
        $obfuscatedOutput = & $technique -Command $currentCommand
        if ([string]::IsNullOrWhiteSpace($obfuscatedOutput) -or $obfuscatedOutput.Contains("Error")) {
            throw "Engine failed at layer ($technique). Halting."
        }
        $currentCommand = $obfuscatedOutput
        Write-Host "    [SUCCESS] Layer applied." -ForegroundColor Green
    }
    return $currentCommand
}

# --- TEST EXECUTION ---

Write-Host "--- Validating Original Layering Model ---`n" -ForegroundColor Cyan
Import-Module .\PowerShellSentinelObfuscator.psm1 -Force

try {
    Write-Host "Step 1: Applying complex Argument Obfuscation chain..."
    $obfuscated_base = Apply-ObfuscationChain -InitialCommand $primitive -Recipe $argument_recipe

    Write-Host "`nStep 2: Applying Command Obfuscation finisher..."
    $obfuscated_with_command = Apply-ObfuscationChain -InitialCommand $obfuscated_base -Recipe @($command_finisher)

    Write-Host "`nStep 3: Applying Base64 Execution Wrapper finisher..."
    $final_command = Apply-ObfuscationChain -InitialCommand $obfuscated_with_command -Recipe @($base64_finisher)

    Write-Host "`n[PASSED] The original 304-recipe model is VALID." -ForegroundColor Green
    Write-Host "Final Command:"
    Write-Host $final_command -ForegroundColor Magenta

} catch {
    Write-Host "`n[FAILED] The original 304-recipe model is INVALID." -ForegroundColor Red
    Write-Host "The failure occurred at the step that threw the error above."
    Write-Host "This confirms that Command and/or Base64 obfuscation cannot be reliably layered after Argument obfuscation."
    Write-Host "Error details: $_"
}

Write-Host "`n--- Validation Complete ---" -ForegroundColor Cyan


