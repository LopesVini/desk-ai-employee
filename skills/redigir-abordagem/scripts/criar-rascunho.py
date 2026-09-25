#!/usr/bin/env python3
"""Create the next versioned Milo body without replacing an earlier draft."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile


SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
def create(mesa: Path, conta: str, source: Path) -> dict:
    if not SLUG.fullmatch(conta):
        raise ValueError("conta_invalida")
    try:
        body = source.read_bytes()
        body.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("texto_invalido") from exc
    if not body.strip():
        raise ValueError("texto_vazio")

    drafts = mesa / "rascunhos"
    drafts.mkdir(parents=True, exist_ok=True)
    lock_descriptor = os.open(drafts / f".{conta}.lock", os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(lock_descriptor, "rb+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        last_file = drafts / f".{conta}.last"
        try:
            recorded = int(last_file.read_text(encoding="ascii").strip()) if last_file.exists() else 0
        except (ValueError, UnicodeError) as exc:
            raise ValueError("registro_versoes_invalido") from exc
        if recorded < 0:
            raise ValueError("registro_versoes_invalido")
        highest = recorded
        for path in drafts.glob(f"{conta}-v*.txt"):
            match = re.fullmatch(re.escape(conta) + r"-v([1-9][0-9]*)\.txt", path.name)
            if match:
                highest = max(highest, int(match.group(1)))

        version = highest + 1
        while True:
            target = drafts / f"{conta}-v{version}.txt"
            try:
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                version += 1
                continue
            with os.fdopen(descriptor, "wb") as output:
                output.write(body)
                output.flush()
                os.fsync(output.fileno())
            break

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="ascii", dir=drafts, prefix=f".{conta}.last.",
            delete=False,
        ) as journal:
            journal.write(f"{version}\n")
            journal.flush()
            os.fsync(journal.fileno())
            journal_path = Path(journal.name)
        os.replace(journal_path, last_file)
        directory_descriptor = os.open(drafts, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        return {"ok": True, "conta": conta, "versao": version, "arquivo": str(target)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesa", type=Path, default=Path("/var/lib/plow/workspace/mesa"))
    parser.add_argument("--conta", required=True)
    parser.add_argument("--texto-arquivo", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = create(args.mesa, args.conta, args.texto_arquivo)
    except (ValueError, OSError) as exc:
        result = {"ok": False, "motivo": str(exc)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
