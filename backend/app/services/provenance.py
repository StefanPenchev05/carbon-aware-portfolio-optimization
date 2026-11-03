"""Verified file manifests for real-data imports; no network access during replay."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_name: str = Field(min_length=1, max_length=200)
    reference: str = Field(min_length=1, max_length=1000)
    retrieved_at: AwareDatetime
    license_reference: str = Field(min_length=1, max_length=1000)
    usage_permission: str = Field(min_length=1)
    synthetic: bool
    notes: str = ""
    files: dict[str, str]
    raw_files: dict[str, str] = Field(default_factory=dict)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_manifest(path, csv_path):
    path, csv_path = Path(path), Path(csv_path)
    manifest = Manifest.model_validate_json(path.read_text())
    relative = csv_path.resolve().relative_to(path.parent.resolve()).as_posix()
    if manifest.files.get(relative) != sha256(csv_path):
        raise ValueError("CSV not listed in manifest or SHA-256 mismatch")
    for filename, digest in manifest.raw_files.items():
        raw = (path.parent / filename).resolve()
        if not raw.is_relative_to(path.parent.resolve()) or sha256(raw) != digest:
            raise ValueError("Raw snapshot missing, outside bundle or SHA-256 mismatch")
    return manifest, sha256(path)


def valid_isin(isin):
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        return False
    expanded = "".join(str(ord(c) - 55) if c.isalpha() else c for c in isin.upper())
    return (
        sum(
            (int(n) * (2 if i % 2 else 1)) // 10 + (int(n) * (2 if i % 2 else 1)) % 10
            for i, n in enumerate(reversed(expanded))
        )
        % 10
        == 0
    )


def main():
    parser = argparse.ArgumentParser(description="Build a hashed manifest for a lawfully acquired manual CSV bundle")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--license-reference", required=True)
    parser.add_argument("--permission", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--raw-files", nargs="*", default=[])
    args = parser.parse_args()
    root = args.directory.resolve()

    def hashes(names):
        result = {}
        for name in names:
            target = (root / name).resolve()
            if not target.is_relative_to(root):
                raise ValueError("All bundle files must be inside its directory")
            result[target.relative_to(root).as_posix()] = sha256(target)
        return result

    manifest = Manifest(
        source_name=args.source,
        reference=args.reference,
        retrieved_at=args.retrieved_at,
        license_reference=args.license_reference,
        usage_permission=args.permission,
        synthetic=args.synthetic,
        notes=args.notes,
        files=hashes(args.files),
        raw_files=hashes(args.raw_files),
    )
    with (root / "manifest.json").open("x") as stream:
        stream.write(json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n")
    print(root / "manifest.json")


if __name__ == "__main__":
    main()
