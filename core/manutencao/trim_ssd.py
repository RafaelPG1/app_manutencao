# ==========================================================
# Arquivo: core/manutencao/trim_ssd.py
# Responsabilidade: Otimização TRIM de unidades SSD — categoria
# Manutenção, Fase 5. Usa Optimize-Volume (cmdlet oficial do módulo
# Storage do PowerShell) com o parâmetro -ReTrim, que envia o comando
# TRIM à unidade sem executar desfragmentação alguma (a
# desfragmentação tradicional não se aplica a SSDs e não é usada
# aqui).
#
# DETECÇÃO DE COMPATIBILIDADE: reaproveita
# core/shared/disk_info.detectar_tipo_disco() — a MESMA função já
# usada por core/diagnostico/chkdsk.py para decidir os parâmetros do
# CHKDSK. Segue exatamente o mesmo padrão: quem chama (ui/main_window.py)
# detecta o tipo de disco uma única vez e passa o resultado como
# parâmetro (`disco_tipo`) — esta função não detecta nada sozinha.
#
# Se o disco não for SSD, a tarefa não executa nada (evita rodar TRIM
# em HDD, onde não se aplica) e informa isso claramente ao usuário,
# sem gerar erro.
# ==========================================================

from utils.helpers import agora, executar_comando
from utils.logger import log


def otimizar_ssd(reporter, disco_tipo: str):
    log(f"[TRIM_SSD] Iniciado em {agora()} - Disco: {disco_tipo}")

    if disco_tipo.upper() != "SSD":
        reporter.log(
            f"[INFO] Disco detectado como {disco_tipo} — a otimização TRIM só se aplica a "
            "unidades SSD. Nenhuma ação foi executada.\n",
            "titulo",
        )
        log(f"[TRIM_SSD] IGNORADO - disco nao e SSD ({disco_tipo}) - {agora()}")
        return

    reporter.log("[INFO] SSD detectado — executando otimização TRIM na unidade C:...\n", "titulo")
    reporter.message("Otimizando SSD (TRIM)... isso pode levar alguns minutos.")

    rc, out, err = executar_comando([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        "Optimize-Volume -DriveLetter C -ReTrim -Verbose",
    ])
    log(out)

    if rc == 0:
        reporter.log("[SUCESSO] Otimização TRIM concluída com sucesso.\n", "ok")
        log(f"[TRIM_SSD] SUCESSO - {agora()}")
    else:
        detalhe = (err or "").strip()
        reporter.log(
            f"[ERRO] Falha ao otimizar o SSD (código {rc})."
            + (f" Detalhe: {detalhe}\n" if detalhe else "\n"),
            "erro",
        )
        log(f"[TRIM_SSD] ERRO - codigo {rc} - {detalhe} - {agora()}")