# ==========================================================
# Arquivo: core/limpeza/recyclebin.py
# Responsabilidade: Rotina para esvaziar a Lixeira do Windows
# via API do shell32 (SHEmptyRecycleBinW).
#
# É uma única chamada de API, não um loop — não existe percentual
# real possível. A UI mostra o indicador indeterminado a partir das
# capacidades declaradas, não por este módulo.
# ==========================================================

import ctypes

from utils.helpers import agora
from utils.logger import log


def esvaziar_lixeira(reporter):
    log(f"[LIXEIRA] Iniciado em {agora()}")
    try:
        # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        flags = 0x00000001 | 0x00000002 | 0x00000004
        ret = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        # 0 = sucesso, -2147418113 (0x8000FFFF) ocorre às vezes quando já está vazia
        if ret in (0, -2147418113):
            reporter.log("[SUCESSO] Lixeira esvaziada.\n", "ok")
            log(f"[LIXEIRA] SUCESSO - Concluído em {agora()}")
        else:
            reporter.log(f"[AVISO] Retorno inesperado: {ret}\n", "aviso")
            log(f"[LIXEIRA] AVISO - Código {ret} - {agora()}")
    except Exception as e:
        reporter.log(f"[ERRO] {e}\n", "erro")
        log(f"[LIXEIRA] ERRO - {e}")