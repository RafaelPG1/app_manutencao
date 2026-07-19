# ==========================================================
# Arquivo: core/recuperacao/restore_point.py
# Responsabilidade: Criação de um ponto de restauração do sistema
# (System Restore) antes de reparos potencialmente arriscados
# (DISM, SFC, CHKDSK) — categoria Recuperação.
#
# Usa exclusivamente o mecanismo oficial do Windows via PowerShell:
#   - Get-ComputerRestorePoint  -> lista os pontos existentes; também
#     serve como checagem indireta de que a Proteção do Sistema está
#     habilitada (lança erro quando não está, comportamento
#     documentado do próprio cmdlet).
#   - Checkpoint-Computer       -> cria um novo ponto de restauração.
#
# NÃO CRIAR PONTOS DUPLICADOS: em vez de o aplicativo inventar seu
# próprio limite de tempo (ex.: "só um a cada X horas"), a decisão foi
# deixar o PRÓPRIO WINDOWS decidir isso, que já limita nativamente a
# frequência de criação de pontos de restauração (o comportamento
# documentado da Microsoft desde o Windows 8 é de, no máximo, um novo
# ponto a cada 24 horas, independente da origem da chamada). Esta
# rotina apenas chama Checkpoint-Computer normalmente e COMPARA a
# quantidade de pontos antes/depois da chamada:
#   - se um novo ponto realmente apareceu -> sucesso, informa ao
#     usuário;
#   - se a quantidade não mudou -> o Windows optou por não criar um
#     novo (já existe um recente o bastante) -> informa isso ao
#     usuário como um resultado esperado, não como falha.
# Isso evita duplicar uma regra que o próprio Windows já aplica, sem
# o aplicativo precisar adivinhar ou reimplementar esse limite.
# ==========================================================

import subprocess

from utils.helpers import agora
from utils.logger import log

_TIMEOUT_SEGUNDOS = 150

_DESCRICAO_PONTO = "Manutencao do Sistema - antes de reparo"

# Script único, executado de uma só vez, para que a contagem de
# pontos "antes" e "depois" seja consistente (evita duas chamadas
# separadas ao PowerShell, cada uma com custo de inicialização
# próprio, e uma janela de tempo maior para uma condição de corrida
# com outro processo que também crie pontos de restauração).
_SCRIPT_PS = f"""
$ErrorActionPreference = 'Stop'
try {{
    $antes = @(Get-ComputerRestorePoint)
}} catch {{
    Write-Output 'PROTECAO_DESATIVADA'
    exit 0
}}
try {{
    Checkpoint-Computer -Description '{_DESCRICAO_PONTO}' -RestorePointType 'MODIFY_SETTINGS'
}} catch {{
    Write-Output ('ERRO:' + $_.Exception.Message)
    exit 0
}}
Start-Sleep -Seconds 2
try {{
    $depois = @(Get-ComputerRestorePoint)
}} catch {{
    $depois = @()
}}
if ($depois.Count -gt $antes.Count) {{
    Write-Output 'CRIADO'
}} else {{
    Write-Output 'THROTTLE'
}}
"""


def criar_ponto_restauracao(reporter):
    """reporter: TaskReporter (ver core/execution/reporter.py).

    Tarefa de progresso INDETERMINADO (uma única operação, sem
    percentual possível) — não chama reporter.progress() em nenhum
    momento, igual a dns.py/recyclebin.py."""
    reporter.log("[INFO] Criando ponto de restauração do sistema...\n", "titulo")
    reporter.message("Criando ponto de restauração... (pode levar até 2 minutos)")
    log(f"[RESTAURACAO] Iniciado em {agora()}")

    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        reporter.log(
            "[ERRO] A criação do ponto de restauração demorou demais e foi cancelada.\n", "erro"
        )
        log(f"[RESTAURACAO] ERRO - Timeout - {agora()}")
        return
    except Exception as e:
        reporter.log(f"[ERRO] Não foi possível criar o ponto de restauração: {e}\n", "erro")
        log(f"[RESTAURACAO] ERRO - {e} - {agora()}")
        return

    saida = (resultado.stdout or "").strip()
    ultima_linha = saida.splitlines()[-1].strip() if saida else ""

    if ultima_linha == "PROTECAO_DESATIVADA":
        reporter.log(
            "[AVISO] A Proteção do Sistema está desativada para esta unidade.\n"
            "[AVISO] Ative em: Painel de Controle > Sistema > Proteção do Sistema "
            "> selecione a unidade C: > Configurar > Ativar proteção do sistema.\n",
            "aviso",
        )
        log(f"[RESTAURACAO] AVISO - Protecao do Sistema desativada - {agora()}")
        return

    if ultima_linha == "CRIADO":
        reporter.log(
            "[SUCESSO] Ponto de restauração criado com sucesso.\n", "ok"
        )
        log(f"[RESTAURACAO] SUCESSO - Ponto criado - {agora()}")
        return

    if ultima_linha == "THROTTLE":
        reporter.log(
            "[INFO] Já existe um ponto de restauração recente o suficiente — "
            "o Windows limita a criação de novos pontos a um a cada 24 horas, "
            "então nenhum ponto duplicado foi criado.\n",
            "ok",
        )
        log(f"[RESTAURACAO] INFO - Ponto recente ja existia (throttle do Windows) - {agora()}")
        return

    if ultima_linha.startswith("ERRO:"):
        detalhe = ultima_linha[len("ERRO:"):].strip()
        reporter.log(f"[ERRO] Falha ao criar o ponto de restauração: {detalhe}\n", "erro")
        log(f"[RESTAURACAO] ERRO - {detalhe} - {agora()}")
        return

    # Saída inesperada (versão de PowerShell diferente, script bloqueado por
    # política de execução etc.) — não interpreta como sucesso silencioso.
    reporter.log(
        f"[AVISO] Não foi possível confirmar o resultado da criação do ponto "
        f"de restauração (retorno inesperado: {ultima_linha or resultado.stderr.strip()}).\n",
        "aviso",
    )
    log(f"[RESTAURACAO] AVISO - Retorno inesperado: {ultima_linha!r} - {agora()}")
