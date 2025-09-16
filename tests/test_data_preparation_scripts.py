# tests/test_data_preparation_scripts.py
import unittest
import json
import os

def deduplicate_dataset(input_path: str, output_path: str):
    """
    Loads a dataset, removes entries with duplicate prompts, and saves the
    clean dataset to a new file.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        original_dataset = json.load(f)

    seen_prompts = set()
    deduped_data = []
    for item in original_dataset:
        if item['prompt'] not in seen_prompts:
            deduped_data.append(item)
            seen_prompts.add(item['prompt'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(deduped_data, f)


class TestDataPreparationScripts(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory and dummy data for tests."""
        self.test_dir = "temp_test_data"
        os.makedirs(self.test_dir, exist_ok=True)
        self.dummy_data = [
            {"prompt": "A", "response": "1"},
            {"prompt": "B", "response": "2"},
            {"prompt": "A", "response": "3"}, # Duplicate prompt
            {"prompt": "C", "response": "4"},
            {"prompt": "B", "response": "5"}, # Duplicate prompt
        ]
        self.input_path = os.path.join(self.test_dir, "dummy_input.json")
        with open(self.input_path, "w") as f:
            json.dump(self.dummy_data, f)

    def tearDown(self):
        """Clean up the temporary directory and files after tests."""
        if os.path.exists(self.test_dir):
            for file_name in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file_name))
            os.rmdir(self.test_dir)

    def test_deduplication_logic(self):
        """
        Tests that the deduplication logic correctly removes
        redundant entries based on the 'prompt' key.
        """
        output_path = os.path.join(self.test_dir, "dummy_output.json")
        # Call the local version of the function
        deduplicate_dataset(self.input_path, output_path)

        self.assertTrue(os.path.exists(output_path))

        with open(output_path, "r") as f:
            clean_data = json.load(f)

        self.assertEqual(len(clean_data), 3)
        prompts = [item['prompt'] for item in clean_data]
        self.assertListEqual(prompts, ["A", "B", "C"])

if __name__ == '__main__':
    unittest.main()