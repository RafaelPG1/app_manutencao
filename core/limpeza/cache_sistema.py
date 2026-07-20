# ==========================================================
# Arquivo: core/limpeza/cache_sistema.py
# Responsabilidade: Limpeza de caches adicionais do sistema —
# categoria Limpeza, Fase 6. Cobre categorias oficiais da Limpeza de
# Disco que ainda não têm uma tarefa própria no aplicativo (cache de
# miniaturas, temporários, lixeira e cache do Windows Update já são
# cobertos por tarefas dedicadas desde as fases anteriores):
#   - Temporary Internet Files (cache do Internet Explorer/Edge legado)
#   - DirectX Shader Cache
#
# Reaproveita core/shared/disk_cleanup_oficial.py (mesmo mecanismo
# usado por windows_old.py e logs_antigos.py).
# ==========================================================

from core.shared.disk_cleanup_oficial import executar_limpeza_disco_oficial

_CATEGORIAS = [
    "Temporary Internet Files",
    "DirectX Shader Cache",
]


def limpar_cache_adicional_sistema(reporter):
    executar_limpeza_disco_oficial(
        reporter, _CATEGORIAS, "CACHE_SISTEMA", "limpeza de cache adicional do sistema"
    )
