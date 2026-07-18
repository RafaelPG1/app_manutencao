# ==========================================================
# Arquivo: core/limpeza/update_cache.py
# Responsabilidade: Limpeza do cache do Windows Update
# (SoftwareDistribution\Download), parando e reiniciando os
# serviços necessários.
#
# As etapas de parar/reiniciar os serviços (net stop/start) não têm
# percentual possível e por isso não chamam reporter.progress() —
# isso é honesto: a barra simplesmente permanece no último valor
# real (0, no início) até a remoção de arquivos começar, que sim é
# controlada pelo próprio app e reporta progresso real item a item.
# ==========================================================

import os

from utils.helpers import agora, executar_comando
from utils.logger import log
from core.limpeza.cleanup import limpar_pasta


def limpar_cache_windows_update(reporter):
    log(f"[WINUPDATE] Iniciado em {agora()}")
    reporter.log("Parando serviço Windows Update...\n", "fraco")
    executar_comando(["net", "stop", "wuauserv"])
    executar_comando(["net", "stop", "bits"])

    system_root = os.environ.get("SystemRoot", "")
    pasta = os.path.join(system_root, "SoftwareDistribution", "Download") if system_root else ""
    removidos, ignorados = (0, 0)
    try:
        if pasta and os.path.isdir(pasta):
            def _ao_progredir(i, total):
                reporter.progress((i / total) * 100 if total else 100)
                reporter.message(f"{i}/{total} itens")

            removidos, ignorados = limpar_pasta(pasta, ao_progredir=_ao_progredir)
    finally:
        # Garantido mesmo se a remoção acima falhar (ex.: erro ao
        # listar a pasta) — sem isso, uma falha nessa etapa deixava o
        # Windows Update parado permanentemente, exigindo reinício
        # manual dos serviços ou reinicialização do computador.
        reporter.log("Reiniciando serviço Windows Update...\n", "fraco")
        executar_comando(["net", "start", "bits"])
        executar_comando(["net", "start", "wuauserv"])

    reporter.progress(100)
    reporter.log(
        f"[SUCESSO] Cache do Windows Update limpo "
        f"({removidos} removidos, {ignorados} ignorados).\n", "ok"
    )
    log(f"[WINUPDATE] SUCESSO - {removidos} removidos, {ignorados} ignorados - {agora()}")