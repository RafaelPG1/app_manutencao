# ==========================================================
# Arquivo: core/recuperacao/startup_repair.py
# Responsabilidade: Reiniciar o computador diretamente nas Opções de
# Inicialização Avançadas do Windows (WinRE) — categoria Recuperação,
# Fase 3.
#
# IMPORTANTE — por que isso, e não "rodar o Reparo de Inicialização
# direto": o Windows não oferece nenhum comando oficial que dispare o
# Reparo de Inicialização (Startup Repair) diretamente enquanto o
# Windows está funcionando normalmente — ele só existe DENTRO do
# Ambiente de Recuperação do Windows (WinRE), acessível pelo menu
# Solucionar problemas > Opções avançadas > Reparo de Inicialização.
# `shutdown /r /o` é o mecanismo OFICIAL e documentado pela Microsoft
# para reiniciar diretamente nessa tela, sem precisar segurar Shift
# ao clicar em Reiniciar. Nenhuma etapa é pulada nem simulada — o
# usuário só precisa selecionar a opção final no próprio Windows.
#
# AÇÃO DISRUPTIVA: reinicia o computador imediatamente. Por isso NÃO
# é uma tarefa de lote (não pode ser combinada com outras tarefas
# numa mesma execução — a reinicialização interromperia qualquer
# tarefa em andamento) e a confirmação com o usuário é feita na UI
# antes de chamar esta função (ver ui/dialogs.py:
# confirmar_reparo_inicializacao e ui/main_window.py:
# reparo_inicializacao).
# ==========================================================

import subprocess

from utils.helpers import agora
from utils.logger import log


def iniciar_reparo_inicializacao() -> dict:
    """Agenda a reinicialização imediata do computador diretamente nas
    Opções de Inicialização Avançadas. Retorna
    {"sucesso": bool, "mensagem": str} — nunca lança exceção. Se
    retornar sucesso, o computador já está prestes a reiniciar."""
    log(f"[REPARO_INICIALIZACAO] Reinicializacao para WinRE solicitada em {agora()}")
    try:
        resultado = subprocess.run(
            ["shutdown", "/r", "/o", "/f", "/t", "00"],
            capture_output=True, text=True, errors="ignore",
            timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except FileNotFoundError:
        log(f"[REPARO_INICIALIZACAO] ERRO - comando shutdown nao encontrado - {agora()}")
        return {"sucesso": False, "mensagem": "O comando de reinicialização do Windows não foi encontrado."}
    except subprocess.TimeoutExpired:
        log(f"[REPARO_INICIALIZACAO] ERRO - timeout - {agora()}")
        return {"sucesso": False, "mensagem": "O comando de reinicialização não respondeu a tempo."}
    except Exception as e:
        log(f"[REPARO_INICIALIZACAO] ERRO - {e} - {agora()}")
        return {"sucesso": False, "mensagem": f"Não foi possível agendar a reinicialização: {e}"}

    if resultado.returncode != 0:
        detalhe = (resultado.stderr or resultado.stdout or "").strip()
        log(f"[REPARO_INICIALIZACAO] ERRO - codigo {resultado.returncode} - {detalhe} - {agora()}")
        return {
            "sucesso": False,
            "mensagem": "Não foi possível agendar a reinicialização"
            + (f": {detalhe}" if detalhe else " (o Windows recusou o comando)."),
        }

    log(f"[REPARO_INICIALIZACAO] Reinicializacao agendada com sucesso em {agora()}")
    return {
        "sucesso": True,
        "mensagem": (
            "O computador vai reiniciar agora nas Opções de Inicialização Avançadas.\n\n"
            "Quando a tela azul aparecer, selecione:\n"
            "Solucionar problemas  →  Opções avançadas  →  Reparo de Inicialização."
        ),
    }