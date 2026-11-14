#!/usr/bin/env python3
"""Executa UM comando de build/teste do projeto com timeout, log limitado e evidência em JSON.

Uso (a partir da raiz do projeto auditado):
    python run_tests.py --name pytest --timeout 900 -- python -m pytest -q

- Recusa comandos destrutivos (ver _common._BLOCKED_PATTERNS).
- stdin fechado e CI=1 para evitar prompts/modo watch; encerra a árvore de processos no timeout.
- Grava <out>/<data>_<nome>.log e .json.

Códigos de saída: 0 aprovado · 1 reprovado · 2 bloqueado/uso inválido · 3 não executado · 124 timeout.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

MAX_TIMEOUT_S = 4 * 3600


def main() -> int:
    c.setup_stdout()
    parser = argparse.ArgumentParser(description="Executa um comando de teste/build com timeout e evidência.")
    parser.add_argument("--name", required=True, help="identificador curto (ex.: pytest, build, e2e)")
    parser.add_argument("--timeout", type=int, default=600, help=f"segundos (1..{MAX_TIMEOUT_S}, padrão 600)")
    parser.add_argument("--cwd", default=".", help="diretório de execução (padrão: atual)")
    parser.add_argument("--out", default="qa-report/evidencias", help="pasta das evidências")
    parser.add_argument("--max-log-mb", type=int, default=20, help="limite do log em MB (padrão 20)")
    parser.add_argument("--tail", type=int, default=40, help="linhas finais do log exibidas")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="comando após --")
    args = parser.parse_args()

    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not cmd:
        parser.error("informe o comando após --")
    if not 1 <= args.timeout <= MAX_TIMEOUT_S:
        parser.error(f"--timeout deve estar entre 1 e {MAX_TIMEOUT_S}")
    if not 1 <= args.max_log_mb <= 500:
        parser.error("--max-log-mb deve estar entre 1 e 500")

    cwd = Path(args.cwd).resolve()
    out = Path(args.out).resolve()
    base = f"{c.stamp()}_{c.safe_name(args.name)}"
    log_path = out / f"{base}.log"
    record = {
        "nome": args.name,
        "comando": cmd,
        "cwd": str(cwd),
        "timeout_s": args.timeout,
        "inicio": c.now_iso(),
    }

    def finish(status: str, code: int, **extra) -> int:
        record.update(status=status, fim=c.now_iso(), **extra)
        c.write_json(out / f"{base}.json", record)
        print(f"STATUS: {status}")
        for key in ("motivo", "codigo_retorno", "duracao_s"):
            if key in record:
                print(f"{key}: {record[key]}")
        print(f"evidência: {out / (base + '.json')}")
        return code

    reason = c.check_command(cmd)
    if reason:
        return finish("BLOQUEADO", c.EXIT_BLOCKED,
                      motivo=f"comando recusado ({reason}); se for legítimo, peça ao usuário para executá-lo manualmente")
    if not cwd.is_dir():
        return finish("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED, motivo=f"diretório inexistente: {cwd}")
    argv = c.resolve_argv(cmd)
    if argv is None:
        return finish("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED,
                      motivo=f"executável não encontrado no PATH: {cmd[0]}", dependencia_necessaria=cmd[0])

    env = dict(os.environ, CI="1", PYTHONUNBUFFERED="1")
    print(f"Executando ({args.timeout}s máx.): {' '.join(cmd)}", flush=True)
    t0 = time.monotonic()
    try:
        proc, pump, stats = c.start_logged_process(argv, str(cwd), log_path, args.max_log_mb * 1024 * 1024, env)
    except OSError as exc:
        return finish("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED, motivo=f"falha ao iniciar: {exc}")

    timed_out = False
    try:
        rc = proc.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        c.kill_tree(proc)
        rc = proc.returncode
    except KeyboardInterrupt:
        c.kill_tree(proc)
        pump.join(timeout=10)
        return finish("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED, motivo="interrompido pelo usuário",
                      duracao_s=round(time.monotonic() - t0, 2), log=str(log_path))
    pump.join(timeout=10)
    duration = round(time.monotonic() - t0, 2)

    tail = c.tail_text(log_path, args.tail)
    if tail:
        print(f"--- últimas {args.tail} linhas do log ---\n{tail}\n--- fim ---")

    extra = {"codigo_retorno": rc, "duracao_s": duration, "log": str(log_path), **stats}
    if timed_out:
        return finish("REPROVADO", c.EXIT_TIMEOUT,
                      motivo=f"timeout de {args.timeout}s; árvore de processos encerrada", **extra)
    if rc == 0:
        return finish("APROVADO", c.EXIT_OK, **extra)
    return finish("REPROVADO", c.EXIT_FAIL, motivo=f"código de retorno {rc}", **extra)


if __name__ == "__main__":
    sys.exit(main())
