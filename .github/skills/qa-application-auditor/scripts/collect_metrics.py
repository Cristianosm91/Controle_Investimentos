#!/usr/bin/env python3
"""Amostra CPU, memória (RSS), threads, handles e processos filhos de um PID ou de um comando.

Uso (a partir da raiz do projeto auditado):
    python collect_metrics.py --name app-ocioso --duration 300 -- python app.py
    python collect_metrics.py --name app-em-uso --pid 1234 --duration 600

- Requer psutil (não instala). Sem psutil → NÃO EXECUTADO (código 3).
- Modo comando: recusa comandos destrutivos e encerra a árvore de processos ao fim da janela.
- Modo --pid: apenas observa; nunca encerra o processo.
- Grava <out>/<data>_<nome>_metricas.csv e .json. Alertas são HIPÓTESES, não falhas confirmadas.

Códigos de saída: 0 coletado · 2 bloqueado/uso inválido · 3 não executado.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

try:
    import psutil
except ImportError:
    psutil = None

MAX_DURATION_S = 8 * 3600
FIELDS = ["t_s", "processos", "cpu_proc_pct", "rss_mb", "threads", "handles",
          "cpu_sistema_pct", "mem_sistema_pct", "disco_livre_gb"]


def trend_per_min(ts: list[float], ys: list[float]):
    """Inclinação por minuto (mínimos quadrados) e R²."""
    n = len(ts)
    if n < 3:
        return None, None
    mt, my = sum(ts) / n, sum(ys) / n
    sxx = sum((t - mt) ** 2 for t in ts)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0:
        return None, None
    sxy = sum((t - mt) * (y - my) for t, y in zip(ts, ys))
    r2 = (sxy * sxy) / (sxx * syy) if syy else 0.0
    return round(sxy / sxx * 60, 3), round(r2, 3)


def main() -> int:
    c.setup_stdout()
    parser = argparse.ArgumentParser(description="Coleta métricas de recurso de um processo e seus filhos.")
    parser.add_argument("--name", required=True, help="identificador do cenário (ex.: app-ocioso)")
    parser.add_argument("--pid", type=int, help="PID existente a observar (não é encerrado)")
    parser.add_argument("--duration", type=float, default=60, help=f"segundos (1..{MAX_DURATION_S}, padrão 60)")
    parser.add_argument("--interval", type=float, default=1.0, help="segundos entre amostras (mín. 0.2)")
    parser.add_argument("--cwd", default=".", help="diretório de execução do comando")
    parser.add_argument("--out", default="qa-report/evidencias", help="pasta das evidências")
    parser.add_argument("--max-log-mb", type=int, default=20, help="limite do log do comando em MB")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="comando após -- (alternativa a --pid)")
    args = parser.parse_args()

    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if bool(cmd) == (args.pid is not None):
        parser.error("informe --pid OU um comando após --")
    if not 1 <= args.duration <= MAX_DURATION_S:
        parser.error(f"--duration deve estar entre 1 e {MAX_DURATION_S}")
    if args.interval < 0.2 or args.interval > args.duration:
        parser.error("--interval deve ser >= 0.2 e <= --duration")

    out = Path(args.out).resolve()
    base = f"{c.stamp()}_{c.safe_name(args.name)}_metricas"
    record = {"nome": args.name, "inicio": c.now_iso(), "duracao_solicitada_s": args.duration,
              "intervalo_s": args.interval, "alvo": {"pid": args.pid} if args.pid else {"comando": cmd}}

    def stop(status: str, code: int, motivo: str) -> int:
        record.update(status=status, motivo=motivo, fim=c.now_iso())
        c.write_json(out / f"{base}.json", record)
        print(f"STATUS: {status}\nmotivo: {motivo}\nevidência: {out / (base + '.json')}")
        return code

    if psutil is None:
        return stop("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED,
                    "dependência psutil ausente (instalar somente com autorização: python -m pip install psutil)")

    proc = None
    if cmd:
        reason = c.check_command(cmd)
        if reason:
            return stop("BLOQUEADO", c.EXIT_BLOCKED, f"comando recusado ({reason})")
        argv = c.resolve_argv(cmd)
        if argv is None:
            return stop("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED, f"executável não encontrado no PATH: {cmd[0]}")
        log_path = out / f"{base}_saida.log"
        try:
            proc, pump, log_stats = c.start_logged_process(
                argv, str(Path(args.cwd).resolve()), log_path, args.max_log_mb * 1024 * 1024)
        except OSError as exc:
            return stop("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED, f"falha ao iniciar: {exc}")
        record["log_do_processo"] = str(log_path)
        pid = proc.pid
    else:
        pid = args.pid

    try:
        root = psutil.Process(pid)
    except psutil.Error as exc:
        if proc:
            c.kill_tree(proc)
        return stop("NÃO EXECUTADO", c.EXIT_NOT_EXECUTED, f"processo {pid} inacessível: {exc}")

    cache: dict[int, "psutil.Process"] = {}
    disk_path = str(Path(args.cwd).resolve())

    def members():
        try:
            found = [root, *root.children(recursive=True)]
        except psutil.Error:
            return []
        alive = []
        for p in found:
            if p.pid not in cache:
                cache[p.pid] = p
                try:
                    p.cpu_percent(None)
                except psutil.Error:
                    continue
            alive.append(cache[p.pid])
        return alive

    def root_alive() -> bool:
        if proc is not None and proc.poll() is not None:
            return False
        try:
            return root.is_running() and root.status() != psutil.STATUS_ZOMBIE
        except psutil.Error:
            return False

    psutil.cpu_percent(None)
    members()
    rows = []
    csv_path = out / f"{base}.csv"
    out.mkdir(parents=True, exist_ok=True)
    print(f"Coletando PID {pid} por até {args.duration}s (intervalo {args.interval}s)...", flush=True)
    t0 = time.monotonic()
    ended_early = False
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            while time.monotonic() - t0 < args.duration:
                time.sleep(args.interval)
                if not root_alive():
                    ended_early = True
                    break
                cpu = rss = threads = handles = count = 0
                for p in members():
                    try:
                        with p.oneshot():
                            cpu += p.cpu_percent(None)
                            rss += p.memory_info().rss
                            threads += p.num_threads()
                            handles += p.num_handles() if os.name == "nt" else p.num_fds()
                        count += 1
                    except psutil.Error:
                        continue
                row = {
                    "t_s": round(time.monotonic() - t0, 2),
                    "processos": count,
                    "cpu_proc_pct": round(cpu, 1),
                    "rss_mb": round(rss / 1048576, 2),
                    "threads": threads,
                    "handles": handles,
                    "cpu_sistema_pct": psutil.cpu_percent(None),
                    "mem_sistema_pct": psutil.virtual_memory().percent,
                    "disco_livre_gb": round(psutil.disk_usage(disk_path).free / 1073741824, 2),
                }
                writer.writerow(row)
                fh.flush()
                rows.append(row)
    except KeyboardInterrupt:
        record["interrompido_pelo_usuario"] = True
    finally:
        if proc is not None:
            exit_code = proc.poll()
            if exit_code is None:
                c.kill_tree(proc)
                record["encerramento"] = "forçado pelo coletor ao fim da janela (não valida shutdown gracioso)"
            else:
                record["codigo_saida_processo"] = exit_code
            pump.join(timeout=10)
            record.update(log_stats)

    record.update(amostras=len(rows), duracao_observada_s=rows[-1]["t_s"] if rows else 0,
                  encerrou_antes_do_fim=ended_early, csv=str(csv_path))
    alerts = []
    if rows:
        ts = [r["t_s"] for r in rows]
        cores = psutil.cpu_count() or 1
        summary = {}
        for key in ("cpu_proc_pct", "rss_mb", "threads", "handles", "processos"):
            vals = [r[key] for r in rows]
            summary[key] = {"inicio": vals[0], "fim": vals[-1], "min": min(vals), "max": max(vals),
                            "media": round(sum(vals) / len(vals), 2)}
        for key in ("rss_mb", "threads", "handles"):
            summary[key]["tendencia_por_min"], summary[key]["r2"] = trend_per_min(ts, [r[key] for r in rows])
        summary["mem_sistema_pct_max"] = max(r["mem_sistema_pct"] for r in rows)
        summary["disco_livre_gb_min"] = min(r["disco_livre_gb"] for r in rows)
        summary["nucleos_logicos"] = cores
        record["resumo"] = summary

        long_enough = ts[-1] >= 60
        rss = summary["rss_mb"]
        if long_enough and (rss["tendencia_por_min"] or 0) > 1 and (rss["r2"] or 0) >= 0.8:
            alerts.append(f"HIPÓTESE: memória crescendo ~{rss['tendencia_por_min']} MB/min de forma consistente "
                          f"(R²={rss['r2']}). Confirmar com soak mais longo e carga constante.")
        for key, limit in (("threads", 0.5), ("handles", 5)):
            s = summary[key]
            if long_enough and (s["tendencia_por_min"] or 0) > limit and (s["r2"] or 0) >= 0.8:
                alerts.append(f"HIPÓTESE: {key} crescendo ~{s['tendencia_por_min']}/min (R²={s['r2']}) - "
                              f"possível vazamento de {key}.")
        busy = sum(1 for r in rows if r["cpu_proc_pct"] >= 90) / len(rows)
        if busy >= 0.8:
            alerts.append(f"HIPÓTESE: CPU >= 90% de um núcleo em {busy:.0%} das amostras - se o app estava ocioso, "
                          "suspeitar de busy-wait/polling agressivo.")
        if summary["mem_sistema_pct_max"] >= 90:
            alerts.append(f"ATENÇÃO: memória do sistema chegou a {summary['mem_sistema_pct_max']}% durante a coleta.")
        if summary["disco_livre_gb_min"] < 1:
            alerts.append(f"ATENÇÃO: espaço livre em disco abaixo de 1 GB ({summary['disco_livre_gb_min']} GB).")
        if not long_enough:
            alerts.append("LIMITAÇÃO: janela < 60s; tendências não avaliadas.")
    if ended_early:
        alerts.append(f"ATENÇÃO: processo encerrou antes do fim da janela (código: {record.get('codigo_saida_processo')}). "
                      "Verificar se era esperado ou se houve crash.")
    record["alertas"] = alerts

    c.write_json(out / f"{base}.json", record)
    print(f"STATUS: COLETADO ({len(rows)} amostras)")
    if rows:
        s = record["resumo"]
        print(f"CPU proc média/pico: {s['cpu_proc_pct']['media']}% / {s['cpu_proc_pct']['max']}% "
              f"({s['nucleos_logicos']} núcleos lógicos)")
        print(f"RSS início/fim/pico: {s['rss_mb']['inicio']} / {s['rss_mb']['fim']} / {s['rss_mb']['max']} MB "
              f"(tendência {s['rss_mb']['tendencia_por_min']} MB/min, R²={s['rss_mb']['r2']})")
        print(f"Threads início/fim: {s['threads']['inicio']} / {s['threads']['fim']} · "
              f"Handles início/fim: {s['handles']['inicio']} / {s['handles']['fim']}")
    for alert in alerts:
        print(f"- {alert}")
    print(f"evidência: {out / (base + '.json')}")
    return c.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
