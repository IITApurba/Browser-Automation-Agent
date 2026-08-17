import json
import os


async def login(
    toolkit,
    url: str,
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    username: str,
    password: str,
) -> dict:
    await toolkit.navigate(url)
    await toolkit.type_text(username_selector, username)
    await toolkit.type_text(password_selector, password)
    await toolkit.click(submit_selector)
    return await toolkit._context.storage_state()


def save_storage_state(state: dict, path: str) -> None:
    """File-based persistence for now. In the DB-backed variant this would
    serialize `state` into the Session model's `storage_state` column instead
    of (or in addition to) a JSON file on disk.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)


def load_storage_state(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
