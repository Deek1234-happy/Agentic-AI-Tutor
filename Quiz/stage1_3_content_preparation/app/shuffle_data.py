"""
Shuffle data from JSONL file and save to a new file.
"""

import json
import random
from pathlib import Path

def shuffle_jsonl(input_path: str, output_path: str, seed: int = None) -> None:
    """
    Load JSONL file, shuffle all records, and write to output file.
    
    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSONL file
        seed: Optional random seed for reproducibility
    """
    if seed is not None:
        random.seed(seed)
    
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Load all records
    records = []
    with open(input_file, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"Warning: Skipping malformed line {line_num}: {exc}")
    
    print(f"Loaded {len(records)} records from {input_file.name}")
    
    # Shuffle
    random.shuffle(records)
    print(f"Shuffled {len(records)} records")
    
    # Write to output file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"Saved shuffled data to {output_file}")
    print(f"Output file: {output_file.absolute()}")


if __name__ == "__main__":
    input_file = r"C:\Graduation Project\Quiz\data\metadata\selected_subset_v2_unique_by_chunk_id.jsonl"
    output_file = r"C:\Graduation Project\Quiz\data\metadata\selected_subset_v2_unique_by_chunk_id_shuffled.jsonl"
    
    shuffle_jsonl(input_file, output_file)
