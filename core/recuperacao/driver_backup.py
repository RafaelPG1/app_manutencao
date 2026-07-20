# ==========================================================
# Arquivo: core/recuperacao/driver_backup.py
# Responsabilidade: Backup dos pacotes de driver instalados, usando
# o utilitário oficial do Windows `pnputil /export-driver` —
# categoria Recuperação, Fase 3.
#
# Exige uma pasta de destino escolhida pelo usuário (a UI abre um
# seletor de pasta ANTES de chamar esta função — ver
# ui/main_window.py: backup_drivers). Por depender de uma escolha do
# usuário antes de rodar, esta é uma AÇÃO INSTANTÂNEA, e não uma
# tarefa de lote (o fluxo de checkbox + "Executar selecionadas" não
# tem como pedir uma pasta no meio da execução).
# ==========================================================

import os
import subprocess

from utils.helpers import agora
from utils.logger import log


def fazer_backup_drivers(destino: str) -> dict:
    """Exporta todos os pacotes de driver de terceiros instalados
    (pnputil /export-driver * <destino>) para a pasta `destino`.
    Retorna {"sucesso": bool, "mensagem": str} — nunca lança
    exceção."""
    if not destino:
        return {"sucesso": False, "mensagem": "Nenhuma pasta de destino foi selecionada."}

    try:
        os.makedirs(destino, exist_ok=True)
    except OSError as e:
        return {"sucesso": False, "mensagem": f"Não foi possível criar/acessar a pasta de destino: {e}"}

    log(f"[BACKUP_DRIVERS] Iniciado em {agora()} - destino={destino}")
    try:
        resultado = subprocess.run(
            ["pnputil", "/export-driver", "*", destino],
            capture_output=True, text=True, errors="ignore",
            timeout=180, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except FileNotFoundError:
        log(f"[BACKUP_DRIVERS] ERRO - pnputil nao encontrado - {agora()}")
        return {"sucesso": False, "mensagem": "O utilitário pnputil não foi encontrado neste sistema."}
    except subprocess.TimeoutExpired:
        log(f"[BACKUP_DRIVERS] ERRO - timeout - {agora()}")
        return {"sucesso": False, "mensagem": "O backup dos drivers demorou demais e foi cancelado."}
    except Exception as e:
        log(f"[BACKUP_DRIVERS] ERRO - {e} - {agora()}")
        return {"sucesso": False, "mensagem": f"Falha ao fazer backup dos drivers: {e}"}

    saida = ((resultado.stdout or "") + (resultado.stderr or "")).strip()
    if resultado.returncode != 0:
        log(f"[BACKUP_DRIVERS] ERRO - codigo {resultado.returncode} - {agora()}")
        return {
            "sucesso": False,
            "mensagem": f"O pnputil retornou um erro (código {resultado.returncode})."
            + (f"\n\nDetalhe: {saida}" if saida else ""),
        }

    # Cada pacote exportado vira uma subpasta própria em `destino` —
    # conta apenas para informar quantos itens foram salvos, sem
    # interpretar o conteúdo de cada um.
    try:
        qtd = len([n for n in os.listdir(destino) if os.path.isdir(os.path.join(destino, n))])
    except OSError:
        qtd = None

    log(f"[BACKUP_DRIVERS] SUCESSO - {qtd} pacotes - {agora()}")
    detalhe = f" ({qtd} pacote(s) de driver salvos)" if qtd is not None else ""
    return {"sucesso": True, "mensagem": f"Backup de drivers concluído em:\n{destino}{detalhe}"}