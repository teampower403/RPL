#!/usr/bin/env python3
import os
import sys
import json
import pickle
import hashlib
import time
import shutil
import argparse
import tempfile
from datetime import datetime
from pathlib import Path

# Configurar encoding para evitar problemas com caracteres especiais
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Verifica e importa watchdog com fallback
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

class RPLSnapshot:
    def __init__(self, version: str, project_path: str):
        self.version = version
        self.project_path = project_path
        self.rpl_dir = os.path.join(project_path, '.rpl')
        self.snapshots_dir = os.path.join(self.rpl_dir, 'snapshots')
        self.changes_dir = os.path.join(self.rpl_dir, 'changes')
        self.auto_save_dir = os.path.join(self.rpl_dir, 'auto_save')
        self.backup_dir = os.path.join(self.rpl_dir, 'backups')
        
        # Criar diretórios necessários
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.changes_dir, exist_ok=True)
        os.makedirs(self.auto_save_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Arquivos de snapshot
        self.structure_file = os.path.join(self.snapshots_dir, f'snapshot_{version}.rpl')
        self.json_file = os.path.join(self.snapshots_dir, f'snapshot_{version}.json')

    def calculate_file_hash(self, filepath: str) -> str:
        """Calcula o hash MD5 de um arquivo"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    def save_file_content(self, filepath: str, rel_path: str):
        """Salva o conteúdo REAL do arquivo no backup"""
        try:
            # Criar nome seguro para o arquivo de backup
            safe_name = rel_path.replace('/', '_').replace('\\', '_').replace(':', '_')
            backup_file = os.path.join(self.backup_dir, f"{safe_name}.bak")
            
            # Copiar o arquivo REAL
            shutil.copy2(filepath, backup_file)
            
            return backup_file
        except Exception as e:
            print(f"  Aviso: Não foi possível salvar {rel_path}: {e}")
            return None

    def scan_project_structure(self) -> dict:
        """Escaneia a estrutura do projeto e salva conteúdo REAL"""
        structure = {
            'version': self.version,
            'timestamp': datetime.now().isoformat(),
            'files': {},
            'directories': [],
            'metadata': {
                'total_size': 0,
                'file_count': 0,
                'backup_dir': self.backup_dir
            }
        }
        
        print("Salvando conteúdo dos arquivos...")
        
        for root, dirs, files in os.walk(self.project_path):
            # Ignorar diretório .rpl
            if '.rpl' in root:
                continue
                
            # Adicionar diretórios
            for dir_name in dirs:
                if dir_name != '.rpl':
                    full_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(full_path, self.project_path)
                    structure['directories'].append(rel_path)
            
            # Adicionar arquivos e salvar conteúdo REAL
            for file_name in files:
                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, self.project_path)
                
                try:
                    # Salvar conteúdo REAL do arquivo
                    backup_path = self.save_file_content(full_path, rel_path)
                    
                    file_info = {
                        'path': rel_path,
                        'size': os.path.getsize(full_path),
                        'modified': os.path.getmtime(full_path),
                        'hash': self.calculate_file_hash(full_path),
                        'backup_file': os.path.basename(backup_path) if backup_path else None,
                        'encoding': 'utf-8'
                    }
                    structure['files'][rel_path] = file_info
                    
                    structure['metadata']['file_count'] += 1
                    structure['metadata']['total_size'] += file_info['size']
                    
                    print(f"  ✓ {rel_path}")
                    
                except Exception as e:
                    print(f"  ✗ Erro em {rel_path}: {e}")
        
        return structure

    def create_snapshot(self) -> bool:
        """Cria uma snapshot da estrutura do projeto COM CONTEÚDO REAL"""
        try:
            print("Escaneando estrutura do projeto...")
            structure = self.scan_project_structure()
            
            # Salvar snapshot binária
            with open(self.structure_file, 'wb') as f:
                pickle.dump(structure, f)
            
            # Salvar snapshot JSON legível
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(structure, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Snapshot {self.version} criada com sucesso!")
            print(f"  Arquivos: {len(structure['files'])}")
            print(f"  Diretórios: {len(structure['directories'])}")
            print(f"  Tamanho total: {structure['metadata']['total_size']} bytes")
            print(f"  Backup salvo em: {self.backup_dir}")
            return True
        except Exception as e:
            print(f"✗ Erro ao criar snapshot: {e}")
            return False

    def restore_file_content(self, file_info: dict) -> bool:
        """Restaura o conteúdo REAL de um arquivo do backup"""
        try:
            rel_path = file_info['path']
            backup_filename = file_info.get('backup_file')
            
            if not backup_filename:
                print(f"  Aviso: Nenhum backup encontrado para {rel_path}")
                return False
            
            # Encontrar o arquivo de backup
            backup_file = os.path.join(self.backup_dir, backup_filename)
            
            if not os.path.exists(backup_file):
                print(f"  Aviso: Arquivo de backup não encontrado: {backup_filename}")
                return False
            
            # Criar diretório se não existir
            full_path = os.path.join(self.project_path, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Copiar o arquivo REAL do backup
            shutil.copy2(backup_file, full_path)
            
            # Restaurar timestamp original se disponível
            if 'modified' in file_info:
                os.utime(full_path, (file_info['modified'], file_info['modified']))
            
            print(f"  ✓ Restaurado: {rel_path}")
            return True
            
        except Exception as e:
            print(f"  ✗ Erro ao restaurar {rel_path}: {e}")
            return False

    def restore_snapshot(self) -> bool:
        """Restaura o projeto COMPLETO a partir de uma snapshot"""
        try:
            if not os.path.exists(self.structure_file):
                print(f"✗ Snapshot {self.version} não encontrada!")
                return False
            
            # Confirmar restauração
            confirm = input(f"⚠️  Isso irá DELETAR todos os arquivos atuais e restaurar a snapshot {self.version}. Continuar? (s/N): ")
            if confirm.lower() not in ['s', 'sim', 'y', 'yes']:
                print("Restauração cancelada.")
                return False
            
            # Carregar snapshot
            with open(self.structure_file, 'rb') as f:
                structure = pickle.load(f)
            
            # Limpar projeto atual (exceto .rpl)
            self.clean_project()
            
            # Recriar estrutura de diretórios
            print("Recriando diretórios...")
            for directory in structure['directories']:
                full_path = os.path.join(self.project_path, directory)
                os.makedirs(full_path, exist_ok=True)
                print(f"  ✓ Diretório: {directory}")
            
            # Recriar arquivos COM CONTEÚDO REAL
            print("Restaurando arquivos...")
            success_count = 0
            total_files = len(structure['files'])
            
            for file_info in structure['files'].values():
                if self.restore_file_content(file_info):
                    success_count += 1
            
            print(f"✓ Projeto restaurado da snapshot {self.version}!")
            print(f"  Arquivos restaurados: {success_count}/{total_files}")
            print(f"  Diretórios restaurados: {len(structure['directories'])}")
            
            return success_count == total_files
            
        except Exception as e:
            print(f"✗ Erro ao restaurar snapshot: {e}")
            return False

    def clean_project(self):
        """Limpa o projeto atual (exceto diretório .rpl)"""
        print("Limpando projeto atual...")
        for item in os.listdir(self.project_path):
            if item != '.rpl':
                item_path = os.path.join(self.project_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print(f"  Aviso: Não foi possível remover {item}: {e}")

class RPLAutoSave:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.rpl_dir = os.path.join(project_path, '.rpl')
        self.auto_save_dir = os.path.join(self.rpl_dir, 'auto_save')
        self.changes_dir = os.path.join(self.rpl_dir, 'changes')
        
        # Criar diretórios
        os.makedirs(self.auto_save_dir, exist_ok=True)
        os.makedirs(self.changes_dir, exist_ok=True)

    def save_file_content(self, filepath: str, change_type: str):
        """Salva o conteúdo real do arquivo"""
        try:
            if '.rpl' in filepath or not os.path.exists(filepath):
                return
                
            rel_path = os.path.relpath(filepath, self.project_path)
            safe_name = rel_path.replace('/', '_').replace('\\', '_').replace(':', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            # Salvar conteúdo do arquivo
            backup_file = os.path.join(self.auto_save_dir, f"{safe_name}_{timestamp}.bak")
            
            if os.path.exists(filepath) and change_type != 'deleted':
                shutil.copy2(filepath, backup_file)
            
            # Registrar mudança
            change_data = {
                'timestamp': datetime.now().isoformat(),
                'type': change_type,
                'file': rel_path,
                'backup_file': os.path.basename(backup_file) if change_type != 'deleted' else None,
                'file_size': os.path.getsize(filepath) if os.path.exists(filepath) else 0
            }
            
            change_file = os.path.join(self.changes_dir, f"change_{timestamp}.json")
            with open(change_file, 'w', encoding='utf-8') as f:
                json.dump(change_data, f, indent=2)
                
        except Exception as e:
            print(f"Erro ao salvar arquivo {filepath}: {e}")

class RPLManager:
    def __init__(self, project_path: str = "."):
        self.project_path = os.path.abspath(project_path)
        self.rpl_dir = os.path.join(self.project_path, '.rpl')
        self.observer = None
        self.tracking = False
        self.auto_save = None
        
    def init_project(self):
        """Inicializa o projeto RPL"""
        if os.path.exists(self.rpl_dir):
            print("✓ Projeto RPL já inicializado")
            return True
            
        os.makedirs(self.rpl_dir, exist_ok=True)
        os.makedirs(os.path.join(self.rpl_dir, 'snapshots'), exist_ok=True)
        os.makedirs(os.path.join(self.rpl_dir, 'changes'), exist_ok=True)
        os.makedirs(os.path.join(self.rpl_dir, 'auto_save'), exist_ok=True)
        os.makedirs(os.path.join(self.rpl_dir, 'backups'), exist_ok=True)
        
        config = {
            'created': datetime.now().isoformat(),
            'project_path': self.project_path,
            'version': '1.0.0'
        }
        
        with open(os.path.join(self.rpl_dir, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Projeto RPL inicializado em: {self.project_path}")
        print(f"  Diretório RPL: {self.rpl_dir}")
        return True

    def create_snapshot(self, version: str):
        """Cria uma nova snapshot"""
        if not os.path.exists(self.rpl_dir):
            print("✗ Projeto RPL não inicializado. Execute 'rpl --init' primeiro.")
            return False
            
        snapshot = RPLSnapshot(version, self.project_path)
        return snapshot.create_snapshot()

    def restore_snapshot(self, version: str):
        """Restaura uma snapshot"""
        if not os.path.exists(self.rpl_dir):
            print("✗ Projeto RPL não inicializado.")
            return False
            
        snapshot = RPLSnapshot(version, self.project_path)
        return snapshot.restore_snapshot()

    def list_snapshots(self):
        """Lista todas as snapshots disponíveis"""
        snapshots_dir = os.path.join(self.rpl_dir, 'snapshots')
        if not os.path.exists(snapshots_dir):
            print("Nenhuma snapshot encontrada")
            return
        
        snapshots = []
        for file in os.listdir(snapshots_dir):
            if file.endswith('.rpl'):
                version = file.replace('snapshot_', '').replace('.rpl', '')
                file_path = os.path.join(snapshots_dir, file)
                size = os.path.getsize(file_path)
                
                # Carregar info da snapshot
                try:
                    with open(file_path, 'rb') as f:
                        snapshot_data = pickle.load(f)
                    file_count = len(snapshot_data.get('files', {}))
                    dir_count = len(snapshot_data.get('directories', []))
                    snapshots.append((version, size, file_count, dir_count))
                except:
                    snapshots.append((version, size, 0, 0))
        
        if snapshots:
            print("Snapshots disponíveis:")
            for snap, size, files, dirs in sorted(snapshots):
                print(f"  - {snap} ({files} arquivos, {dirs} pastas, {size} bytes)")
        else:
            print("Nenhuma snapshot disponível")

    def start_auto_save(self):
        """Inicia o save automático em background"""
        if not WATCHDOG_AVAILABLE:
            print("✗ Funcionalidade de save automático não disponível.")
            print("  Instale: pip install watchdog")
            return False
            
        if self.tracking:
            print("✓ Save automático já está ativo")
            return True
        
        self.auto_save = RPLAutoSave(self.project_path)
        
        class AutoSaveHandler(FileSystemEventHandler):
            def __init__(self, auto_saver):
                self.auto_saver = auto_saver
            
            def on_modified(self, event):
                if not event.is_directory:
                    print(f"📁 Salvando alteração: {os.path.basename(event.src_path)}")
                    self.auto_saver.save_file_content(event.src_path, 'modified')
            
            def on_created(self, event):
                if not event.is_directory:
                    print(f"📁 Novo arquivo: {os.path.basename(event.src_path)}")
                    self.auto_saver.save_file_content(event.src_path, 'created')
            
            def on_deleted(self, event):
                if not event.is_directory:
                    print(f"📁 Arquivo deletado: {os.path.basename(event.src_path)}")
                    self.auto_saver.save_file_content(event.src_path, 'deleted')
            
            def on_moved(self, event):
                if not event.is_directory:
                    print(f"📁 Arquivo movido: {os.path.basename(event.src_path)} -> {os.path.basename(event.dest_path)}")
                    self.auto_saver.save_file_content(event.src_path, 'moved')
                    self.auto_saver.save_file_content(event.dest_path, 'created')
        
        event_handler = AutoSaveHandler(self.auto_save)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.project_path, recursive=True)
        self.observer.start()
        self.tracking = True
        
        print("✓ Save automático iniciado!")
        print("  Todos os arquivos serão salvos automaticamente na pasta .rpl/auto_save/")
        print("  Pressione Ctrl+C para parar")
        
        # Manter o processo rodando
        try:
            while self.tracking:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_auto_save()
        
        return True

    def stop_auto_save(self):
        """Para o save automático"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.tracking = False
        print("✓ Save automático parado")

def show_version():
    """Mostra a versão do RPL"""
    version_info = {
        'RPL Version': '1.0.0',
        'Python': sys.version.split()[0],
        'Watchdog Available': WATCHDOG_AVAILABLE
    }
    
    print("RPL - Versionamento Estrutural")
    for key, value in version_info.items():
        print(f"  {key}: {value}")

def install_to_path():
    """Instala o RPL no PATH do sistema"""
    try:
        # Encontrar o script atual
        current_script = os.path.abspath(__file__)
        
        if os.name == 'nt':  # Windows
            # Criar arquivo batch
            bat_content = f'@echo off\npython "{current_script}" %*'
            bat_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "WindowsApps", "rpl.bat")
            
            os.makedirs(os.path.dirname(bat_path), exist_ok=True)
            with open(bat_path, 'w') as f:
                f.write(bat_content)
            
            print(f"✓ RPL instalado no PATH: {bat_path}")
            print("  Você agora pode usar 'rpl' de qualquer lugar!")
            
        else:  # Linux/Mac
            # Criar link simbólico
            link_path = "/usr/local/bin/rpl"
            os.symlink(current_script, link_path)
            os.chmod(link_path, 0o755)
            print(f"✓ RPL instalado no PATH: {link_path}")
            
    except Exception as e:
        print(f"✗ Erro na instalação: {e}")
        print("  Você pode usar 'python rpl.py' diretamente")

def main():
    parser = argparse.ArgumentParser(
        description='RPL - Versionamento Estrutural com Save Automático',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos:
  rpl --init                    # Inicializar projeto
  rpl -c 1.0.0                 # Criar snapshot
  rpl -r 1.0.0                 # Restaurar snapshot
  rpl --list                   # Listar snapshots
  rpl --auto-save              # Iniciar save automático
  rpl --install                # Instalar no PATH do sistema
  rpl --version                # Mostrar versão
        '''
    )
    parser.add_argument('--init', action='store_true', help='Inicializar projeto RPL')
    parser.add_argument('--create', '-c', type=str, help='Criar snapshot (ex: -c 0.0.1)')
    parser.add_argument('--restore', '-r', type=str, help='Restaurar snapshot (ex: -r 0.0.1)')
    parser.add_argument('--list', '-l', action='store_true', help='Listar snapshots')
    parser.add_argument('--auto-save', '-a', action='store_true', help='Iniciar save automático')
    parser.add_argument('--stop', action='store_true', help='Parar save automático')
    parser.add_argument('--install', action='store_true', help='Instalar no PATH do sistema')
    parser.add_argument('--version', '-v', action='store_true', help='Mostrar versão')
    
    args = parser.parse_args()
    
    if args.version:
        show_version()
        return
    
    if args.install:
        install_to_path()
        return
    
    rpl = RPLManager()
    
    if args.init:
        rpl.init_project()
    elif args.create:
        rpl.create_snapshot(args.create)
    elif args.restore:
        rpl.restore_snapshot(args.restore)
    elif args.list:
        rpl.list_snapshots()
    elif args.auto_save:
        rpl.start_auto_save()
    elif args.stop:
        rpl.stop_auto_save()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()