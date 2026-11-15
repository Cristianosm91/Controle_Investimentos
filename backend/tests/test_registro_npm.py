import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def test_frontend_usa_registro_npm_publico():
    linhas = (FRONTEND / ".npmrc").read_text(encoding="utf-8").splitlines()
    registros = [
        linha.strip()
        for linha in linhas
        if not linha.lstrip().startswith(("#", ";")) and "=" in linha
        and linha.split("=", 1)[0].strip().endswith("registry")
    ]
    assert registros == ["registry=https://registry.npmjs.org/"]

    lock = json.loads((FRONTEND / "package-lock.json").read_text(encoding="utf-8"))
    resolvidos = [
        (nome, pacote["resolved"])
        for nome, pacote in lock["packages"].items()
        if "resolved" in pacote
    ]
    assert resolvidos
    for nome, endereco in resolvidos:
        url = urlsplit(endereco)
        assert url.scheme == "https" and url.netloc == "registry.npmjs.org", nome


@pytest.mark.parametrize(
    ("registro", "endereco"),
    [
        ("registry=https://registry.npmjs.org/", "https://example.invalid/pkg.tgz"),
        ("registry=https://example.invalid/", "https://registry.npmjs.org/pkg.tgz"),
        (
            "registry=https://registry.npmjs.org/\n@teste:registry=https://example.invalid/",
            "https://registry.npmjs.org/pkg.tgz",
        ),
    ],
)
def test_rejeita_registro_nao_publico(tmp_path, monkeypatch, registro, endereco):
    (tmp_path / ".npmrc").write_text(registro, encoding="utf-8")
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"packages": {"node_modules/pkg": {"resolved": endereco}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(__name__ + ".FRONTEND", tmp_path)
    with pytest.raises(AssertionError):
        test_frontend_usa_registro_npm_publico()
