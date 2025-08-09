# tests/test_evaluate_pipeline.py

import unittest
from collections import Counter
from unittest.mock import patch, mock_open

from scripts.evaluate_pipeline import infer_techniques_from_prompt, analyze_failures, analyze_decoded_content

class TestEvaluationPipeline(unittest.TestCase):

    def test_infer_techniques_from_prompt(self):
        """Tests the logic for inferring obfuscation techniques from a prompt string."""
        prompt1 = "powershell.exe -EncodedCommand SQBu..."
        expected1 = {'obfuscate_base64', 'layered_technique_inside_base64'}
        self.assertEqual(infer_techniques_from_prompt(prompt1), expected1)
        
        prompt2 = "$a='Get';$b='-Process';Invoke-Expression($a+$b)"
        expected2 = {'obfuscate_variables', 'obfuscate_concat'}
        self.assertEqual(infer_techniques_from_prompt(prompt2), expected2)

    def test_analyze_failures_logic(self):
        """Tests the failure analysis logic by checking the counted data directly."""
        mock_log_data = """
        {"primitive_id": "PS-001", "obfuscation_chain": ["obfuscate_variables", "obfuscate_base64"]}
        {"primitive_id": "PS-001", "obfuscation_chain": ["obfuscate_format_operator"]}
        {"primitive_id": "PS-045", "obfuscation_chain": ["obfuscate_types", "obfuscate_variables"]}
        """
        
        from rich.console import Console
        console = Console()

        with patch('collections.Counter.update') as mock_update:
            with patch("builtins.open", mock_open(read_data=mock_log_data)):
                analyze_failures(console, "dummy_log_path.log")

        all_updates = [c.args[0] for c in mock_update.call_args_list]
        
        # Now that the production code uses .update for primitives, this will work.
        self.assertIn(['PS-001'], all_updates)
        self.assertIn(['PS-045'], all_updates)
        self.assertIn(['obfuscate_variables', 'obfuscate_base64'], all_updates)


    def test_analyze_decoded_content_logic(self):
        """
        Tests the Base64 content analysis logic by checking the counted data directly.
        """
        mock_dataset_data = """
        [
            { "prompt": "powershell.exe -EncodedCommand SQBuAHYAbwBrAGUALQBFAHgAcAByAGUAcwBzAGkAbwBuACgAJwBnAGUAdAAnACsAJwAtAHAAcgBvAGMAZQBzAHMAJwApAA==" },
            { "prompt": "powershell.exe -EncodedCommand JABhAD0AJwBnAGUAdAAnADsAJABiAD0AJwAtAHAAcgBvAGMAZQBzAHMAJwA7AGkAZQB4ACAAJABhACsAJABiAA==" }
        ]
        """
        
        from rich.console import Console
        console = Console()
        import json
        mock_dataset = json.loads(mock_dataset_data)

        with patch('collections.Counter.update') as mock_update:
             with patch("random.sample", lambda population, k: population[:k]):
                analyze_decoded_content(console, mock_dataset, sample_size=2)
        
        update_calls = [c.args[0] for c in mock_update.call_args_list]
        
        self.assertIn({'obfuscate_concat'}, update_calls)
        self.assertIn({'obfuscate_variables', 'obfuscate_concat'}, update_calls)

if __name__ == '__main__':
    unittest.main()