# ==========================================================
# Arquivo: core/limpeza/delivery_optimization.py
# Responsabilidade: Limpeza do cache de Otimização de Entrega
# (Delivery Optimization) — categoria Limpeza, Fase 6.
#
# Usa Delete-DeliveryOptimizationCache -Force, cmdlet OFICIAL
# dedicado do módulo DeliveryOptimization (nativo do Windows 10/11) —
# diferente de Windows.old/logs antigos/cache do sistema, que passam
# pelo mecanismo de Limpeza de Disco (core/shared/disk_cleanup_oficial.py),
# a Otimização de Entrega tem seu próprio cmdlet oficial dedicado, que
# é o caminho documentado pela Microsoft para essa finalidade
# específica — por isso não reaproveita aquele helper.
# ==========================================================

from utils.helpers import agora, executar_comando
from utils.logger import log


def limpar_delivery_optimization(reporter):
    log(f"[DELIVERY_OPT] Iniciado em {agora()}")
    reporter.log("[INFO] Limpando cache de Otimização de Entrega...\n", "titulo")
    reporter.message("Limpando cache de Otimização de Entrega...")

    rc, out, err = executar_comando([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        "Delete-DeliveryOptimizationCache -Force",
    ])
    log(out)

    if rc == 0:
        reporter.log("[SUCESSO] Cache de Otimização de Entrega limpo.\n", "ok")
        log(f"[DELIVERY_OPT] SUCESSO - {agora()}")
    else:
        detalhe = (err or "").strip()
        reporter.log(
            "[AVISO] Não foi possível limpar o cache de Otimização de Entrega "
            "(pode já estar vazio ou o recurso estar indisponível nesta versão do Windows).\n",
            "aviso",
        )
        log(f"[DELIVERY_OPT] AVISO - codigo {rc} - {detalhe} - {agora()}")
