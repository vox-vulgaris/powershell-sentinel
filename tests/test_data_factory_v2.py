import os
import json
import pytest
from powershell_sentinel.main_data_factory import (
    generate_all_recipes,
    load_state,
    save_state,
    log_audit_event,
    invoke_sentinel_engine,
    EXCLUSION_LIST
)
from powershell_sentinel.models import TrainingPair, LLMResponse, Analysis, IntentEnum, MitreTTPEnum

# --- Unit Tests ---

def test_generate_all_recipes_count():
    """Tests if the recipe generator creates the correct number of combinations."""
    recipes = generate_all_recipes()
    # Validated Model: 76 (Argument Recipes) * 3 (Finishers) = 228
    assert len(recipes) == 228

def test_generate_all_recipes_content():
    """Sanity-checks the first and last recipes."""
    recipes = generate_all_recipes()
    # The first recipe should always be the "do nothing" recipe
    assert recipes[0] == []
    # The last recipe should be the most complex possible combination
    last_recipe = recipes[-1]
    assert 'Invoke-SentinelType' in last_recipe
    assert 'Invoke-SentinelConcat' in last_recipe
    assert 'Invoke-SentinelBase64' in last_recipe
    assert 'Invoke-SentinelCommand' not in last_recipe # Command and Base64 are mutually exclusive

def test_state_management(tmpdir):
    """Tests saving and loading of the dataset and completion log."""
    # Setup dummy data
    output_file = os.path.join(tmpdir, "test_dataset.json")
    log_file = os.path.join(tmpdir, "test_log.json")

    analysis = Analysis(intent=[IntentEnum.PROCESS_DISCOVERY], mitre_ttps=[MitreTTPEnum.T1057], telemetry_signature=[])
    response = LLMResponse(deobfuscated_command="whoami", analysis=analysis)
    dummy_pairs = [TrainingPair(prompt="whoami", response=response)]
    dummy_jobs = {("PS-001", ("Invoke-SentinelConcat",))}

    # Test saving
    save_state(dummy_pairs, dummy_jobs, output_file, log_file)
    assert os.path.exists(output_file)
    assert os.path.exists(log_file)

    # Test loading
    loaded_pairs, loaded_jobs = load_state(output_file, log_file)
    assert len(loaded_pairs) == 1
    assert loaded_pairs[0].prompt == "whoami"
    assert ("PS-001", ("Invoke-SentinelConcat",)) in loaded_jobs

def test_audit_logging(tmpdir):
    """Tests if the audit log function correctly writes a JSON line."""
    audit_file = os.path.join(tmpdir, "audit.jsonl")
    log_audit_event(
        "PS-009", ["Invoke-SentinelConcat"], "success", audit_log_path=audit_file
    )
    assert os.path.exists(audit_file)
    with open(audit_file, 'r') as f:
        line = f.readline()
        log_entry = json.loads(line)
        assert log_entry["primitive_id"] == "PS-009"
        assert log_entry["status"] == "success"

# --- Integration Tests ---

@pytest.mark.slow
def test_invoke_sentinel_engine_success():
    """
    CRITICAL: Tests the full Python -> PowerShell bridge with a valid command.
    This test requires PowerShell and the custom module to be correctly located.
    """
    success, result = invoke_sentinel_engine("whoami", "Invoke-SentinelConcat")
    assert success is True
    assert result is not None
    assert "whoami" not in result # The command should be obfuscated
    assert "+'" in result or "'+'" in result # Should contain concatenation artifacts

@pytest.mark.slow
def test_invoke_sentinel_engine_ps_error():
    """Tests if the bridge gracefully handles an error from the PowerShell script."""
    # Pass a non-existent function name
    success, result = invoke_sentinel_engine("whoami", "Invoke-NonExistentFunction")
    assert success is False
    assert "ENGINE_ERROR" in result
    assert "is not recognized" in result # Should contain PowerShell's error message