# Modelos de documentos

Esqueletos de referência. Preencha **somente com fatos confirmados no código**; use
`<a confirmar>` quando não houver evidência. Dados de exemplo sempre fictícios.

## README

```markdown
# <Nome da aplicação>

<Objetivo em 1–3 frases.>

## Requisitos
- <Runtime> <versão> · <Runtime> <versão>

## Instalação
1. <comando confirmado>
2. <comando confirmado>

## Configuração
| Variável/arquivo | Padrão | Descrição |
|---|---|---|
| `APP_PORTA` | `8000` | Porta HTTP local |

Dados ficam em `<pasta>`; logs em `<pasta>`. Segredos: configure em `<local>`, nunca no repositório.

## Uso
- Iniciar: `<comando>` · Acessar: `http://127.0.0.1:<porta>` · Parar: `<procedimento>`
- Funcionalidades: ver [docs/funcionalidades.md](docs/funcionalidades.md)

## Desenvolvimento
- Verificações antes do commit: `<script local>` (lint, testes, tipos)
- Migrações: `<comando>`

## Limitações conhecidas
- <limitação confirmada>
```

## CHANGELOG (Keep a Changelog)

```markdown
# Changelog
Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) · Versionamento: SemVer.

## [Unreleased]
### Adicionado
- <funcionalidade, do ponto de vista do usuário>

## [1.2.0] - 2026-01-31
### Adicionado
### Alterado
### Corrigido
### Removido
### Segurança
```

## Regra de cálculo

```markdown
# <Nome do cálculo>
- **Onde aparece:** <tela/relatório>
- **Implementação:** `<módulo>.<função>` · **Teste:** `<arquivo de teste>::<caso>`
- **Entradas:** <campo (unidade, origem)>
- **Fórmula:** <expressão>
- **Arredondamento:** <casas, modo (ex.: meio para cima), em que etapa>
- **Datas/cortes:** <dias úteis/corridos, fuso, data-base>
- **Casos-limite:** <zero, negativo, ausência de dado, divisão por zero>
- **Exemplo (fictício):** entradas … → resultado … (igual ao teste citado)
- **Fonte externa:** <origem e periodicidade, se houver>
```

## FAQ / solução de problemas

```markdown
### <Sintoma ou mensagem exibida>
**Causa provável:** …
**Solução:** 1. … 2. …
**Se persistir:** onde ver logs / o que coletar (sem dados pessoais).
```

## ADR

```markdown
# ADR-NNN: <título da decisão>
- **Status:** proposta | aceita | substituída por ADR-MMM | obsoleta
- **Data:** AAAA-MM-DD
## Contexto
## Decisão
## Alternativas consideradas
## Consequências (positivas, negativas, riscos)
```
Local sugerido: `docs/adr/NNN-titulo-curto.md`. ADR aceita não é editada — é substituída.

## Runbook de operação

```markdown
# Runbook — <aplicação>
## Iniciar            — comando, verificação de saúde (URL/status), tempo esperado
## Parar              — parada normal; parada forçada (com cuidado)
## Atualizar versão   — backup → obter versão → dependências → migrações → iniciar → verificar
## Migrações          — aplicar, verificar versão atual, o que fazer se falhar
## Backup             — o que inclui, onde fica, frequência, como validar
## Restaurar          — pré-requisitos, passos, verificação pós-restauração
## Saúde e logs       — onde ficam, níveis, o que procurar
## Problemas comuns   — link para FAQ
## Rollback           — voltar à versão anterior com segurança
```
Cada seção: comandos confirmados, resultado esperado e `NÃO EXECUTADO` quando não testado.

## OpenAPI (FastAPI como exemplo — sem mudar contrato)

```python
@router.get("/registros/{id}", summary="Obtém um registro",
            description="Retorna o registro pelo identificador. 404 se não existir.",
            responses={404: {"description": "Registro não encontrado"}})
```
```python
class Registro(BaseModel):
    nome: str = Field(description="Nome exibido", examples=["Registro Fictício A"])
```
