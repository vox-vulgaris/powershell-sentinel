# Validate that custom-built, non-interactive obfuscation
# module can successfully handle both of the mutually exclusive
# "finisher" branches (Variables and Base64).


$ErrorActionPreference = "Stop"

# Configuration

# 1. The Primitive to Test
$primitive = "Get-LocalGroupMember -Group ""Administrators"""

# 2. The Argument Obfuscation Layers (the "base" for both tests)
$argument_recipe = @(
    'Invoke-SentinelType',
    'Invoke-SentinelType',
    'Invoke-SentinelFormat',
    'Invoke-SentinelFormat',
    'Invoke-SentinelConcat',
    'Invoke-SentinelConcat',
    'Invoke-SentinelConcat'
)

# 3. Define the Finishers
$recipe_A_finisher = 'Invoke-SentinelCommand'
$recipe_B_finisher = 'Invoke-SentinelBase64' # This is now active


# Utility Function
function Apply-ObfuscationChain {
    param(
        [string]$InitialCommand,
        [string[]]$Recipe
    )
    $currentCommand = $InitialCommand
    foreach ($technique in $Recipe) {
        Write-Host "  Applying Layer: $technique ..." -ForegroundColor Yellow
        
        # Directly invoke the function from module
        $obfuscatedOutput = & $technique -Command $currentCommand
        
        if ([string]::IsNullOrWhiteSpace($obfuscatedOutput) -or $obfuscatedOutput.Contains("Error")) {
            throw "Engine failed at layer ($technique). Halting."
        }
        $currentCommand = $obfuscatedOutput
        Write-Host "    [SUCCESS] Layer applied." -ForegroundColor Green
    }
    return $currentCommand
}


# Test Execution

Write-Host "--- Starting Reconstructed Engine Validation ---`n" -ForegroundColor Cyan

# Import custom module (with the new Base64 function)
Import-Module .\PowerShellSentinelObfuscator.psm1 -Force

# --- TEST A: Variables as the Finisher ---
Write-Host "--- TEST A: Finishing with Invoke-SentinelCommand (Variables) ---" -ForegroundColor White
try {
    # Step 1: Apply the complex argument obfuscation chain
    Write-Host "Step 1: Applying Argument Obfuscation Chain..."
    $obfuscated_base_A = Apply-ObfuscationChain -InitialCommand $primitive -Recipe $argument_recipe

    # Step 2: Apply the 'Variables' finisher
    Write-Host "`nStep 2: Applying Finisher ($recipe_A_finisher)..."
    $final_command_A = Apply-ObfuscationChain -InitialCommand $obfuscated_base_A -Recipe @($recipe_A_finisher)

    Write-Host "`n[PASSED] Test A Succeeded." -ForegroundColor Green
    Write-Host "Final Command (A):"
    Write-Host $final_command_A -ForegroundColor Magenta

} catch {
    Write-Host "`n[FAILED] Test A Failed." -ForegroundColor Red
    Write-Host "Error details: $_"
}


# --- TEST B: Base64 as the Finisher ---
Write-Host "`n--- TEST B: Finishing with Invoke-SentinelBase64 ---" -ForegroundColor White
try {
    # Step 1: Apply the same argument obfuscation chain
    Write-Host "Step 1: Applying Argument Obfuscation Chain..."
    $obfuscated_base_B = Apply-ObfuscationChain -InitialCommand $primitive -Recipe $argument_recipe

    # Step 2: Apply the 'Base64' finisher
    Write-Host "`nStep 2: Applying Finisher ($recipe_B_finisher)..."
    $final_command_B = Apply-ObfuscationChain -InitialCommand $obfuscated_base_B -Recipe @($recipe_B_finisher)

    Write-Host "`n[PASSED] Test B Succeeded." -ForegroundColor Green
    Write-Host "Final Command (B):"
    Write-Host $final_command_B -ForegroundColor Magenta

} catch {
    Write-Host "`n[FAILED] Test B Failed." -ForegroundColor Red
    Write-Host "Error details: $_"
}


Write-Host "`n--- Validation Complete ---" -ForegroundColor Cyan