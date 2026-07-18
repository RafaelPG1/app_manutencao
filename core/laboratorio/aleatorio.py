# ==========================================================
# Arquivo: core/laboratorio/aleatorio.py
# Responsabilidade: Teste ALEATÓRIO do Laboratório — mistura
# progresso variável, logs, avisos e pequenas pausas, para validar a
# estabilidade da interface sob um padrão imprevisível. Usa o mesmo
# CMD persistente do aplicativo, através do TerminalManager.
# ==========================================================

import random
import time

from core.shared.terminal_manager import terminal


def teste_aleatorio(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Os comandos enviados ao
    CMD gerenciado (via terminal.executar) são apenas `echo`
    inofensivos — nenhum comando real do Windows é executado.

    Os eventos sorteados de log/aviso também são ecoados no CMD real,
    mantendo o caráter imprevisível do teste; eventos de pausa e de
    progresso continuam afetando só o painel interno."""
    reporter.log("[LAB] Teste aleatório iniciado\n", "titulo")
    terminal.executar("echo Teste aleatorio iniciado")

    progresso = 0
    eventos_possiveis = ["log", "aviso", "pausa", "progresso"]
    while progresso < 100:
        evento = random.choice(eventos_possiveis)
        if evento == "log":
            reporter.log(f"[INFO] Evento aleatório de log em {progresso}%\n")
            terminal.executar(f"echo Evento aleatorio de log em {progresso}%")
        elif evento == "aviso":
            reporter.warning(f"[AVISO] Evento aleatório de aviso em {progresso}%\n")
            terminal.executar(f"echo AVISO: evento aleatorio de aviso em {progresso}%")
        elif evento == "pausa":
            time.sleep(random.uniform(0.3, 1.0))
        else:
            incremento = random.randint(3, 12)
            progresso = min(progresso + incremento, 100)
            reporter.progress(progresso)
            reporter.message(f"Progresso variável: {progresso}%")
        time.sleep(0.15)

    terminal.executar("echo Teste aleatorio concluido")
    reporter.progress(100)
    reporter.log("[SUCESSO] Teste aleatório concluído.\n", "ok")