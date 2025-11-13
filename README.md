# RPL - Snapshot Estrutural e Backup Automático

**Uma ferramenta de snapshot estrutural e backup automático para projetos de desenvolvimento**

---

## 📌 Características Principais

### 📂 Snapshots Estruturais
- **Cria snapshots completos** da estrutura do projeto  
- **Armazena conteúdo real** dos arquivos (não apenas metadados)  
- **Versões organizadas** com controle semântico (0.0.1, 1.0.0, etc.)  
- **Restauração completa** do projeto para qualquer versão  

### 🔄 Backup Automático
- **Monitoramento em tempo real** de mudanças nos arquivos  
- **Backup automático** de arquivos criados, modificados ou deletados  
- **Histórico de alterações** com timestamp preciso  
- **Funciona em background** sem interromper o fluxo de trabalho  

---

## 📁 Estrutura de Dados

```
.projeto/
├── .rpl/
│   ├── config.json              # Configuração do projeto
│   ├── snapshots/               # Snapshots versionadas
│   │   ├── snapshot_1.0.0.rpl
│   │   ├── snapshot_1.0.0.json
│   │   └── ...
│   ├── backups/                 # Conteúdo real dos arquivos
│   │   └── arquivos_backup/
│   ├── auto_save/               # Backups automáticos
│   │   └── arquivos_timestamp.bak
│   └── changes/                 # Histórico de mudanças
│       └── change_timestamp.json
└── (seus arquivos do projeto)
```
## 🛠️ como instalar
no momento o comando install está com problema, vimos isso de última hora então aguarde até isso ser corrigido, façam pull-requests para ajudarmos nessa tarefa.
## 📘 Como Usar

### 🔹 Inicializar Projeto

```powershell
# Dentro da pasta do seu projeto
python3 rpl.py --init
```

---

### 🔹 Criar Snapshots

```powershell
# Criar snapshot versão 1.0.0
python3 rpl.py --create 1.0.0

# Criar snapshot com alias
python3 rpl.py -c 1.0.1
```

---

### 🔹 Listar Snapshots

```powershell
python3 rpl.py --list
```

---

### 🔹 Backup Automático

```powershell
# Iniciar monitoramento automático
python3 rpl.py --auto-save

# Parar monitoramento
python3 rpl.py --stop
```

---

## 📄 Licença
MIT License

---

## ✨ Contribuições
Pull requests são bem-vindos!  
Sugestões, melhorias e novas funcionalidades também!
