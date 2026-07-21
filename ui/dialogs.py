# ==========================================================
# Arquivo: ui/dialogs.py
# Responsabilidade: Janelas e caixas de diálogo (mensagens de
# aviso, confirmação e informação exibidas ao usuário).
# ==========================================================

from tkinter import messagebox


def avisar_permissao_admin():
    messagebox.showwarning(
        "Permissão necessária",
        "Este programa precisa ser executado como Administrador.\n"
        "Ele será reaberto pedindo elevação de privilégios.",
    )


def perguntar_chkdsk_r() -> bool:
    return messagebox.askyesno(
        "CHKDSK - Disco HDD",
        "Disco HDD detectado.\n\n"
        "Deseja incluir varredura de setores físicos (/r) no CHKDSK?\n"
        "Atenção: com /r a verificação demora muito mais no boot.",
    )


def confirmar_reparo_inicializacao() -> bool:
    """Confirmação forte antes de reiniciar o computador para as
    Opções de Inicialização Avançadas (WinRE) — ação disruptiva, com
    reinicialização imediata assim que confirmada."""
    return messagebox.askyesno(
        "Reparo de Inicialização",
        "Isto vai REINICIAR O COMPUTADOR AGORA nas Opções de Inicialização Avançadas do Windows.\n\n"
        "Salve qualquer trabalho em aberto antes de continuar.\n\n"
        "Depois de reiniciar, selecione:\n"
        "Solucionar problemas  →  Opções avançadas  →  Reparo de Inicialização.\n\n"
        "Deseja reiniciar agora?",
        icon="warning",
    )


def confirmar_execucao(quantidade: int) -> bool:
    return messagebox.askyesno(
        "Confirmar execução",
        f"Executar {quantidade} tarefa(s) selecionada(s) agora?"
    )


def avisar_nada_selecionado():
    messagebox.showinfo("Nada selecionado", "Marque ao menos uma tarefa para executar.")


def avisar_operacao_em_andamento():
    messagebox.showinfo("Aguarde", "Uma operação já está em andamento.")


def informar_local_log(log_file: str, erro: Exception = None):
    if erro is None:
        messagebox.showinfo("Local do log", f"O log fica em:\n{log_file}")
    else:
        messagebox.showinfo(
            "Local do log",
            f"O log fica em:\n{log_file}\n\n"
            f"(Não foi possível abrir a pasta automaticamente: {erro})"
        )


def confirmar_limpar_historico_logs() -> bool:
    """Histórico e logs são gravados no mesmo arquivo (ver
    utils/logger.py) — por isso a tela de Configurações tem uma única
    ação para os dois, em vez de dois botões que fariam exatamente a
    mesma coisa com nomes diferentes."""
    return messagebox.askyesno(
        "Limpar histórico e logs",
        "Isto vai apagar TODO o histórico de execuções e os logs salvos até agora.\n\n"
        "Esta ação não pode ser desfeita. Deseja continuar?",
        icon="warning",
    )