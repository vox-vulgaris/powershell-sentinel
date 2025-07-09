# Phase 3: Data Factory - Generation & MLOps Prep
# Index: [10]
#
# This module is the creative engine of the data factory. It is responsible for
# taking a clean, primitive PowerShell command and applying multiple layers of
# obfuscation to generate a complex, realistic-looking malicious command.
#
# REQUIREMENTS (per v1.3 blueprint):
# 1. Must implement at least 5 distinct, separate functions for individual obfuscation techniques
#    (e.g., concatenation, Base64, backticks, variables, format operator).
# 2. Must include a master function, `generate_layered_obfuscation(command)`, that orchestrates these techniques.
# 3. The master function must apply a randomized chain of 1-4 UNIQUE techniques. A technique
#    should not be applied twice consecutively in the same chain to avoid redundancy.
# 4. The module must be self-contained and not rely on external state.

import base64
import random

def obfuscate_concat(command: str) -> str:
    """Obfuscates a command using string concatenation."""
    # TODO: Implement logic. Split the command into parts and join with '+'.
    # E.g., "Get-Process" -> "'Get' + '-' + 'Process'"
    parts = [command[i:i+random.randint(2, 5)] for i in range(0, len(command), random.randint(2, 5))]
    return "'" + "' + '".join(parts) + "'"

def obfuscate_base64(command: str) -> str:
    """Obfuscates a command using Base64 encoding."""
    # TODO: Implement logic.
    # E.g., "Get-Process" -> "powershell -e <base64_string>"
    encoded_bytes = base64.b64encode(command.encode('utf-16le'))
    encoded_str = encoded_bytes.decode('ascii')
    return f"powershell.exe -EncodedCommand {encoded_str}"

def obfuscate_backticks(command: str) -> str:
    """Obfuscates a command by hiding parts of it in strings with backticks."""
    # TODO: Implement more robust logic.
    # E.g., "Get-Process" -> "Get-Pr`oce`ss"
    if len(command) < 3:
        return command
    insert_pos = random.randint(1, len(command) - 2)
    return f'{command[:insert_pos]}`{command[insert_pos:]}'

# TODO: Implement at least 2 more obfuscation functions (e.g., variables, format operator).

def generate_layered_obfuscation(command: str) -> tuple[str, list[str]]:
    """
    Applies a randomized chain of 1-4 unique obfuscation techniques.

    Args:
        command: The clean PowerShell command to obfuscate.

    Returns:
        A tuple containing:
        - The final, multi-layered obfuscated command string.
        - A list of the names of the obfuscation functions that were applied, in order.
    """
    # TODO: Implement the master logic.
    # 1. Create a list of all available obfuscation functions.
    # 2. Choose a number of layers to apply (k, from 1 to 4).
    # 3. Randomly sample k UNIQUE functions from the list.
    # 4. Initialize `obfuscated_command = command`.
    # 5. Loop through the selected functions, applying each one to the result of the previous.
    # 6. Keep track of the function names applied in a list (`chain_used`).
    # 7. Return the final command and the chain.

    # Dummy implementation for structure
    obfuscation_functions = [obfuscate_concat, obfuscate_base64, obfuscate_backticks]
    num_layers = random.randint(1, min(len(obfuscation_functions), 4))
    chosen_funcs = random.sample(obfuscation_functions, k=num_layers)
    
    obfuscated_command = command
    chain_used = []
    for func in chosen_funcs:
        obfuscated_command = func(obfuscated_command)
        chain_used.append(func.__name__)
        
    return obfuscated_command, chain_used