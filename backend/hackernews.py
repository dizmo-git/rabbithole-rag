import requests
import json
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
MAX_WORKERS = 10


def fetch_item(item_id: int):
    resp = requests.get(BASE_URL.format(item_id), timeout=5)
    resp.raise_for_status()
    return resp.json()


def fetch_tree(item_id: int):
    item = fetch_item(item_id)
    if item is None:
        return None

    kids = item.get("kids", [])
    if kids:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            children = list(executor.map(fetch_tree, kids))
        item["children"] = [c for c in children if c is not None]

    return item


def test_hn():
    root_id = 48844345
    tree = fetch_tree(root_id)
    print(json.dumps(tree, indent=2))  # truncate, full threads get huge

    # quick sanity counts
    def count_nodes(node):
        if node is None:
            return 0
        return 1 + sum(count_nodes(c) for c in node.get("children", []))

    print(f"\nTotal nodes fetched: {count_nodes(tree)}")
