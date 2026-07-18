# ==========================================================
# Arquivo: core/laboratorio/aviso.py
# Responsabilidade: Teste de AVISO do Laboratório — executa
# normalmente e emite alguns avisos ao longo do caminho, finalizando
# com sucesso. Serve para validar a exibição de avisos sem interromper
# a execução. Usa o mesmo CMD persistente do aplicativo, através do
# TerminalManager.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


def teste_aviso(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Os comandos enviados ao
    CMD gerenciado (via terminal.executar) são apenas `echo`
    inofensivos — nenhum comando real do Windows é executado."""
    reporter.log("[LAB] Teste de aviso iniciado\n", "titulo")
    terminal.executar("echo Teste de aviso iniciado")

    passos = 15
    avisos_nas_etapas = {5, 10}
    for i in range(1, passos + 1):
        time.sleep(0.3)
        reporter.progress((i / passos) * 100)
        reporter.message(f"Etapa {i}/{passos}")
        if i in avisos_nas_etapas:
            reporter.warning(f"[AVISO] Alguns arquivos foram ignorados na etapa {i}.\n")
            terminal.executar(f"echo AVISO: alguns arquivos foram ignorados na etapa {i}")

    terminal.executar("echo Teste de aviso concluido")
    reporter.log("[SUCESSO] Teste de aviso concluído (com avisos acima).\n", "ok")