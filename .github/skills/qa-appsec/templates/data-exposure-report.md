# Relatório de exposição de dados

## Escopo e proteção
- Aplicação/versão:
- Componentes autorizados:
- Data e perfil:
- Dados de teste: sintéticos / descrição sem valores reais:
- Limitações:

## Classes de dados observadas
| Classe | Sensibilidade | Origem | Finalidade/uso | Retenção conhecida | Evidência sanitizada |
|---|---|---|---|---|---|
| Pessoal/financeira/transacional/credencial/operacional | | | | | |

## Fluxo de dados

```text
ORIGEM -> COLETA -> PROCESSAMENTO -> ARMAZENAMENTO -> TRANSMISSÃO -> COMPARTILHAMENTO -> DESTINO -> RETENÇÃO -> DESCARTE
```

| Etapa/componente | Atores com acesso | Permissões | Criptografia/mascaramento | Logs/cópias | Controle/lacuna |
|---|---|---|---|---|---|

## Possíveis pontos de exposição
| ID | Dado em risco e classe | Local/canal | Estado | Caminho potencial descrito | Impacto/probabilidade/confiança | Controle compensatório | Recomendação |
|---|---|---|---|---|---|---|---|

## Retenção e descarte
- Finalidade e necessidade:
- Retenção documentada e execução observada:
- Backups, temporários, cache e telemetria:
- Recomendação de minimização/expurgo:

Não copiar nem exfiltrar dados reais. Mascarar identificadores e interromper qualquer atividade que
amplie exposição. Se um segredo for encontrado, informar somente tipo e localização; não incluir valor.