from datetime import datetime
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Response

from ..schemas import ExportacaoIn
from ..services import exportacao

router = APIRouter(tags=["exportação"])

_TIPOS = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.post("/exportacao/{formato}")
def exportar(formato: Literal["csv", "xlsx"], dados: ExportacaoIn):
    conteudo = exportacao.gerar_csv(dados.abas) if formato == "csv" else exportacao.gerar_xlsx(dados.abas)
    nome = f"{dados.nome.strip()}-{datetime.now():%Y%m%d-%H%M}.{formato}"
    return Response(
        conteudo,
        media_type=_TIPOS[formato],
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"},
    )
