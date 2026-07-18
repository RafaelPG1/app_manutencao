# ==========================================================
# Arquivo: utils/logger.py
# Responsabilidade: Sistema de logs da aplicação — escolha da
# pasta de log, inicialização do arquivo e escrita de mensagens.
# ==========================================================

import os
import sys
import tempfile
import threading

from config import NOME_PASTA_LOG, NOME_ARQUIVO_LOG
from utils.helpers import agora

# Protege as escritas no arquivo de log: log() é chamado de várias
# threads diferentes (UI, detecção de disco em segundo plano,
# execução de tarefas em lote, TerminalManager) e cada chamada abre e
# fecha o arquivo — sem este lock, escritas concorrentes poderiam se
# intercalar de forma inconsistente.
_lock_log = threading.Lock()


def _resolver_pasta_log() -> str:
    """
    Escolhe uma pasta para o log que realmente aceite escrita.
    Pastas dentro do OneDrive às vezes bloqueiam a escrita de processos
    elevados (Executar como Administrador), então testamos e caímos
    para %LOCALAPPDATA% e depois para a pasta TEMP se necessário.
    """
    candidatos = [os.path.dirname(os.path.abspath(sys.argv[0]))]
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidatos.append(os.path.join(local_appdata, NOME_PASTA_LOG))
    candidatos.append(os.path.join(tempfile.gettempdir(), NOME_PASTA_LOG))

    for pasta in candidatos:
        try:
            os.makedirs(pasta, exist_ok=True)
            teste = os.path.join(pasta, ".write_test.tmp")
            with open(teste, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(teste)
            return pasta
        except Exception:
            continue
    return tempfile.gettempdir()


PASTA_LOG = _resolver_pasta_log()
LOGFILE = os.path.join(PASTA_LOG, NOME_ARQUIVO_LOG)


def log_init():
    """Nunca deve derrubar o app: se o log não puder ser criado, apenas
    seguimos sem registrar (a interface continua funcionando normalmente)."""
    try:
        with _lock_log:
            os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
            novo = not os.path.exists(LOGFILE)
            with open(LOGFILE, "a", encoding="utf-8") as f:
                if novo:
                    f.write("=" * 55 + "\n LOG DE MANUTENÇÃO DO SISTEMA\n")
                    f.write(f" Criado em: {agora()}\n" + "=" * 55 + "\n\n")
                else:
                    f.write("\n" + "=" * 55 + f"\n Nova sessão: {agora()}\n" + "=" * 55 + "\n\n")
    except Exception as e:
        print(f"[AVISO] Não foi possível criar o log em {LOGFILE}: {e}")


def log(msg: str):
    """Escreve no log de forma silenciosa; falhas de log nunca devem
    interromper a execução das tarefas de manutenção."""
    try:
        with _lock_log:
            with open(LOGFILE, "a", encoding="utf-8") as f:
                f.write(str(msg) + "\n")
    except Exception as e:
        print(f"[AVISO] Falha ao gravar log: {e}")
