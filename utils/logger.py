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


def limpar_log() -> bool:
    """Apaga o conteúdo do LOGFILE e recomeça com um cabeçalho novo,
    no mesmo formato usado por log_init().

    Usado pela tela de Configurações ("Limpar histórico e logs" —
    Fase 8). Como ler_historico() reconstrói o Histórico a partir
    deste MESMO arquivo (ver comentário abaixo), não existem dois
    armazenamentos separados: limpar o log também limpa o histórico,
    e vice-versa — por isso uma única função cobre as duas ações da
    tela de Configurações.

    Nunca lança exceção — mesma postura do resto deste módulo.
    Retorna True/False para a tela decidir a mensagem exibida."""
    try:
        with _lock_log:
            os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
            with open(LOGFILE, "w", encoding="utf-8") as f:
                f.write("=" * 55 + "\n LOG DE MANUTENÇÃO DO SISTEMA\n")
                f.write(f" Limpo em: {agora()}\n" + "=" * 55 + "\n\n")
        return True
    except Exception as e:
        print(f"[AVISO] Não foi possível limpar o log em {LOGFILE}: {e}")
        return False


# ==========================================================
# Leitura estruturada do histórico (tela "Histórico")
#
# NÃO é um novo formato/arquivo de log: continua sendo o mesmo
# LOGFILE, escrito exclusivamente através da função log() acima. A
# única adição é que core/execution/execution_manager.py agora também
# grava, além das linhas de texto livre que já existiam (ex.: "[SFC]
# Concluído..."), um pequeno conjunto de linhas com um formato fixo e
# previsível, sempre começando com a tag "[HISTORICO]" — para que
# esta tela consiga reconstruir "o que rodou, quando e com que
# resultado" sem depender de interpretar o texto livre e variado que
# cada módulo de core/ já escrevia à sua própria maneira (um por
# tarefa, cada um com um rótulo diferente — DNS, TEMP, LIXEIRA,
# THUMBNAIL, WINUPDATE, DISM, SFC, CHKDSK etc. — o que tornaria o
# parser frágil e obrigado a conhecer cada um deles).
#
# Formato das linhas adicionadas (uma por evento, sempre em um único
# `log()`, nunca span múltiplas linhas):
#   [HISTORICO] LOTE_INICIO | data=<dd/mm/aaaa hh:mm:ss> | tarefas=<chave,chave,...>
#   [HISTORICO] TAREFA | chave=<chave> | titulo=<texto> | estado=<concluida|erro> | duracao_s=<float>
#   [HISTORICO] LOTE_FIM | data=<dd/mm/aaaa hh:mm:ss> | duracao_s=<float>
#
# Um lote incompleto (ex.: o aplicativo foi encerrado no meio de uma
# execução, sem LOTE_FIM) ainda é exibido, marcado como tal — as
# tarefas que já tinham terminado continuam visíveis.
# ==========================================================

_TAG_HISTORICO = "[HISTORICO]"


def _parse_campos(resto: str) -> dict:
    """Extrai um dicionário simples de uma linha no formato
    "chave=valor | chave=valor | ...". Usado só pelo parser de
    histórico abaixo — nenhuma tarefa deve gerar esse formato
    diretamente; é responsabilidade exclusiva do ExecutionManager."""
    campos = {}
    for parte in resto.split(" | "):
        parte = parte.strip()
        if not parte or "=" not in parte:
            continue
        chave, _, valor = parte.partition("=")
        campos[chave.strip()] = valor.strip()
    return campos


def ler_historico(limite: int = 50) -> list:
    """Lê o LOGFILE e reconstrói a lista de execuções em lote
    passadas, mais recente primeiro, cada uma no formato:

        {
            "data_inicio": str, "data_fim": str | None,
            "duracao_s": float | None, "completo": bool,
            "tarefas": [
                {"chave": str, "titulo": str, "estado": str,
                 "duracao_s": float}, ...
            ],
        }

    Nunca lança exceção: se o arquivo não existir ou não puder ser
    lido, devolve uma lista vazia — a tela de Histórico trata isso
    como "nenhuma execução registrada ainda", sem diferenciar do caso
    de um log realmente vazio (a distinção não muda o que é exibido).
    """
    try:
        with open(LOGFILE, "r", encoding="utf-8", errors="ignore") as f:
            linhas = f.readlines()
    except OSError:
        return []

    lotes = []
    lote_atual = None
    for linha in linhas:
        linha = linha.rstrip("\n")
        if _TAG_HISTORICO not in linha:
            continue
        resto = linha.split(_TAG_HISTORICO, 1)[1].strip()

        if resto.startswith("LOTE_INICIO"):
            campos = _parse_campos(resto[len("LOTE_INICIO"):].lstrip("| ").strip())
            lote_atual = {
                "data_inicio": campos.get("data", "—"),
                "data_fim": None,
                "duracao_s": None,
                "completo": False,
                "tarefas": [],
            }
            lotes.append(lote_atual)
        elif resto.startswith("TAREFA") and lote_atual is not None:
            campos = _parse_campos(resto[len("TAREFA"):].lstrip("| ").strip())
            try:
                duracao = float(campos.get("duracao_s", 0))
            except ValueError:
                duracao = 0.0
            lote_atual["tarefas"].append({
                "chave": campos.get("chave", "?"),
                "titulo": campos.get("titulo", campos.get("chave", "?")),
                "estado": campos.get("estado", "?"),
                "duracao_s": duracao,
            })
        elif resto.startswith("LOTE_FIM") and lote_atual is not None:
            campos = _parse_campos(resto[len("LOTE_FIM"):].lstrip("| ").strip())
            try:
                duracao_total = float(campos.get("duracao_s", 0))
            except ValueError:
                duracao_total = None
            lote_atual["data_fim"] = campos.get("data", "—")
            lote_atual["duracao_s"] = duracao_total
            lote_atual["completo"] = True
            lote_atual = None

    lotes.reverse()  # mais recente primeiro
    return lotes[:limite] if limite else lotes