# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [10]
#
# This module is the creative engine of the data factory. It is responsible for
# taking a clean, primitive PowerShell command and applying multiple layers of
# obfuscation to generate a complex, realistic-looking malicious command.

import base64
import random
import string
import re

def obfuscate_concat(command: str) -> str:
    """[FIX] Obfuscates a command into an executable Invoke-Expression call using string concatenation."""
    if not command:
        return "''"
    parts = []
    i = 0
    while i < len(command):
        chunk_size = random.randint(3, 10)
        part = command[i:i+chunk_size]
        part = part.replace("'", "''")
        parts.append(f"'{part}'")
        i += chunk_size
    concatenated_string = "+".join(parts)
    # Wrap in Invoke-Expression to ensure execution
    return f"Invoke-Expression({concatenated_string})"

def obfuscate_base64(command: str) -> str:
    """Base64 encodes a command string for execution via -EncodedCommand."""
    encoded_bytes = base64.b64encode(command.encode('utf-16le'))
    encoded_str = encoded_bytes.decode('ascii')
    return f"powershell.exe -EncodedCommand {encoded_str}"

def obfuscate_types(command: str) -> str:
    """Obfuscates a command using type casting, returning an executable string."""
    parts = re.split(r'(\s+)', command)
    obfuscated_parts = []
    for part in parts:
        if re.match(r'^\w{3,}$', part):
            chars = "', '".join(list(part))
            obfuscated_parts.append(f"&([string]::new('{chars}'))")
        else:
            obfuscated_parts.append(part)
    return "".join(obfuscated_parts)

def obfuscate_variables(command: str) -> str:
    """
    [FIX] Splits a command by spaces, assigns parts to variables, and correctly executes them using '+' for concatenation.
    """
    parts = command.split(' ')
    var_names = [f"${''.join(random.choices(string.ascii_lowercase, k=5))}" for _ in parts]
    
    assignments = []
    for var, part in zip(var_names, parts):
        if part:
            escaped_part = part.replace("'", "''")
            assignments.append(f"{var}='{escaped_part}'")
    
    assignment_block = ';'.join(assignments)
    # [FIX] The correct way to join variables for execution is with the '+' and space separators.
    execution_block = "+' '+".join(var_names)
    
    return f"{assignment_block};Invoke-Expression({execution_block})"

def obfuscate_format_operator(command: str) -> str:
    """[FIX] Obfuscates using the format operator, wrapping in Invoke-Expression."""
    escaped_command = command.replace("'", "''").replace('{', '{{').replace('}', '}}')
    # Wrap the entire command in a format operation that simply reconstructs the original string
    return f"Invoke-Expression ('{{0}}' -f '{escaped_command}')"


# --- Master Orchestration Function ---

def generate_layered_obfuscation(command: str) -> tuple[str, list[str]]:
    """
    Applies a robust, layered obfuscation strategy by separating syntax modifications
    from command wrappers.
    """
    # [FIX] Removed the unstable backticks function from the pool of available obfuscators.
    wrapper_obfuscators = [
        obfuscate_concat,
        obfuscate_variables,
        obfuscate_format_operator,
        obfuscate_types
    ]
    
    obfuscated_command = command
    chain_used = []

    # Apply one or two layers of command wrapping
    num_wrappers = random.randint(1, 2)
    chosen_wrappers = random.sample(wrapper_obfuscators, k=num_wrappers)
    for func in chosen_wrappers:
        obfuscated_command = func(obfuscated_command)
        chain_used.append(func.__name__)

    # Optional final Base64 encoding layer
    if random.choice([True, False]):
        obfuscated_command = obfuscate_base64(obfuscated_command)
        chain_used.append("obfuscate_base64")
        
    return obfuscated_command, chain_used