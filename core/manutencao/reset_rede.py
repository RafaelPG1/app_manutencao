# ==========================================================
# Arquivo: core/manutencao/reset_rede.py
# Responsabilidade: Reset completo da pilha de rede — categoria
# Manutenção, Fase 5. Usa somente comandos oficiais do Windows:
#   - netsh winsock reset   (redefine o catálogo Winsock)
#   - netsh int ip reset    (redefine a pilha TCP/IP)
#   - ipconfig /flushdns    (limpa o cache de DNS)
#
# A limpeza de DNS REAPROVEITA a tarefa já existente
# core/limpeza/dns.py:limpar_dns() em vez de duplicar o comando aqui
# — mesmo reporter, mesmo log, mesmo texto de sempre.
#
# netsh winsock reset e netsh int ip reset só têm efeito completo
# após reiniciar o computador (comportamento documentado da própria
# Microsoft) — por isso esta tarefa é declarada com
# requer_reinicializacao=True em utils/tasks.py, e também avisa
# diretamente o usuário ao final (reporter.log), já que essa
# informação é relevante mesmo antes de qualquer aviso resumido do
# lote.
# ==========================================================

from utils.helpers import agora, executar_comando
from utils.logger import log
from core.limpeza.dns import limpar_dns


def resetar_rede(reporter):
    reporter.log("[INFO] Iniciando reset completo da pilha de rede...\n", "titulo")
    reporter.message("Redefinindo Winsock e TCP/IP...")
    log(f"[RESET_REDE] Iniciado em {agora()}")

    rc1, out1, _err1 = executar_comando(["netsh", "winsock", "reset"])
    log(out1)
    if rc1 == 0:
        reporter.log("[INFO] Catálogo Winsock redefinido.\n")
        log(f"[RESET_REDE] Winsock OK - {agora()}")
    else:
        reporter.log(f"[AVISO] Falha ao redefinir o Winsock (código {rc1}).\n", "aviso")
        log(f"[RESET_REDE] AVISO - Winsock falhou codigo {rc1} - {agora()}")

    rc2, out2, _err2 = executar_comando(["netsh", "int", "ip", "reset"])
    log(out2)
    if rc2 == 0:
        reporter.log("[INFO] Pilha TCP/IP redefinida.\n")
        log(f"[RESET_REDE] TCP/IP OK - {agora()}")
    else:
        reporter.log(f"[AVISO] Falha ao redefinir a pilha TCP/IP (código {rc2}).\n", "aviso")
        log(f"[RESET_REDE] AVISO - TCP/IP falhou codigo {rc2} - {agora()}")

    # Reaproveita a tarefa de limpeza de DNS já existente (mesmo
    # reporter, para que a mensagem apareça na mesma tarefa em
    # andamento em vez de como uma tarefa separada no lote).
    limpar_dns(reporter)

    reporter.log(
        "[AVISO] Reinicie o computador para que o reset de rede tenha efeito completo.\n",
        "aviso",
    )
    log(f"[RESET_REDE] Concluído - reinicialização necessária - {agora()}")