# 🔧 XMPP Server Setup Guide

Para usar o sistema SPADE real, precisas de um servidor XMPP a correr localmente.

## 📋 **Opção 1: Prosody (RECOMENDADO - Mais fácil)**

### **Windows - Instalação:**

```powershell
# Download Prosody
# https://prosody.im/download/start

# Ou via Chocolatey
choco install prosody
```

### **Configuração:**

1. Editar `C:\Program Files\Prosody\prosody.cfg.lua`:

```lua
admins = { "admin@localhost" }

modules_enabled = {
    "roster"; "saslauth"; "tls"; "dialback";
    "disco"; "posix"; "private"; "vcard";
    "version"; "uptime"; "time"; "ping";
    "pep"; "register"; "admin_adhoc";
}

allow_registration = true

VirtualHost "localhost"
    enabled = true
```

2. Iniciar Prosody:

```powershell
prosody start
```

3. Criar users (fazer 48x - chato mas funciona):

```powershell
prosodyctl register station0 localhost password
prosodyctl register station1 localhost password
# ... até station14

prosodyctl register vehicle0 localhost password
# ... até vehicle9

prosodyctl register passenger0 localhost password
# ... até passenger19

prosodyctl register maintenance0 localhost password
prosodyctl register maintenance1 localhost password
prosodyctl register maintenance2 localhost password
```

---

## 📋 **Opção 2: Ejabberd (Mais robusto)**

### **Windows - Instalação:**

```powershell
# Download ejabberd installer
# https://www.process-one.net/en/ejabberd/downloads/

# Instalar via installer
```

### **Configuração:**

1. Editar `ejabberd.yml`:

```yaml
hosts:
  - localhost

listen:
  -
    port: 5222
    module: ejabberd_c2s
    max_stanza_size: 262144
    shaper: c2s_shaper
    access: c2s

register:
  allow: all

acl:
  admin:
    user:
      - "admin@localhost"
```

2. Criar users via web admin:
   - Aceder: http://localhost:5280/admin
   - Username: admin@localhost
   - Criar os 48 users manualmente

---

## 📋 **Opção 3: Script Automático (Python)**

Criar ficheiro `setup_xmpp_users.py`:

```python
import subprocess

users = []

# Station users
users.extend([f"station{i}" for i in range(15)])

# Vehicle users
users.extend([f"vehicle{i}" for i in range(10)])

# Passenger users
users.extend([f"passenger{i}" for i in range(20)])

# Maintenance users
users.extend([f"maintenance{i}" for i in range(3)])

# Create all users (Prosody)
for user in users:
    cmd = f'prosodyctl register {user} localhost password'
    subprocess.run(cmd, shell=True)
    print(f"✅ Created {user}@localhost")

print(f"\n✅ Total users created: {len(users)}")
```

Executar:
```powershell
python setup_xmpp_users.py
```

---

## 🧪 **Testar XMPP Server:**

```powershell
# Ver status Prosody
prosodyctl status

# Ver users criados
prosodyctl about

# Testar conexão
telnet localhost 5222
```

---

## ✅ **Verificar se está pronto:**

1. ✅ Servidor XMPP a correr na porta 5222
2. ✅ 48 users criados (@localhost)
3. ✅ `allow_registration = true` configurado

Depois executa:
```powershell
python main.py
```

---

## 🚨 **Se não conseguires instalar XMPP:**

Usa o demo sem XMPP:
```powershell
python demo.py
```

O demo simula o comportamento mas não usa SPADE real.

---

## 📞 **Troubleshooting:**

### **Erro: Connection Refused**
- Verifica se Prosody está a correr: `prosodyctl status`
- Verifica porta: `netstat -an | findstr 5222`

### **Erro: Authentication Failed**
- Users não foram criados corretamente
- Verifica: `prosodyctl check`

### **Erro: Module Not Found**
- Verifica módulos em `prosody.cfg.lua`
- Reinicia: `prosodyctl restart`

---

## 💡 **Alternativa: Docker**

Se tiveres Docker:

```powershell
docker run -d -p 5222:5222 -p 5280:5280 ejabberd/ecs
```

Depois cria users via API ou web admin.
