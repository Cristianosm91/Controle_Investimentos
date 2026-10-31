from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response

from ..services import modelos

router = APIRouter(tags=["modelos de importação"])


@router.get("/modelos/{nome}")
def baixar_modelo(nome: str):
    try:
        arquivo, conteudo = modelos.gerar(nome)
    except KeyError:
        raise HTTPException(404, f"Modelo {nome} não existe") from None
    return Response(
        conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(arquivo)}"},
    )
