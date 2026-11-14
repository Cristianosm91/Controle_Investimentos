# Guia — Autenticação (SSH / PAT) e Commits Assinados

## Objetivo

Conectar sua máquina ao GitLab com segurança (sem digitar senha a cada `push`) e,
opcionalmente, **assinar os commits** para ganhar o selo **Verified**.

Há dois métodos de autenticação — escolha **um**:

- **SSH** — recomendado para o dia a dia. Uma chave por máquina.
- **PAT (Personal Access Token)** — token que substitui a senha no HTTPS. Útil
  quando SSH está bloqueado por firewall/proxy corporativo.

---

## 1. Autenticação por SSH (recomendado)

### 1.1. Verificar se já existe uma chave

```bash
ls -al ~/.ssh
```

Procure por `id_ed25519.pub` (ou `id_rsa.pub`). Se existir, pule para 1.3.

### 1.2. Gerar uma chave nova

```bash
ssh-keygen -t ed25519 -C "seu.email@empresa.com"
```

- Aceite o caminho padrão (`~/.ssh/id_ed25519`).
- Defina uma **passphrase** (opcional, mas recomendado).

### 1.3. Adicionar a chave ao agente

```bash
# Linux/macOS/Git Bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

```powershell
# Windows (PowerShell) — inicia o serviço do agente e adiciona a chave
Start-Service ssh-agent
ssh-add "$env:USERPROFILE\.ssh\id_ed25519"
```

### 1.4. Cadastrar a chave pública no GitLab

```bash
# copie o conteúdo da chave PÚBLICA (.pub)
cat ~/.ssh/id_ed25519.pub
```

No GitLab: **Preferences → SSH Keys → Add new key**, cole o conteúdo, dê um
título (ex.: "Notebook do trabalho") e salve.

### 1.5. Testar

```bash
ssh -T git@gitlab.com
# ou o host interno, ex.: ssh -T git@gitlab.empresa.com
```

Deve responder com "Welcome to GitLab, @seu.usuario!".

### 1.6. Usar a URL SSH no repositório

```bash
git remote set-url origin git@gitlab.com:grupo/projeto.git
```

---

## 2. Autenticação por PAT (HTTPS)

Quando o SSH não é viável. O token substitui a senha nos comandos HTTPS.

### 2.1. Criar o token

No GitLab: **Preferences → Access Tokens → Add new token**.

- **Scopes:** marque `write_repository` (e `read_repository`).
- Defina uma **data de expiração** (ex.: 90 dias).
- **Copie o token na hora** — ele não é mostrado de novo.

### 2.2. Usar o token

No primeiro `git push` via HTTPS, informe:

- **Username:** seu usuário do GitLab
- **Password:** **cole o token** (não a sua senha)

Para não digitar sempre, use um *credential helper*:

```bash
# Windows
git config --global credential.helper manager

# macOS
git config --global credential.helper osxkeychain

# Linux (guarda em disco; use com cuidado)
git config --global credential.helper store
```

> ⚠️ **Nunca** cole o token em código, README, chat ou screenshot. Trate-o como
> senha. Se vazar, **revogue** imediatamente em Access Tokens.

---

## 3. Commits assinados (opcional) — selo *Verified*

Assinar prova que o commit foi realmente feito por você. O GitLab mostra um
selo **Verified** ao lado do commit. Duas opções: **SSH** (mais simples, reusa
a chave acima) ou **GPG**.

### 3.1. Assinatura por SSH (recomendada, reusa a chave)

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true   # assina todo commit automaticamente
```

Depois, cadastre a **mesma chave pública** no GitLab em
**Preferences → SSH Keys**, agora marcando o uso **"Signing"** (ou adicione-a
também como *Signing key*, conforme a versão do GitLab).

### 3.2. Assinatura por GPG (alternativa)

```bash
# gerar a chave
gpg --full-generate-key

# listar e pegar o ID da chave
gpg --list-secret-keys --keyid-format=long

# configurar o Git (troque <KEY_ID> pelo ID)
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
```

Exporte a chave pública e cadastre em **Preferences → GPG Keys**:

```bash
gpg --armor --export <KEY_ID>
```

### 3.3. Assinar um commit pontual

Se **não** quiser assinar tudo automaticamente:

```bash
git commit -S -m "feat(export): adiciona exportação CSV"
```

### 3.4. Conferir

```bash
git log --show-signature -1
```

No GitLab, o commit aparece com o selo **Verified**.

---

## Checklist

- [ ] SSH **ou** PAT configurado e testado.
- [ ] `origin` usando a URL correta (SSH ou HTTPS).
- [ ] Credential helper configurado (se HTTPS/PAT).
- [ ] Token com expiração e escopo mínimo (se PAT).
- [ ] (Opcional) `commit.gpgsign = true` e chave de assinatura cadastrada.
- [ ] Nenhum token/segredo versionado ou compartilhado.
