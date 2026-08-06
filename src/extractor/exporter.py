import json
import csv
import os
from typing import List, Dict, Any, Union

class DataExporter:
    """
    Exports structured records into JSON, CSV, or Markdown format.
    """

    @staticmethod
    def to_json(data: Union[List[Dict[str, Any]], Dict[str, Any]], filepath: str) -> str:
        """Saves records to a formatted JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    @staticmethod
    def to_csv(data: List[Dict[str, Any]], filepath: str) -> str:
        """Saves a list of dictionary records to a CSV file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        if not data:
            with open(filepath, "w", encoding="utf-8") as f:
                pass
            return filepath

        headers = list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        return filepath

    @staticmethod
    def to_markdown_table(data: List[Dict[str, Any]]) -> str:
        """Converts a list of records into a GitHub-flavored Markdown table."""
        if not data:
            return "*No data extracted.*"

        headers = list(data[0].keys())
        header_row = "| " + " | ".join(headers) + " |"
        separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"

        data_rows = []
        for record in data:
            row_vals = [str(record.get(h, "")).replace("|", "\\|").replace("\n", " ") for h in headers]
            data_rows.append("| " + " | ".join(row_vals) + " |")

        return "\n".join([header_row, separator_row] + data_rows)
