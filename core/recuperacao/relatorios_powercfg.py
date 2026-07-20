# ==========================================================
# Arquivo: core/recuperacao/relatorios_powercfg.py
# Responsabilidade: Geração dos relatórios oficiais do Windows via
# `powercfg` — bateria (/batteryreport), energia (/energy) e
# eficiência (/sleepstudy) — categoria Recuperação, Fase 3. Os três
# compartilham exatamente a mesma mecânica (rodar o powercfg com
# /output apontando para um arquivo HTML e abrir o resultado), por
# isso ficam num único arquivo com uma função interna comum — mesmo
# racional já usado em core/diagnostico/dism_diagnostico.py para
# CheckHealth/ScanHealth.
#
# RECURSO INDISPONÍVEL (equipamento sem bateria, sem suporte a
# Modern Standby/Sleep Study etc.): em vez de tentar reconhecer o
# texto exato da mensagem de erro do powercfg (que muda conforme o
# idioma do Windows), a checagem de sucesso é feita pela EXISTÊNCIA
# REAL do arquivo de saída. Se o powercfg não conseguiu gerar o
# relatório, o arquivo simplesmente não existe — o que cobre de forma
# uniforme todos os casos pedidos (sem bateria, sem suporte a Sleep
# Study, comando ausente etc.) sem precisar tratar cada um à parte.
# ==========================================================

import os
import subprocess

from utils.helpers import agora
from utils.logger import log

_PASTA_RELATORIOS = os.path.join(os.path.expanduser("~"), "Documents", "RelatoriosManutencao")
_TIMEOUT_SEGUNDOS = 90  # /energy roda por 60s de propósito (comportamento oficial do comando)


def _gerar_relatorio(comando: str, nome_arquivo: str, tag_log: str, titulo_amigavel: str) -> dict:
    try:
        os.makedirs(_PASTA_RELATORIOS, exist_ok=True)
    except OSError as e:
        return {"sucesso": False, "mensagem": f"Não foi possível criar a pasta de relatórios: {e}"}

    caminho = os.path.join(_PASTA_RELATORIOS, nome_arquivo)
    log(f"[{tag_log}] Iniciado em {agora()}")

    try:
        resultado = subprocess.run(
            ["powercfg", f"/{comando}", "/output", caminho],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except FileNotFoundError:
        log(f"[{tag_log}] ERRO - powercfg nao encontrado - {agora()}")
        return {"sucesso": False, "mensagem": "O utilitário powercfg não foi encontrado neste sistema."}
    except subprocess.TimeoutExpired:
        log(f"[{tag_log}] ERRO - timeout - {agora()}")
        return {"sucesso": False, "mensagem": f"A geração do {titulo_amigavel} demorou demais e foi cancelada."}
    except Exception as e:
        log(f"[{tag_log}] ERRO - {e} - {agora()}")
        return {"sucesso": False, "mensagem": f"Falha ao gerar o {titulo_amigavel}: {e}"}

    if not os.path.isfile(caminho):
        motivo = ((resultado.stdout or "") + (resultado.stderr or "")).strip()
        log(f"[{tag_log}] INDISPONIVEL - {motivo} - {agora()}")
        return {
            "sucesso": False,
            "mensagem": (
                f"Não foi possível gerar o {titulo_amigavel}: este recurso não está "
                "disponível neste equipamento ou nesta versão do Windows."
                + (f"\n\nMensagem do Windows: {motivo}" if motivo else "")
            ),
        }

    log(f"[{tag_log}] SUCESSO - {caminho} - {agora()}")
    try:
        os.startfile(caminho)
        aberto = True
    except Exception:
        aberto = False

    aviso = "" if aberto else "\n(Não foi possível abri-lo automaticamente — abra manualmente pelo caminho acima.)"
    return {"sucesso": True, "mensagem": f"{titulo_amigavel} gerado em:\n{caminho}{aviso}"}


def gerar_relatorio_bateria() -> dict:
    """powercfg /batteryreport — indisponível em equipamentos sem
    bateria (desktops, a maioria das VMs)."""
    return _gerar_relatorio("batteryreport", "relatorio_bateria.html", "REL_BATERIA", "relatório de bateria")


def gerar_relatorio_energia() -> dict:
    """powercfg /energy — roda por 60 segundos por padrão (assim o
    Windows consegue observar o comportamento do sistema); demora é
    esperada, não é uma falha."""
    return _gerar_relatorio("energy", "relatorio_energia.html", "REL_ENERGIA", "relatório de energia")


def gerar_relatorio_eficiencia() -> dict:
    """powercfg /sleepstudy — só é suportado em equipamentos com
    Modern Standby/Conectado em Espera; em outros, o próprio Windows
    recusa gerar o relatório (detectado pela ausência do arquivo de
    saída, como os demais)."""
    return _gerar_relatorio(
        "sleepstudy", "relatorio_eficiencia.html", "REL_EFICIENCIA", "relatório de eficiência (Sleep Study)"
    )