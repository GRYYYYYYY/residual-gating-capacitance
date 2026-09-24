from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any


def load_manifest(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("schema_version") != 1:
        raise ValueError("Unsupported sources manifest")
    return value


def _read_json_url(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "openrcbench/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def expand_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand pinned GitHub collections to immutable source records."""

    result = list(manifest.get("sources", []))
    for collection in manifest.get("github_collections", []):
        repository = collection["repository"]
        commit = collection["commit"]
        tree_url = f"https://api.github.com/repos/{repository}/git/trees/{commit}?recursive=1"
        tree = _read_json_url(tree_url)
        pattern = re.compile(collection["path_regex"])
        for item in tree.get("tree", []):
            source_path = item.get("path", "")
            if item.get("type") != "blob" or not pattern.fullmatch(source_path):
                continue
            name = Path(source_path).name
            corner = name.rsplit("_", 1)[-1].removesuffix(".rules")
            result.append(
                {
                    "source_id": f"{collection['collection_id']}:{name}",
                    "process_id": collection["process_id"],
                    "corner_id": corner,
                    "format": collection["format"],
                    "path": f"{collection['output_dir']}/{name}",
                    "url": f"https://raw.githubusercontent.com/{repository}/{commit}/{source_path}",
                    "git_blob_sha": item["sha"],
                    "license": collection["license"],
                    "commit": commit,
                    "redistributable": collection.get("redistributable", False),
                }
            )
    result.sort(key=lambda x: x["source_id"])
    return result


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_sources(manifest_path: str | Path, raw_dir: str | Path) -> list[Path]:
    manifest = load_manifest(manifest_path)
    root = Path(raw_dir)
    downloaded: list[Path] = []
    for source in expand_sources(manifest):
        destination = root / source["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        valid = destination.exists() and _source_hash_matches(destination.read_bytes(), source)
        if not valid:
            request = urllib.request.Request(
                source["url"], headers={"User-Agent": "openrcbench/0.1"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            if not _source_hash_matches(payload, source):
                raise ValueError(
                    f"Hash mismatch for immutable source {source['source_id']}"
                )
            destination.write_bytes(payload)
        downloaded.append(destination)
    return downloaded


def _source_hash_matches(payload: bytes, source: dict[str, Any]) -> bool:
    if "sha256" in source:
        return hashlib.sha256(payload).hexdigest() == source["sha256"]
    if "git_blob_sha" in source:
        header = f"blob {len(payload)}\0".encode()
        return hashlib.sha1(header + payload).hexdigest() == source["git_blob_sha"]
    raise ValueError(f"Source {source['source_id']} has no content hash")
