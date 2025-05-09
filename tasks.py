from invoke import task
import zipfile
import os
import os.path
import shutil
from datetime import datetime, timedelta

@task
def backup(c, source='.', destination='backup', dias_max=7):
    """
    Realiza backup compactado do projeto e remove backups antigos.

    Args:
    dias_max (int): Quantos dias manter os backups antigos.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_backup_dir = os.path.join(destination, f'temp_{timestamp}')
    zip_filename = os.path.join(destination, f'backup_{timestamp}.zip')

    os.makedirs(temp_backup_dir, exist_ok=True)

    # Arquivos a incluir no backup
    itens_para_backup = ['src', 'data', 'tasks.py']

    for item in itens_para_backup:
        if os.path.exists(item):
            destino_item = os.path.join(temp_backup_dir, item)
            try:
                if os.path.isdir(item):
                    shutil.copytree(item, destino_item)
                else:
                    shutil.copy2(item, destino_item)
                print(f"Copiado: {item}")
            except Exception as e:
                print(f"Erro ao copiar {item}: {e}")

    # Compacta o backup
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_backup_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, arcname=os.path.relpath(file_path, temp_backup_dir))

    print(f"\n Backup compactado criado em: {zip_filename}")

    # Remove diretório temporário
    shutil.rmtree(temp_backup_dir)

    # Limpeza de backups antigos
    remover_antigos_backups(destination, dias_max)


def remover_antigos_backups(pasta_backup, dias_max):
    """
    Remove arquivos de backup .zip com mais de X dias.
    """
    agora = datetime.now()
    limite = agora - timedelta(days=int(dias_max))

    for arquivo in os.listdir(pasta_backup):
        if arquivo.endswith('.zip'):
            caminho = os.path.join(pasta_backup, arquivo)
            mod_time = datetime.fromtimestamp(os.path.getmtime(caminho))
            if mod_time < limite:
                os.remove(caminho)
                print(f" Backup antigo removido: {arquivo}")        








@task
def descompactar(c, source='.', destination='backup'):
    maior = ''
    for f in os.listdir(destination):
        if os.path.isfile(os.path.join(destination, f)):
            aux = f
            if aux > maior:
                maior = aux

    with zipfile.ZipFile(os.path.join(destination, maior), 'r') as zip_ref:
        zip_ref.extractall('descompactado')

    print(f"Arquivos extraídos com sucesso")

