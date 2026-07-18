# ==========================================================
# Arquivo: core/laboratorio/longo.py
# Responsabilidade: Teste LONGO do Laboratório — simula uma tarefa de
# ~2 minutos com progresso contínuo, ideal para testar troca de abas,
# minimizar/voltar, painel de execução e estabilidade geral. Usa o
# mesmo CMD persistente do aplicativo, através do TerminalManager.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


def teste_longo(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Os comandos enviados ao
    CMD gerenciado (via terminal.executar) são apenas `echo`
    inofensivos — nenhum comando real do Windows é executado.

    Os `echo` reais no CMD são enviados apenas nos mesmos checkpoints
    já usados para o log interno (a cada 20s), e não a cada segundo,
    para não alongar demais o teste com o tempo real de ida e volta
    ao terminal."""
    reporter.log("[LAB] Teste longo iniciado (~2min)\n", "titulo")
    terminal.executar("echo Teste longo iniciado")

    duracao_total = 120
    for i in range(1, duracao_total + 1):
        time.sleep(1)
        reporter.progress((i / duracao_total) * 100)
        reporter.message(f"Tempo decorrido: {i}s / {duracao_total}s")
        if i % 20 == 0:
            reporter.log(f"[INFO] {i}s decorridos — ainda em execução\n")
            terminal.executar(f"echo {i}s decorridos - ainda em execucao")

    terminal.executar("echo Teste longo concluido")
    reporter.log("[SUCESSO] Teste longo concluído.\n", "ok")