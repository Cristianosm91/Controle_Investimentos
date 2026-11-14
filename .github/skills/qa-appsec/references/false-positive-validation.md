# Validação de falsos positivos

Antes de classificar um alerta como achado:

1. Confirme arquivo, versão, dependência ou componente efetivamente analisado.
2. Leia o contexto e a origem do dado; siga o fluxo até a operação sensível sem executar exploração.
3. Verifique sanitização, autorização, configuração, feature flag, ambiente e controles compensatórios.
4. Avalie alcançabilidade, pré-condições, privilégio requerido e se o componente está ativo.
5. Compare a faixa afetada e advisory aplicável; considere backport, fork e fix do fornecedor.
6. Procure evidência independente ou teste seguro existente; não invente uma reprodução.
7. Registre incerteza e confiança; classifique como potencial/requer validação manual quando não conclusivo.

Um scanner fornece sinal, não veredito. Preserve evidência mínima e não marque como falso positivo só
porque não foi possível testar. Não use CVE/CWE de forma decorativa ou sem correspondência técnica.