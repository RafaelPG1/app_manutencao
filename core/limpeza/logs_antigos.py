# ==========================================================
# Arquivo: core/limpeza/logs_antigos.py
# Responsabilidade: Limpeza de logs antigos do Windows — categoria
# Limpeza, Fase 6.
#
# IMPORTANTE — por que NÃO usa wevtutil: o Visualizador de Eventos
# (Log de Eventos do Windows) é a MESMA fonte de dados usada pela
# funcionalidade "Eventos críticos recentes" (ver
# core/diagnostico/eventos_criticos.py). Apagar esses logs ao vivo
# via `wevtutil cl` destruiria justamente o histórico que o próprio
# aplicativo usa para diagnóstico, então essa via foi descartada.
#
# Em vez disso, esta tarefa usa as categorias OFICIAIS de "arquivos
# de log" já previstas pela própria Limpeza de Disco do Windows —
# arquivos de log de instalação/configuração e de relatório de erros,
# não o Log de Eventos ativo:
#   - Setup Log Files
#   - System error memory dump files
#   - System error minidump files
#   - Windows Error Reporting Files
#
# Reaproveita core/shared/disk_cleanup_oficial.py (mesmo mecanismo
# usado por windows_old.py e cache_sistema.py).
# ==========================================================

from core.shared.disk_cleanup_oficial import executar_limpeza_disco_oficial

_CATEGORIAS = [
    "Setup Log Files",
    "System error memory dump files",
    "System error minidump files",
    "Windows Error Reporting Files",
]


def limpar_logs_antigos(reporter):
    executar_limpeza_disco_oficial(
        reporter, _CATEGORIAS, "LOGS_ANTIGOS", "limpeza de logs antigos do Windows"
    )
