# ==========================================================
# Arquivo: core/diagnostico/eventos_criticos.py
# Responsabilidade: Leitura dos últimos eventos Críticos e de Erro
# registrados no Log de Eventos do Windows (log "System"), para
# ajudar a entender travamentos, reinicializações inesperadas e
# falhas de driver/hardware recentes.
#
# AÇÃO INSTANTÂNEA, NÃO É UMA TAREFA DE LOTE — mesmo racional de
# core/diagnostico/espaco_disco.py (ver o cabeçalho daquele arquivo):
# o resultado É o valor desta funcionalidade, e o console de execução
# não exibe mais reporter.log() em tempo real, então uma consulta
# como esta precisa ser mostrada fora do fluxo de lote.
#
# Usa Get-WinEvent com -FilterHashtable, a forma oficial e mais
# eficiente (filtra no próprio provedor de eventos, sem carregar o
# log inteiro) de consultar o Visualizador de Eventos via PowerShell.
# Nível 1 = Crítico, Nível 2 = Erro (valores documentados pela
# Microsoft para o parâmetro Level do FilterHashtable).
# ==========================================================

import json
import subprocess

_TIMEOUT_SEGUNDOS = 20
_DIAS_JANELA = 7
_MAX_EVENTOS = 20

_SCRIPT_PS = r"""
$ErrorActionPreference = 'Stop'
try {
    $filtro = @{
        LogName = 'System'
        Level = 1,2
        StartTime = (Get-Date).AddDays(-__DIAS__)
    }
    $eventos = @(Get-WinEvent -FilterHashtable $filtro -MaxEvents __MAX__ -ErrorAction Stop)
    $saida = @($eventos | ForEach-Object {
        $msg = "$($_.Message)"
        if ($msg.Length -gt 220) { $msg = $msg.Substring(0, 220) + '...' }
        @{
            data = $_.TimeCreated.ToString('dd/MM/yyyy HH:mm:ss')
            nivel = $_.LevelDisplayName
            origem = $_.ProviderName
            id_evento = $_.Id
            mensagem = $msg
        }
    })
    $saida | ConvertTo-Json -Depth 3 -Compress
} catch [Exception] {
    if ($_.Exception.Message -match 'No events were found') {
        Write-Output '[]'
    } else {
        Write-Output ('ERRO:' + $_.Exception.Message)
    }
}
""".replace("__DIAS__", str(_DIAS_JANELA)).replace("__MAX__", str(_MAX_EVENTOS))


def obter_eventos_criticos() -> dict:
    """Retorna {"eventos": [...]} com os últimos eventos Críticos/Erro
    do log System nos últimos _DIAS_JANELA dias (mais recente
    primeiro, como o próprio Get-WinEvent já devolve), ou {"erro": ...}
    em caso de falha real na consulta. A ausência de eventos no
    período NÃO é tratada como erro — é um resultado válido e
    positivo (nenhum evento crítico recente)."""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return {"erro": f"Não foi possível consultar o Log de Eventos: {e}"}

    saida = (resultado.stdout or "").strip()
    if not saida:
        return {"erro": "O PowerShell não retornou nenhum dado do Log de Eventos."}

    if saida.startswith("ERRO:"):
        return {"erro": saida[len("ERRO:"):].strip()}

    try:
        bruto = json.loads(saida)
    except (json.JSONDecodeError, ValueError):
        return {"erro": "Não foi possível interpretar o resultado do Log de Eventos."}

    if bruto is None:
        bruto = []
    if isinstance(bruto, dict):  # um único evento -> PowerShell não devolve lista
        bruto = [bruto]

    eventos = [
        {
            "data": e.get("data") or "—",
            "nivel": e.get("nivel") or "—",
            "origem": e.get("origem") or "—",
            "id_evento": e.get("id_evento"),
            "mensagem": e.get("mensagem") or "(sem descrição)",
        }
        for e in bruto
    ]
    return {"eventos": eventos, "dias_janela": _DIAS_JANELA}
