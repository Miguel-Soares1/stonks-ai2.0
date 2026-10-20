# Guia de Instalação

## 📋 Pré-requisitos

| Requisito | Versão Mínima | Obrigatório? |
|-----------|--------------|--------------|
| Python | 3.11+ | ✅ Sim |
| pip | 21+ | ✅ Sim |
| Ollama | Qualquer | ⭕ Para análise com IA |

---

## 🪟 Windows

### 1. Python

```powershell
# Verificar versão
python --version

# Se não tiver, baixe em: https://www.python.org/downloads/
```

### 2. Instalar Stonks AI

```powershell
# Via pip (recomendado)
pip install stonks-ai

# Ou via source
git clone https://github.com/seu-usuario/stonks-ai.git
cd stonks-ai
pip install -e .
```

### 3. Ollama (opcional)

Baixe o instalador em [ollama.com/download](https://ollama.com/download) e execute.

```powershell
# Baixar modelo recomendado
ollama pull llama3.2:3b

# Verificar se está rodando
ollama list
```

### 4. Inicializar

```powershell
stonks init
```

---

## 🐧 Linux

### 1. Python + pip

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Fedora
sudo dnf install python3 python3-pip

# Arch
sudo pacman -S python python-pip
```

### 2. Instalar Stonks AI

```bash
# Ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate

# Instalar
pip install stonks-ai
```

### 3. Ollama (opcional)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

### 4. Inicializar

```bash
stonks init
```

---

## 🍎 macOS

### 1. Python

```bash
# Usando Homebrew
brew install python@3.12
```

### 2. Instalar Stonks AI

```bash
# Ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar
pip install stonks-ai
```

### 3. Ollama (opcional)

```bash
brew install ollama
ollama serve &
ollama pull llama3.2:3b
```

### 4. Inicializar

```bash
stonks init
```

---

## 📦 Instalação via pip (desenvolvimento)

```bash
git clone https://github.com/seu-usuario/stonks-ai.git
cd stonks-ai
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -e ".[dev]"
```

---

---

## ✅ Verificação

```bash
# Verificar instalação
stonks --version

# Verificar saúde do sistema
stonks init

# Testar cotação
stonks quote PETR4

# Testar finanças pessoais
stonks finance dashboard
```
