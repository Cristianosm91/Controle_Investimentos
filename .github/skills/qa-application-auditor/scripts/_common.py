"""Utilitários compartilhados pelos scripts do qa-application-auditor (somente biblioteca padrão)."""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_BLOCKED = 2
EXIT_NOT_EXECUTED = 3
EXIT_TIMEOUT = 124

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", ".env", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox", "dist", "build", ".idea",
    ".vs", "bin", "obj", "target", ".next", ".nuxt", "coverage", "htmlcov", "qa-report",
    "site-packages", ".gradle",
}

# Rede de segurança: não substitui a análise do comando antes de executá-lo.
_BLOCKED_PATTERNS = [
    (r"\brm\s+-\w*[rf]", "remoção recursiva/forçada de arquivos"),
    (r"\b(rmdir|rd)\b", "remoção de diretório"),
    (r"\b(del|erase)\b", "remoção de arquivos"),
    (r"\bremove-item\b", "remoção de arquivos"),
    (r"\bformat(\.com)?\s+[a-z]:", "formatação de disco"),
    (r"\b(diskpart|mkfs\S*)\b", "particionamento/formatação de disco"),
    (r"\bdd\s+if=", "escrita direta em dispositivo"),
    (r"\b(shutdown|reboot|restart-computer|stop-computer)\b", "desligamento/reinício da máquina"),
    (r"\breg(\.exe)?\s+(delete|add|import)\b", "alteração do registro do Windows"),
    (r"\b(sudo|runas)\b|-verb\s+runas", "elevação de privilégio"),
    (r"\bgit\s+(push|clean|rebase)\b|\bgit\s+reset\s+--hard\b|\bgit\s+checkout\s+--\s", "operação Git destrutiva ou remota"),
    (r"\b(drop|truncate)\s+(table|database|schema)\b", "DDL destrutivo"),
    (r"\b(npm|yarn|pnpm)\s+(publish|update|upgrade)\b|\bnpm\s+audit\s+fix\b", "publicação/atualização de dependências"),
    (r"\bpip3?\s+install\b.*(\s-u\b|--upgrade)", "atualização de dependências"),
    (r"\btwine\s+upload\b|\bdotnet\s+nuget\s+push\b", "publicação de pacote"),
    (r"\bdocker\s+(system\s+prune|volume\s+rm|rm|rmi)\b|\bkubectl\s+delete\b|\bterraform\s+(apply|destroy)\b", "alteração de infraestrutura"),
    (r"\b(curl|wget|iwr|invoke-webrequest)\b.*\|\s*(sh|bash|iex|invoke-expression)\b", "execução de script remoto"),
]


def setup_stdout() -> None:
    encoding = "utf-8"
    # Quando a saída é redirecionada, o PowerShell decodifica com a code page do console.
    if os.name == "nt" and not sys.stdout.isatty():
        try:
            import ctypes
            cp = ctypes.windll.kernel32.GetConsoleOutputCP()
            if cp:
                encoding = f"cp{cp}"
        except (AttributeError, OSError):
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding=encoding, errors="replace")
        except (AttributeError, LookupError):
            pass


def check_command(argv: list[str]) -> str | None:
    """Retorna o motivo do bloqueio, ou None se o comando não casar com padrões destrutivos."""
    text = " ".join(argv).lower()
    for pattern, reason in _BLOCKED_PATTERNS:
        if re.search(pattern, text):
            return reason
    return None


def resolve_argv(argv: list[str]) -> list[str] | None:
    exe = shutil.which(argv[0])
    return [exe, *argv[1:]] if exe else None


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_name(name: str) -> str:
    return re.sub(r"[^\w.-]", "_", name)[:60] or "execucao"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def start_logged_process(argv, cwd, log_path: Path, max_log_bytes: int, env=None):
    """Inicia o processo em novo grupo, gravando stdout+stderr no log até max_log_bytes."""
    if os.name == "nt":
        group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        group = {"start_new_session": True}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **group,
    )
    stats = {"bytes_gravados": 0, "bytes_descartados": 0}

    def pump() -> None:
        with open(log_path, "wb") as fh:
            for chunk in iter(lambda: proc.stdout.read1(65536), b""):
                room = max(0, max_log_bytes - stats["bytes_gravados"])
                kept = chunk[:room]
                if kept:
                    fh.write(kept)
                    stats["bytes_gravados"] += len(kept)
                stats["bytes_descartados"] += len(chunk) - len(kept)
            if stats["bytes_descartados"]:
                fh.write(f"\n[log truncado: {stats['bytes_descartados']} bytes descartados]\n".encode())

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    return proc, thread, stats


def kill_tree(proc: subprocess.Popen) -> None:
    """Encerra o processo e todos os descendentes."""
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=False,
            )
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        try:
            proc.kill()
        except OSError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def tail_text(path: Path, lines: int = 40) -> str:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 65536))
            data = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(data.splitlines()[-lines:])
