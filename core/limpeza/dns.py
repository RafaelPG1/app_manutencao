# ==========================================================
# Arquivo: core/limpeza/dns.py
# Responsabilidade: Rotina de limpeza do cache de DNS
# (ipconfig /flushdns).
#
# Chamada única e instantânea — não existe percentual possível aqui.
# A UI mostra o indicador indeterminado, decidido a partir das
# capacidades declaradas (progresso_real=False), não por este módulo.
# ==========================================================

from utils.helpers import agora, executar_comando
from utils.logger import log


def limpar_dns(reporter):
    log(f"[DNS] Iniciado em {agora()}")
    rc, out, err = executar_comando(["ipconfig", "/flushdns"])
    log(out)
    if rc == 0:
        reporter.log("[SUCESSO] Cache de DNS limpo com sucesso.\n", "ok")
        log(f"[DNS] SUCESSO - Concluído em {agora()}")
    else:
        reporter.log(f"[ERRO] Falha ao limpar DNS. Código: {rc}\n", "erro")
        log(f"[DNS] ERRO - Código {rc} - {agora()}")