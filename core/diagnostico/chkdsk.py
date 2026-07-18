# ==========================================================
# Arquivo: core/diagnostico/chkdsk.py
# Responsabilidade: Agendamento da verificação de disco (CHKDSK)
# para a próxima reinicialização, ajustando os parâmetros
# conforme o tipo de disco (SSD/HDD).
#
# Esta tarefa NUNCA fornece percentual real: ela apenas agenda a
# verificação (fsutil dirty set + chkdsk /f [/r] /x), a varredura em
# si só roda no próximo boot, fora do controle deste processo. Por
# isso não chama reporter.progress() em nenhum momento — a UI já sabe
# disso através das capacidades declaradas (progresso_real=False) e
# mostra o indicador indeterminado sozinha.
# ==========================================================

from utils.helpers import agora, executar_comando
from utils.logger import log


def agendar_chkdsk(reporter, disco_tipo: str, usar_r: bool):
    reporter.log(f"Disco detectado: {disco_tipo}\n", "fraco")
    log(f"[CHKDSK] Iniciado em {agora()} - Disco: {disco_tipo}")

    executar_comando(["fsutil", "dirty", "set", "C:"])

    if disco_tipo.upper() == "SSD":
        reporter.log(
            "[INFO] SSD detectado - usando apenas /f (sem varredura de setores)\n"
        )
        log("[CHKDSK] SSD - Agendando com /f apenas")
        executar_comando(["chkdsk", "C:", "/f", "/x"])
    else:
        if usar_r:
            log("[CHKDSK] HDD - Agendando com /f /r")
            executar_comando(["chkdsk", "C:", "/f", "/r", "/x"])
        else:
            log("[CHKDSK] HDD - Agendando com /f apenas")
            executar_comando(["chkdsk", "C:", "/f", "/x"])

    rc, _, _ = executar_comando(["fsutil", "dirty", "query", "C:"])
    if rc == 0:
        reporter.log(
            "[SUCESSO] CHKDSK agendado com sucesso.\n"
            "[AVISO] Reinicie o computador para executar a verificação.\n", "ok"
        )
        log(f"[CHKDSK] SUCESSO - Agendamento confirmado - {agora()}")
    else:
        reporter.log(
            "[AVISO] Não foi possível confirmar o agendamento.\n", "aviso"
        )
        log(f"[CHKDSK] AVISO - Agendamento não confirmado - {agora()}")