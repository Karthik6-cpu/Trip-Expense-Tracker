"""Read and write the single trip file."""

import json
from pathlib import Path


class StoreError(Exception):
    """The trip file could not be read or written."""


def empty_trip():
    return {
        "nextFriendId": 1,
        "nextExpenseId": 1,
        "friends": [],
        "expenses": [],
    }


class Store:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            data = empty_trip()
            self.save(data)
            return data
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StoreError("The trip file could not be read.") from exc
        if not isinstance(data, dict):
            raise StoreError("The trip file could not be read.")
        return data

    def save(self, data):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + ".tmp")
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError as exc:
            raise StoreError("The trip file could not be written.") from exc
