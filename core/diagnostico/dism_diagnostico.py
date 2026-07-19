# ==========================================================
# Arquivo: core/diagnostico/dism_diagnostico.py
# Responsabilidade: Etapas de DIAGNÓSTICO do DISM — /CheckHealth e
# /ScanHealth — que verificam a presença de corrupção no component
# store do Windows SEM reparar nada. São mais rápidas que o
# /RestoreHealth já existente em core/manutencao/dism.py e servem
# para o usuário decidir se vale a pena rodar o reparo completo.
#
# Diferença entre os três modos (documentada pela Microsoft):
#   /CheckHealth  -> só lê uma flag já registrada internamente;
#                     segundos.
#   /ScanHealth   -> varre o component store em busca de corrupção;
#                     alguns minutos.
#   /RestoreHealth (core/manutencao/dism.py, categoria Manutenção)
#                 -> varre E repara; o mais demorado dos três.
#
# Assim como /RestoreHealth, estas duas rodam no Prompt de Comando
# real e persistente do aplicativo (core/shared/terminal_manager.py),
# e por isso NÃO interpretam o código de retorno — a saída nativa do
# DISM já aparece no próprio CMD. O padrão de log/relato é o mesmo
# usado por dism.py/sfc.py, compartilhado via
# core/shared/comando_terminal.py (ver o cabeçalho de dism.py para o
# histórico dessa extração).
# ==========================================================

from core.shared.comando_terminal import executar_comando_no_terminal

_STATUS_CHECK = "Verificando sinalização de corrupção... (acompanhe no Prompt de Comando aberto)"
_STATUS_SCAN = "Varrendo a imagem do Windows em busca de corrupção... (acompanhe no Prompt de Comando aberto)"


def executar_dism_checkhealth(reporter):
    """DISM /CheckHealth — checagem rápida (poucos segundos): só lê a
    flag de corrupção já conhecida pelo Windows, sem varrer nada.
    Útil como primeira verificação, antes de decidir rodar o
    ScanHealth (mais demorado) ou o RestoreHealth (que já repara)."""
    executar_comando_no_terminal(
        reporter,
        comando="DISM /Online /Cleanup-Image /CheckHealth",
        tag_log="DISM_CHECK",
        mensagem_inicio="Iniciando checagem rápida da imagem do Windows (CheckHealth)...",
        mensagem_status=_STATUS_CHECK,
    )


def executar_dism_scanhealth(reporter):
    """DISM /ScanHealth — varredura completa em busca de corrupção,
    sem reparar nada (somente leitura). Mais demorada que
    /CheckHealth, mas bem mais rápida que /RestoreHealth, pois não
    faz o reparo em si."""
    executar_comando_no_terminal(
        reporter,
        comando="DISM /Online /Cleanup-Image /ScanHealth",
        tag_log="DISM_SCAN",
        mensagem_inicio="Iniciando varredura da imagem do Windows em busca de corrupção (ScanHealth)...",
        mensagem_status=_STATUS_SCAN,
    )
