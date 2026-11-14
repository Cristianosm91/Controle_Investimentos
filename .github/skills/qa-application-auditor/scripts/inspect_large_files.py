#!/usr/bin/env python3
"""Inventário somente leitura de uso de disco: maiores arquivos, diretórios com muitas entradas,
logs grandes, temporários e espaço livre no volume.

Uso:
    python inspect_large_files.py --root . --top 20
    python inspect_large_files.py --root $env:TEMP --include-all --json qa-report/evidencias/temp.json

Não segue links simbólicos e para ao atingir --max-entries. Código de saída: 0 ok · 2 uso inválido.
"""
from __future__ import annotations

import argparse
import heapq
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

LOG_RE = re.compile(r"\.(log|out|trace)(\.\d+)?$", re.IGNORECASE)
TEMP_RE = re.compile(r"(\.(tmp|temp|bak|old|swp|part|crdownload)$)|(^~\$)", re.IGNORECASE)
MB = 1048576


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def scan(root: Path, skip: set[str], args) -> dict:
    top: list[tuple[int, str]] = []
    crowded, logs, errors, skipped = [], [], [], set()
    temps = {"quantidade": 0, "bytes": 0, "exemplos": []}
    total_bytes = files = entries = 0
    truncated = False
    stack = [root]
    while stack and not truncated:
        current = stack.pop()
        try:
            iterator = os.scandir(current)
        except OSError as exc:
            errors.append(f"{current}: {exc.strerror or exc}")
            continue
        count = 0
        with iterator:
            for entry in iterator:
                count += 1
                entries += 1
                if entries > args.max_entries:
                    truncated = True
                    break
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in skip:
                            skipped.add(entry.name)
                        else:
                            stack.append(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError as exc:
                    errors.append(f"{entry.path}: {exc.strerror or exc}")
                    continue
                files += 1
                total_bytes += size
                rel = os.path.relpath(entry.path, root)
                if len(top) < args.top:
                    heapq.heappush(top, (size, rel))
                elif size > top[0][0]:
                    heapq.heapreplace(top, (size, rel))
                if LOG_RE.search(entry.name) and size >= args.log_mb * MB:
                    logs.append((size, rel))
                if TEMP_RE.search(entry.name):
                    temps["quantidade"] += 1
                    temps["bytes"] += size
                    if len(temps["exemplos"]) < 10:
                        temps["exemplos"].append(rel)
        if count >= args.dir_entries:
            crowded.append((count, os.path.relpath(current, root)))
    return {
        "maiores_arquivos": [{"bytes": s, "caminho": p} for s, p in sorted(top, reverse=True)],
        "diretorios_lotados": [{"entradas": n, "caminho": p} for n, p in sorted(crowded, reverse=True)[:args.top]],
        "logs_grandes": [{"bytes": s, "caminho": p} for s, p in sorted(logs, reverse=True)[:args.top]],
        "temporarios": temps,
        "total_bytes": total_bytes,
        "arquivos": files,
        "entradas_lidas": entries,
        "truncado": truncated,
        "ignorados": sorted(skipped),
        "erros": errors[:50],
        "qtd_erros": len(errors),
    }


def main() -> int:
    c.setup_stdout()
    parser = argparse.ArgumentParser(description="Inventário somente leitura de uso de disco.")
    parser.add_argument("--root", default=".", help="pasta a inspecionar")
    parser.add_argument("--top", type=int, default=20, help="quantidade de itens por lista")
    parser.add_argument("--min-size-mb", type=float, default=0, help="destacar arquivos acima deste tamanho")
    parser.add_argument("--log-mb", type=float, default=10, help="tamanho mínimo para listar logs (MB)")
    parser.add_argument("--dir-entries", type=int, default=1000, help="entradas para considerar diretório lotado")
    parser.add_argument("--max-entries", type=int, default=300000, help="limite de entradas lidas")
    parser.add_argument("--include-all", action="store_true", help="não ignora node_modules, venv, dist etc. (só .git)")
    parser.add_argument("--json", help="grava o resultado também em JSON")
    args = parser.parse_args()
    if not 1 <= args.top <= 500 or not 1 <= args.max_entries <= 5_000_000:
        parser.error("--top deve estar entre 1 e 500 e --max-entries entre 1 e 5.000.000")

    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error(f"pasta inexistente: {root}")
    skip = {".git"} if args.include_all else c.SKIP_DIRS
    result = scan(root, skip, args)
    usage = shutil.disk_usage(root)
    result["volume"] = {"total_bytes": usage.total, "livre_bytes": usage.free,
                        "livre_pct": round(usage.free / usage.total * 100, 1) if usage.total else None}
    result["raiz"] = str(root)

    print(f"# Inventário de disco - {root}\n")
    print(f"Arquivos: {result['arquivos']} · Total: {human(result['total_bytes'])} · "
          f"Entradas lidas: {result['entradas_lidas']}" + (" · TRUNCADO (aumente --max-entries)" if result["truncado"] else ""))
    vol = result["volume"]
    print(f"Volume: {human(vol['livre_bytes'])} livres de {human(vol['total_bytes'])} ({vol['livre_pct']}%)")
    if vol["livre_pct"] is not None and vol["livre_pct"] < 10:
        print("ATENÇÃO: menos de 10% livre no volume - testes que gravam em disco podem afetar a máquina.")
    if result["ignorados"]:
        print(f"Pastas ignoradas: {', '.join(result['ignorados'])}")

    print(f"\n## Maiores arquivos (top {args.top})")
    for item in result["maiores_arquivos"]:
        flag = "  <-- acima do limite" if args.min_size_mb and item["bytes"] >= args.min_size_mb * MB else ""
        print(f"- {human(item['bytes']):>10}  {item['caminho']}{flag}")
    print(f"\n## Diretórios com >= {args.dir_entries} entradas")
    for item in result["diretorios_lotados"]:
        print(f"- {item['entradas']}  {item['caminho']}")
    if not result["diretorios_lotados"]:
        print("- nenhum")
    print(f"\n## Logs >= {args.log_mb} MB")
    for item in result["logs_grandes"]:
        print(f"- {human(item['bytes']):>10}  {item['caminho']}")
    if not result["logs_grandes"]:
        print("- nenhum")
    t = result["temporarios"]
    print(f"\n## Temporários/backups: {t['quantidade']} arquivo(s), {human(t['bytes'])}")
    for ex in t["exemplos"]:
        print(f"- {ex}")
    if result["qtd_erros"]:
        print(f"\n## Sem acesso ({result['qtd_erros']}; primeiros {len(result['erros'])})")
        for err in result["erros"][:10]:
            print(f"- {err}")

    if args.json:
        c.write_json(Path(args.json).resolve(), result)
        print(f"\nJSON: {Path(args.json).resolve()}")
    return c.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
