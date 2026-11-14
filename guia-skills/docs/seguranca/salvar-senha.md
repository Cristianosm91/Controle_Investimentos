# Regras — Salvar senha ("Lembrar senha") com DPAPI do Windows

Padrão reutilizável para **persistir a credencial do usuário** ("Lembrar senha")
de forma protegida, sem bibliotecas externas. Copie os trechos e ajuste apenas os
nomes de arquivo/caminho.

> **Escopo:** este documento trata **apenas de como salvar/ler/apagar a senha**.
> A validação da credencial (autenticar ou não contra o servidor) é responsabilidade
> de cada app e **não** faz parte deste padrão.

---

## Conceito

- A senha é criptografada com a **DPAPI do Windows** (`CryptProtectData` /
  `CryptUnprotectData` da `crypt32.dll`), chamada via `ctypes` — **sem dependências
  externas** (nada de `keyring`, `cryptography`, etc.).
- O conteúdo cifrado só pode ser descriptografado pela **mesma conta Windows na
  mesma máquina**. Copiar o arquivo para outra máquina/usuário torna-o inútil.
- O resultado é gravado num arquivo **dedicado** (ex.: `credencial.bin`), que
  **nunca** é versionado.

### Por que DPAPI
- Não exige instalar/empacotar libs de criptografia (facilita o PyInstaller).
- A chave é gerenciada pelo Windows e atrelada à conta do usuário — não há
  segredo embutido no código nem senha em texto puro no disco.

> **Limitação consciente:** a senha é **reversível por design** — o próprio
> processo do usuário consegue recuperá-la em texto (necessário para reenviar no
> HTTP Basic Auth). DPAPI protege contra **outros usuários/máquinas**, não contra
> o próprio usuário. Não use este padrão para segredos que precisem ser
> irrecuperáveis (para isso, use hash, não criptografia reversível).

---

## Regras de ouro (checklist)

1. **DPAPI via `ctypes`**, sem libs externas (`CryptProtectData` / `CryptUnprotectData`).
2. **Arquivo dedicado** (ex.: `credencial.bin`) na pasta do app/exe; nunca misture
   com config de outra natureza.
3. **Salvar só após validar** o login com sucesso **e** somente se o usuário marcou
   **"Lembrar senha"**.
4. **Apagar** a credencial quando: o usuário **desmarca** "Lembrar senha", a senha
   salva ficar **inválida** (ex.: 401 ao usá-la), ou a pedido explícito.
5. **Leitura tolerante a falhas:** qualquer erro de DPAPI (arquivo de outra
   máquina/usuário, corrompido) retorna vazio — **nunca** derruba o app.
6. **API nunca devolve a senha:** endpoints/consultas informam apenas *se existe*
   credencial e, no máximo, o **usuário** — jamais a senha.
7. **`.gitignore`:** o arquivo de credencial **nunca** vai para o repositório.
8. **Logout preserva** a credencial salva (limpa só a sessão em memória), para
   permitir reentrar sem redigitar.

---

## 1. Python — bloco DPAPI (copiar como está)

```python
import ctypes
import json
import os

# Arquivo onde a credencial e guardada (criptografada via DPAPI do Windows)
# quando o usuario marca "Lembrar senha". Fica na pasta do projeto/exe.
_CRED_FILE = os.path.join(_APP_BASE_DIR, "credencial.bin")


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(funcao, dados: bytes) -> bytes:
    """Chama CryptProtectData / CryptUnprotectData (crypt32.dll)."""
    blob_in = _DATA_BLOB(len(dados),
                         ctypes.cast(ctypes.create_string_buffer(dados, len(dados)),
                                     ctypes.POINTER(ctypes.c_char)))
    blob_out = _DATA_BLOB()
    ok = funcao(ctypes.byref(blob_in), None, None, None, None, 0,
                ctypes.byref(blob_out))
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _salvar_credenciais(usuario: str, senha: str) -> None:
    """Criptografa (DPAPI) e grava usuario+senha em credencial.bin."""
    try:
        texto = json.dumps({"usuario": usuario, "senha": senha}).encode("utf-8")
        cifrado = _dpapi(ctypes.windll.crypt32.CryptProtectData, texto)
        with open(_CRED_FILE, "wb") as fp:
            fp.write(cifrado)
    except OSError:
        pass


def _carregar_credenciais():
    """Le e descriptografa credencial.bin. Retorna (usuario, senha) ou (None, None)."""
    try:
        with open(_CRED_FILE, "rb") as fp:
            cifrado = fp.read()
        texto = _dpapi(ctypes.windll.crypt32.CryptUnprotectData, cifrado)
        payload = json.loads(texto.decode("utf-8"))
        usuario = payload.get("usuario")
        senha = payload.get("senha")
        if usuario and senha:
            return usuario, senha
    except (OSError, ValueError):
        pass
    except Exception:
        # Falha de DPAPI (ex.: arquivo de outra maquina/usuario) — ignora.
        pass
    return None, None


def _apagar_credenciais() -> None:
    """Remove o arquivo de credencial salva."""
    try:
        os.remove(_CRED_FILE)
    except OSError:
        pass
```

## 2. Python — quando salvar / apagar (após validar o login)

O salvamento acontece **depois** que o login foi validado com sucesso e apenas
conforme a opção "Lembrar senha":

```python
# ... login ja validado contra o servidor com sucesso ...
_SESSION.update({"usuario": usuario, "senha": senha, "logado": True})

# Atualiza/cria ou remove a credencial salva conforme a opcao "Lembrar senha".
if lembrar:
    _salvar_credenciais(usuario, senha)
else:
    _apagar_credenciais()
```

Descarte automático quando a senha salva ficou inválida (ex.: troca de senha):

```python
if resp.status_code == 401:
    if usar_salva:          # o usuario tentou entrar com a senha salva
        _apagar_credenciais()
    return jsonify({"ok": False, "erro": "Usuario ou senha incorretos."}), 401
```

## 3. Python — expor à interface sem vazar a senha

A API informa apenas **se existe** credencial e o **usuário** — nunca a senha:

```python
@app.route("/api/credencial", methods=["GET"])
def api_credencial():
    """Informa se existe credencial salva (apenas o usuario, nunca a senha)."""
    usuario, _senha = _carregar_credenciais()
    return jsonify({"existe": bool(usuario), "usuario": usuario})
```

No front, quando há senha salva e o usuário não digitou nova senha, envie um
flag `usar_salva=True` com a senha vazia — o backend reusa a salva:

```javascript
const usarSalva = TEM_SENHA_SALVA && senha === '';
await api('/api/login', { usuario, senha, lembrar, usar_salva: usarSalva });
```

## 4. Logout — preservar a credencial

```python
@app.route("/api/logout", methods=["POST"])
def api_logout():
    # Encerra apenas a sessao em memoria; a credencial salva (se houver) e
    # mantida para permitir entrar novamente sem redigitar a senha.
    _SESSION.update({"usuario": None, "senha": None, "logado": False})
    return jsonify({"ok": True})
```

## 5. `.gitignore` — nunca versionar

```gitignore
# Credencial salva (DPAPI) — nunca versionar
credencial.bin
```

---

## Checklist ao adicionar "Lembrar senha" a um app

- [ ] Bloco DPAPI (`_dpapi`, `_salvar/_carregar/_apagar_credenciais`) copiado sem libs externas.
- [ ] Arquivo `credencial.bin` em pasta do app e no `.gitignore`.
- [ ] Salva **apenas** após validar o login **e** com "Lembrar senha" marcado.
- [ ] Apaga ao desmarcar, ao dar 401 usando a salva, ou a pedido.
- [ ] Leitura tolerante a falha (retorna `(None, None)` sem quebrar).
- [ ] API/consulta nunca retorna a senha (só `existe` + `usuario`).
- [ ] Logout mantém a credencial salva.
