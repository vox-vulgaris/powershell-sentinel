import sys
sys.path.append('.') 
from powershell_sentinel.main_data_factory import invoke_sentinel_engine

print("--- Running Integration Test: SUCCESS CASE ---")
print("Testing with: whoami -> Invoke-SentinelConcat")
success, result = invoke_sentinel_engine("whoami", "Invoke-SentinelConcat")
if success and "+'" in result:
    print("    [PASS] Engine returned obfuscated command successfully.")
    print(f"    Result: {result}\n")
else:
    print("    [FAIL] Engine did not return a valid obfuscated command.")
    print(f"    Result: {result}\n")


print("--- Running Integration Test: FAILURE CASE ---")
print("Testing with: whoami -> Invoke-NonExistentFunction")
success, result = invoke_sentinel_engine("whoami", "Invoke-NonExistentFunction")
if not success and "ENGINE_ERROR" in result:
    print("    [PASS] Engine correctly handled a failure.")
    print(f"    Result: {result}\n")
else:
    print("    [FAIL] Engine did not correctly report the failure.")
    print(f"    Result: {result}\n")