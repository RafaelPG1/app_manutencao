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
