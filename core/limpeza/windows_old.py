# ==========================================================
# Arquivo: core/limpeza/windows_old.py
# Responsabilidade: Remoção da pasta Windows.old (arquivos da versão
# anterior do Windows, deixados após uma atualização de versão) —
# categoria Limpeza, Fase 6.
#
# Usa a MESMA rotina oficial de core/shared/disk_cleanup_oficial.py
# (categoria "Previous Installations" da Limpeza de Disco), em vez de
# apagar os arquivos diretamente — Windows.old tem permissões
# restritas (pertence ao TrustedInstaller) e apagar via os.remove/
# shutil.rmtree exigiria tomar posse dos arquivos manualmente, o que
# NÃO é um mecanismo oficial. A Limpeza de Disco já sabe remover essa
# pasta com segurança.
#
# Se a pasta não existir, informa isso e não tenta nada — evita
# marcar uma categoria de limpeza sem necessidade.
# ==========================================================

import os

from core.shared.disk_cleanup_oficial import executar_limpeza_disco_oficial


def limpar_windows_old(reporter):
    if not os.path.isdir(r"C:\Windows.old"):
        reporter.log(
            "[INFO] Nenhuma pasta Windows.old foi encontrada neste computador — nada a limpar.\n",
            "titulo",
        )
        return
    executar_limpeza_disco_oficial(
        reporter, ["Previous Installations"], "WINDOWS_OLD", "limpeza da pasta Windows.old"
    )
