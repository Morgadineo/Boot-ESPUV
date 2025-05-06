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
def descompactar(c, zip_path, destino='restaurado'):
    """
    Descompacta um arquivo ZIP em uma pasta destino usando zipfile, os.path e shutil.
    """
    # Verifica se o arquivo existe (os.path)
    if not os.path.exists(zip_path):
        print(f"Arquivo não encontrado: {zip_path}")
        return

    # Verifica se o arquivo é um ZIP válido (zipfile)
    if not zipfile.is_zipfile(zip_path):
        print(f"Não é um arquivo ZIP válido: {zip_path}")
        return

    # Cria diretório com timestamp no nome para os arquivos restaurados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino_temp = os.path.join(destino, f'descompactado_temp_{timestamp}')
    destino_final = os.path.join(destino, f'descompactado_{timestamp}')

    os.makedirs(destino_temp, exist_ok=True)

    try:
        # Extrai o conteúdo (zipfile)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destino_temp)
        print(f"Arquivos extraídos para pasta temporária: {destino_temp}")

        # Copia da pasta temporária para a pasta final (shutil)
        shutil.copytree(destino_temp, destino_final)
        print(f"Arquivos movidos para pasta final: {destino_final}")

    except Exception as e:
        print(f"Erro durante a descompactação: {e}")
    finally:
        # Limpa a pasta temporária (shutil)
        if os.path.exists(destino_temp):
            shutil.rmtree(destino_temp)


