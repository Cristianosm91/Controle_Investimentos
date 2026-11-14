---
name: salvar-senha
description: 'Use ao implementar "Lembrar senha" / persistência de credencial em apps Windows — salvar, ler e apagar a senha do usuário de forma protegida com a DPAPI do Windows (CryptProtectData/CryptUnprotectData via ctypes), sem bibliotecas externas. Cobre apenas a persistência da senha, não a autenticação. Palavras-gatilho: lembrar senha, salvar senha, persistir credencial, credencial.bin, DPAPI, CryptProtectData, CryptUnprotectData, crypt32, guardar senha.'
---

# Salvar senha ("Lembrar senha")

Padrão reutilizável para **persistir a credencial do usuário** de forma protegida,
sem dependências externas. As regras completas ficam em `guia-skills/docs/seguranca/`.

> **Escopo:** trata **apenas de salvar/ler/apagar a senha**. A validação da
> credencial (autenticar contra o servidor) é responsabilidade de cada app e
> **não** faz parte deste padrão.

## Quando usar
- Adicionar uma opção **"Lembrar senha"** a um app.
- **Salvar, ler ou apagar** uma credencial persistida entre sessões.
- Decidir **onde/como** guardar a senha sem vazá-la nem versioná-la.

## Fonte de verdade (leia antes de aplicar)
- Salvar senha (DPAPI): [docs/seguranca/salvar-senha.md](../../../guia-skills/docs/seguranca/salvar-senha.md)

## Regras que NÃO podem ser esquecidas
1. **DPAPI via `ctypes`**, sem libs externas (`CryptProtectData` / `CryptUnprotectData`).
   Só a mesma conta Windows na mesma máquina descriptografa.
2. **Salvar só após validar** o login **e** com "Lembrar senha" marcado.
3. **Apagar** ao desmarcar, ao receber 401 usando a senha salva, ou a pedido.
4. **Leitura tolerante a falha:** erro de DPAPI → retorna vazio, nunca derruba o app.
5. **Nunca vaze a senha:** a API expõe só *se existe* + o **usuário**, jamais a senha.
6. **`.gitignore`:** o arquivo de credencial (ex.: `credencial.bin`) nunca é versionado.
7. **Logout preserva** a credencial salva (limpa só a sessão em memória).

> **Limitação consciente:** a senha é reversível por design (o próprio processo do
> usuário a recupera em texto para reenviar no Basic Auth). DPAPI protege contra
> outros usuários/máquinas, não contra o próprio usuário.

## Procedimento
1. Abra [docs/seguranca/salvar-senha.md](../../../guia-skills/docs/seguranca/salvar-senha.md).
2. Copie o bloco DPAPI (`_dpapi`, `_salvar/_carregar/_apagar_credenciais`) e ajuste
   o nome/caminho do arquivo de credencial.
3. Ligue o salvar/apagar ao fluxo de login (após validar) e à opção "Lembrar senha".
4. Confira o checklist do documento antes de gerar o `.exe`.
