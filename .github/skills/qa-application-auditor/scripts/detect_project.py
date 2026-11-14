#!/usr/bin/env python3
"""Descoberta somente leitura de um projeto: linguagens, manifestos, comandos candidatos, testes,
CI/CD, configurações, documentação e SINAIS de risco no código (arquivo:linha).

Uso (a partir da raiz do projeto auditado):
    python detect_project.py --root . --json qa-report/evidencias/deteccao.json

- Sinais NÃO são falhas confirmadas: abra cada trecho e avalie o contexto.
- Valores de possíveis segredos nunca são exibidos; arquivos .env não são lidos.
- Limites: --max-files arquivos, fontes até 1 MB, --max-hits ocorrências exibidas por categoria.

Código de saída: 0 ok · 2 uso inválido.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as c  # noqa: E402

LANG_BY_EXT = {
    ".py": "Python", ".pyw": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".cs": "C#", ".vb": "VB.NET",
    ".fs": "F#", ".java": "Java", ".kt": "Kotlin", ".go": "Go", ".rs": "Rust", ".php": "PHP",
    ".rb": "Ruby", ".c": "C", ".h": "C/C++", ".cpp": "C++", ".hpp": "C++", ".swift": "Swift",
    ".dart": "Dart", ".ps1": "PowerShell", ".psm1": "PowerShell", ".sh": "Shell", ".bat": "Batch",
    ".cmd": "Batch", ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".vue": "Vue", ".svelte": "Svelte",
}
SOURCE_EXTS = {".py", ".pyw", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".cs", ".vb", ".java",
               ".kt", ".go", ".php", ".rb", ".ps1", ".psm1", ".vue", ".svelte", ".html"}
MANIFESTS = {
    "package.json": "Node.js (npm/yarn/pnpm)", "requirements.txt": "Python (pip)",
    "requirements-dev.txt": "Python (pip, dev)", "pyproject.toml": "Python (pyproject)",
    "setup.py": "Python (setuptools)", "setup.cfg": "Python (setuptools)", "Pipfile": "Python (pipenv)",
    "poetry.lock": "Python (poetry)", "uv.lock": "Python (uv)", "environment.yml": "Conda",
    "pom.xml": "Java (Maven)", "build.gradle": "Gradle", "build.gradle.kts": "Gradle (Kotlin)",
    "go.mod": "Go modules", "Cargo.toml": "Rust (cargo)", "composer.json": "PHP (composer)",
    "Gemfile": "Ruby (bundler)", "CMakeLists.txt": "CMake", "Makefile": "Make", "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose", "docker-compose.yaml": "Docker Compose",
    "compose.yaml": "Docker Compose", "global.json": ".NET SDK", "Directory.Build.props": ".NET",
    "package-lock.json": "lockfile npm", "yarn.lock": "lockfile yarn", "pnpm-lock.yaml": "lockfile pnpm",
}
MANIFEST_SUFFIXES = {".csproj": ".NET (C#)", ".vbproj": ".NET (VB)", ".fsproj": ".NET (F#)",
                     ".sln": ".NET solution", ".spec": "PyInstaller .spec (ou RPM - verificar)"}
CI_NAMES = {".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile", "bitbucket-pipelines.yml", ".travis.yml"}
TEST_FILE_RE = re.compile(
    r"^(test_.*\.py|.*_test\.py|.*\.(test|spec)\.[cm]?[jt]sx?|.*Tests?\.(cs|java|kt)|.*_test\.go)$")
TEST_CONFIGS = {"pytest.ini", "conftest.py", "tox.ini", "noxfile.py", ".coveragerc", "phpunit.xml",
                "karma.conf.js"}
TEST_CONFIG_RE = re.compile(r"^(jest|vitest|playwright|cypress)\.config\.[cm]?[jt]s$")
CONFIG_EXTS = {".ini", ".cfg", ".conf", ".json", ".yaml", ".yml", ".xml", ".toml", ".properties"}
DOC_RE = re.compile(r"^(README|CONTRIBUTING|CHANGELOG|INSTALL|USAGE)(\..*)?$", re.IGNORECASE)
README_CMD_RE = re.compile(
    r"^\s*(?:\$|>|PS>)?\s*((?:python3?|py|pip3?|pytest|uv|poetry|npm|npx|yarn|pnpm|node|dotnet|mvn|gradle|"
    r"\./gradlew|go|cargo|make|docker|docker-compose|uvicorn|gunicorn|flask|streamlit|pyinstaller)\b.*)$")
SECRET_CATEGORY = "segredo-possivel"


def py_import(modules: str) -> str:
    """`from X ...` ou `import a, X` para qualquer módulo da alternância."""
    return (rf"^\s*(from\s+({modules})\b|import\s+([\w.]+(\s+as\s+\w+)?\s*,\s*)*({modules})\b)")


# (categoria, padrão, exclusão na mesma linha)
SIGNALS = [
    ("entrypoint", r"if\s+__name__\s*==\s*['\"]__main__['\"]|static\s+(async\s+)?\w+\s+Main\s*\(|^func\s+main\s*\(|"
                   r"\bapp\.listen\s*\(|\buvicorn\.run\s*\(|\bwebview\.start\s*\(|\.exec_?\s*\(\s*\)\s*\)?\s*$", None),
    ("framework", py_import(r"PyQt5|PyQt6|PySide2|PySide6|tkinter|customtkinter|wx|webview|kivy|streamlit|flask|"
                            r"fastapi|django|aiohttp|tornado|pyautogui|pywinauto|win32\w*") + "|"
                  r"(require\(|from\s+)['\"](express|electron|koa|fastify|react|vue|svelte|next|@angular/core)['\"]|"
                  r"^\s*using\s+(System\.Windows(\.Forms)?|Microsoft\.AspNetCore)\b", None),
    ("integracao-rede", py_import(r"requests|httpx|aiohttp|urllib3?|urllib\.request|socket|paramiko|ftplib|smtplib|"
                                  r"websockets?|grpc|pika|kafka|zmq|redis") + "|"
                        r"\bnew\s+HttpClient\s*\(|(?<!def )(?<!function )(?<![\w.])fetch\s*\(|"
                        r"\baxios\b|\bnew\s+WebSocket\s*\(", None),
    ("banco-de-dados", py_import(r"sqlite3|sqlalchemy|pyodbc|psycopg2?|pymysql|mysql|cx_Oracle|oracledb|pymongo") + "|"
                       r"\bSqlConnection\b|\bDbContext\b|\bcreateConnection\s*\(|\bmongoose\b", None),
    ("http-sem-timeout", r"\b(requests|httpx)\.(get|post|put|patch|delete|head|request)\s*\(|\burlopen\s*\(", r"timeout"),
    ("concorrencia", r"\bthreading\.Thread\s*\(|(?<![\w.])Thread\s*\(|\bQThread\b|\bThreadPoolExecutor\b|"
                     r"\bProcessPoolExecutor\b|\bmultiprocessing\b|\basyncio\.(create_task|gather|run)\b|"
                     r"\bTask\.Run\s*\(|\bnew\s+Thread\s*\(|\bnew\s+Worker\s*\(|\bgo\s+func\b", None),
    ("timers-jobs", r"\bQTimer\b|\bthreading\.Timer\s*\(|\bsetInterval\s*\(|\bschedule\.every\b|"
                    r"\bBackgroundScheduler\b|\bSystem\.Timers\.Timer\b|\bDispatcherTimer\b|\.after\s*\(\s*\d", None),
    ("loop-polling", r"\bwhile\s*\(?\s*(True|true|1)\s*\)?\s*[:{]?\s*$|\bfor\s*\(\s*;\s*;\s*\)", None),
    ("sleep-bloqueante", r"\btime\.sleep\s*\(|\bThread\.Sleep\s*\(|\bStart-Sleep\b", None),
    ("subprocess-shell", r"\bsubprocess\.(run|Popen|call|check_call|check_output)\s*\(|\bos\.(system|popen)\s*\(|"
                         r"\bchild_process\b|\bProcess\.Start\s*\(|\bshell\s*=\s*True", None),
    ("execucao-dinamica", r"(?<![\w.])(eval|exec)\s*\(|\bpickle\.loads?\s*\(|\byaml\.load\s*\(|\bmarshal\.loads?\s*\(|"
                          r"\bInvoke-Expression\b|\bnew\s+Function\s*\(|\bBinaryFormatter\b", r"SafeLoader"),
    ("io-arquivo-integral", r"\.read\s*\(\s*\)|\.readlines\s*\(\s*\)|\bread_text\s*\(|\bread_bytes\s*\(|"
                            r"\bjson\.load\s*\(|\bFile\.ReadAll(Text|Bytes|Lines)\s*\(|\breadFileSync\s*\(|"
                            r"\bpd\.read_(csv|excel)\s*\(", r"chunksize"),
    ("open-sem-with", r"^\s*[\w.]+\s*=\s*open\s*\(", None),
    ("log-sem-rotacao", r"\blogging\.FileHandler\s*\(|basicConfig\s*\(.*filename\s*=", None),
    ("sql-concatenado", r"\.execute\s*\(\s*(f['\"]|['\"][^'\"]*['\"]\s*(%|\+|\.format))", None),
    ("excecao-silenciada", r"^\s*except\s*:|^\s*except\s+(Exception|BaseException)(\s+as\s+\w+)?\s*:\s*pass\b|"
                           r"catch\s*(\([^)]*\))?\s*\{\s*\}", None),
    ("verificacao-tls-desligada", r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|"
                                  r"ServerCertificateCustomValidationCallback|CERT_NONE", None),
    (SECRET_CATEGORY, r"(?i)\b(password|passwd|pwd|senha|secret|token|api[_-]?key|apikey|client[_-]?secret|"
                      r"connection[_-]?string)\b\s*[:=]\s*['\"][^'\"\s]{4,}['\"]", None),
]
COMPILED = [(cat, re.compile(p), re.compile(x, re.IGNORECASE) if x else None) for cat, p, x in SIGNALS]


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path, limit: int) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None


def walk(root: Path, max_files: int):
    files, skipped, truncated = [], set(), False
    for dirpath, dirnames, filenames in os.walk(root):
        kept = []
        for d in dirnames:
            if d in c.SKIP_DIRS:
                skipped.add(d)
            else:
                kept.append(d)
        dirnames[:] = sorted(kept)
        for name in sorted(filenames):
            files.append(Path(dirpath) / name)
            if len(files) >= max_files:
                return files, skipped, True
    return files, skipped, truncated


def commands_from(path: Path, root: Path, data: dict) -> None:
    name, r = path.name, rel(path, root)
    if name == "package.json":
        text = read_text(path, 1_000_000)
        try:
            scripts = json.loads(text or "{}").get("scripts", {})
        except (ValueError, AttributeError):
            scripts = {}
        for key, value in list(scripts.items())[:30]:
            data["comandos"].append({"fonte": r, "comando": f"npm run {key}", "definicao": str(value)[:200]})
    elif name == "Makefile":
        for target in re.findall(r"^([A-Za-z0-9_.-]+):(?!=)", read_text(path, 500_000) or "", re.MULTILINE)[:20]:
            data["comandos"].append({"fonte": r, "comando": f"make {target}"})
    elif name == "pyproject.toml":
        text = read_text(path, 500_000) or ""
        for section in ("[project.scripts]", "[tool.poetry.scripts]", "[tool.pytest.ini_options]",
                        "[tool.hatch.envs", "[tool.tox"):
            if section in text:
                data["comandos"].append({"fonte": r, "comando": f"seção {section} encontrada (ler o arquivo)"})
    elif DOC_RE.match(name) and path.suffix.lower() in {".md", ".rst", ".txt", ""}:
        in_block = False
        found = 0
        for line in (read_text(path, 1_000_000) or "").splitlines():
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            m = README_CMD_RE.match(line) if in_block else None
            if m and found < 30:
                data["comandos"].append({"fonte": r, "comando": m.group(1).strip()[:200]})
                found += 1


def scan_signals(path: Path, root: Path, data: dict, max_hits: int) -> None:
    if path.name.endswith(".min.js"):
        return
    text = read_text(path, 1_000_000)
    if text is None:
        return
    r = rel(path, root)
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > 2000:
            continue
        for cat, pattern, exclude in COMPILED:
            if pattern.search(line) and not (exclude and exclude.search(line)):
                data["contagem_sinais"][cat] += 1
                if len(data["sinais"][cat]) < max_hits:
                    snippet = "[valor omitido]" if cat == SECRET_CATEGORY else line.strip()[:140]
                    data["sinais"][cat].append(f"{r}:{lineno} - {snippet}")


def main() -> int:
    c.setup_stdout()
    parser = argparse.ArgumentParser(description="Descoberta somente leitura de um projeto.")
    parser.add_argument("--root", default=".", help="raiz do projeto")
    parser.add_argument("--max-files", type=int, default=20000, help="limite de arquivos percorridos")
    parser.add_argument("--max-hits", type=int, default=40, help="ocorrências exibidas por categoria de sinal")
    parser.add_argument("--json", help="grava o resultado também em JSON")
    args = parser.parse_args()
    if not 1 <= args.max_files <= 500_000 or not 1 <= args.max_hits <= 1000:
        parser.error("--max-files deve estar entre 1 e 500.000 e --max-hits entre 1 e 1000")
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error(f"pasta inexistente: {root}")

    files, skipped, truncated = walk(root, args.max_files)
    data = {
        "raiz": str(root), "arquivos": len(files), "truncado": truncated, "pastas_ignoradas": sorted(skipped),
        "linguagens": Counter(), "manifestos": [], "comandos": [], "testes": [], "configs_teste": [],
        "ci": [], "configuracao": [], "env": [], "documentacao": [],
        "sinais": defaultdict(list), "contagem_sinais": Counter(),
    }
    for path in files:
        name, suffix, r = path.name, path.suffix.lower(), rel(path, root)
        if suffix in LANG_BY_EXT:
            data["linguagens"][LANG_BY_EXT[suffix]] += 1
        if name in MANIFESTS:
            data["manifestos"].append(f"{r} - {MANIFESTS[name]}")
        elif suffix in MANIFEST_SUFFIXES:
            data["manifestos"].append(f"{r} - {MANIFEST_SUFFIXES[suffix]}")
        if name in CI_NAMES or "/.github/workflows/" in f"/{r}":
            data["ci"].append(r)
        if TEST_FILE_RE.match(name):
            data["testes"].append(r)
        if name in TEST_CONFIGS or TEST_CONFIG_RE.match(name):
            data["configs_teste"].append(r)
        if name.startswith(".env"):
            data["env"].append(r)
        elif suffix in CONFIG_EXTS and name not in MANIFESTS:
            data["configuracao"].append(r)
        if DOC_RE.match(name):
            data["documentacao"].append(r)
        if name in {"package.json", "Makefile", "pyproject.toml"} or (DOC_RE.match(name) and path.parent == root):
            commands_from(path, root, data)
        if suffix in SOURCE_EXTS:
            scan_signals(path, root, data, args.max_hits)

    def section(title: str, items, limit: int = 60) -> None:
        print(f"\n## {title}")
        if not items:
            print("- (nenhum)")
            return
        for item in list(items)[:limit]:
            print(f"- {item}")
        if len(items) > limit:
            print(f"- ... e mais {len(items) - limit}")

    print(f"# Detecção do projeto - {root}")
    print(f"Arquivos percorridos: {len(files)}" + (" (TRUNCADO - aumente --max-files)" if truncated else ""))
    section("Linguagens (nº de arquivos)", [f"{k}: {v}" for k, v in data["linguagens"].most_common()])
    section("Manifestos / dependências / build", data["manifestos"])
    section("Comandos candidatos (CONFIRME na fonte antes de executar)",
            [f"`{x['comando']}` - {x['fonte']}" + (f" -> {x['definicao']}" if x.get("definicao") else "")
             for x in data["comandos"]])
    section("Arquivos de teste", data["testes"], 40)
    section("Configuração de testes", data["configs_teste"])
    section("CI/CD", data["ci"])
    section("Arquivos .env (conteúdo NÃO lido)", data["env"])
    section("Configuração (.ini/.json/.yaml/.xml/.toml...)", data["configuracao"], 40)
    section("Documentação", data["documentacao"])
    section("Pastas ignoradas encontradas", data["pastas_ignoradas"])

    print("\n## Sinais no código (NÃO são falhas confirmadas - revise cada trecho)")
    if not data["contagem_sinais"]:
        print("- (nenhum)")
    for cat, _, _ in SIGNALS:
        total = data["contagem_sinais"].get(cat, 0)
        if not total:
            continue
        shown = data["sinais"][cat]
        print(f"\n### {cat} ({total}{'; exibindo ' + str(len(shown)) if total > len(shown) else ''})")
        for hit in shown:
            print(f"- {hit}")

    if args.json:
        out = Path(args.json).resolve()
        c.write_json(out, {**data, "linguagens": dict(data["linguagens"]), "sinais": dict(data["sinais"]),
                           "contagem_sinais": dict(data["contagem_sinais"])})
        print(f"\nJSON: {out}")
    return c.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
