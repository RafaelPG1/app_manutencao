# ==========================================================
# Arquivo: core/laboratorio/erro.py
# Responsabilidade: Teste de ERRO do Laboratório — executa
# normalmente até ~70% e então lança uma exceção controlada, para
# validar o tratamento de erro, mudança de cor/estado e recuperação
# da interface. O ExecutionManager já captura essa exceção no mesmo
# try/except usado para qualquer tarefa real (ver _executar_lote).
# Usa o mesmo CMD persistente do aplicativo, através do
# TerminalManager.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


class ErroSimuladoLaboratorio(Exception):
    """Exceção controlada, usada apenas pelo Laboratório para testar o
    tratamento de erro da interface — nunca indica uma falha real."""


def teste_erro(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Levanta
    ErroSimuladoLaboratorio de propósito (~70%); o ExecutionManager já
    trata isso pelo mesmo caminho usado para uma falha real. Os
    comandos enviados ao CMD gerenciado (via terminal.executar) são
    apenas `echo` inofensivos — nenhum comando real do Windows é
    executado."""
    reporter.log("[LAB] Teste de erro iniciado\n", "titulo")
    terminal.executar("echo Teste de erro iniciado")

    passos = 20
    ponto_de_falha = 14  # ~70%
    for i in range(1, passos + 1):
        time.sleep(0.2)
        reporter.progress((i / passos) * 100)
        reporter.message(f"Etapa {i}/{passos}")
        terminal.executar(f"echo Etapa {i}/{passos}")
        if i == ponto_de_falha:
            reporter.error("[ERRO] Falha simulada — ponto de falha controlado atingido.\n")
            terminal.executar("echo ERRO: falha simulada no ponto de falha controlado")
            raise ErroSimuladoLaboratorio(
                "Erro simulado pelo Laboratório para teste de interface"
            )