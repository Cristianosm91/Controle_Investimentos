# Manuseio de dados sensíveis

## Classificação e minimização
Identifique somente o necessário para avaliar o fluxo: dados pessoais/sensíveis, financeiros,
transacionais, credenciais, tokens, cookies, chaves, certificados, dados de cliente e informações
operacionais. Não reproduza valores completos.

## Segredos
- Nunca usar, testar, decodificar ou reutilizar segredos encontrados.
- Relatar tipo e localização; usar máscara parcial somente quando indispensável.
- Não enviar a serviços de scanner, issue tracker ou chat externo sem autorização explícita.
- Recomendar revogação/rotação pelo responsável em canal seguro; não executar rotação.

## Dados pessoais/financeiros
- Usar dados sintéticos e mascarados em testes e exemplos.
- Não abrir, extrair, copiar ou exportar registros reais para comprovar risco.
- Mascarar identificadores e payloads em screenshots, logs e relatórios.
- Evitar armazenar dados brutos em evidências; restringir acesso e retenção do relatório.

Se dados reais surgirem inesperadamente, pare a atividade que possa ampliá-los, minimize a evidência,
mascare e informe a limitação e o canal seguro para o responsável.