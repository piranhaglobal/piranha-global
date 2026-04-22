import json
from pathlib import Path

LISTS_PATH = Path(__file__).parent.parent / "data" / "klaviyo_lists.json"


def load_klaviyo_lists() -> list[dict]:
    if not LISTS_PATH.exists():
        return []
    try:
        data = json.loads(LISTS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_klaviyo_lists(lists: list[dict]) -> None:
    LISTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LISTS_PATH.write_text(json.dumps(lists, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_klaviyo_list(item: dict) -> list[dict]:
    lists = load_klaviyo_lists()
    existing = next((entry for entry in lists if entry["id"] == item["id"]), None)
    if existing:
        existing.update(item)
    else:
        lists.append(item)
    save_klaviyo_lists(lists)
    return lists


def delete_klaviyo_list(list_id: str) -> list[dict]:
    lists = [entry for entry in load_klaviyo_lists() if entry["id"] != list_id]
    save_klaviyo_lists(lists)
    return lists
