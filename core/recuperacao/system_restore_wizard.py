# ==========================================================
# Arquivo: core/recuperacao/system_restore_wizard.py
# Responsabilidade: Abrir o assistente OFICIAL de Restauração do
# Sistema do Windows (rstrui.exe) — categoria Recuperação, Fase 3.
#
# NÃO reimplementa nada da lógica de restauração: só abre a própria
# ferramenta nativa do Windows, que assume o controle a partir daí
# (é uma janela própria do Windows, fora do aplicativo). Por isso
# esta é uma AÇÃO INSTANTÂNEA (ver o cabeçalho de
# core/diagnostico/espaco_disco.py para o racional completo desse
# padrão) — não há "progresso" nem "resultado" para acompanhar: ou o
# assistente abre, ou não abre.
# ==========================================================

import subprocess

from utils.helpers import agora
from utils.logger import log


def abrir_restaurar_sistema() -> dict:
    """Abre rstrui.exe (assistente oficial de Restauração do Sistema)
    em uma janela própria do Windows. Retorna
    {"sucesso": bool, "mensagem": str} — nunca lança exceção."""
    try:
        subprocess.Popen(["rstrui.exe"])
    except FileNotFoundError:
        log(f"[RESTAURAR_SISTEMA] ERRO - rstrui.exe nao encontrado - {agora()}")
        return {
            "sucesso": False,
            "mensagem": "O assistente de Restauração do Sistema (rstrui.exe) não foi encontrado neste computador.",
        }
    except Exception as e:
        log(f"[RESTAURAR_SISTEMA] ERRO - {e} - {agora()}")
        return {"sucesso": False, "mensagem": f"Não foi possível abrir o assistente de Restauração do Sistema: {e}"}

    log(f"[RESTAURAR_SISTEMA] Assistente aberto em {agora()}")
    return {
        "sucesso": True,
        "mensagem": "O assistente de Restauração do Sistema foi aberto em uma nova janela do Windows.",
    }