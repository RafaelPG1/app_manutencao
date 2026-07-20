# ==========================================================
# Arquivo: core/sistema/processos.py
# Responsabilidade: Processos que mais consomem CPU e memória RAM —
# categoria Sistema, Fase 4. Somente leitura.
#
# Usa Get-Process (cmdlet oficial nativo do PowerShell) para ambas as
# listas, numa única consulta:
#   - Top CPU: ordenado pela propriedade CPU (tempo total de
#     processador consumido, em segundos, desde que o processo
#     iniciou — a métrica oficial exposta pelo próprio .NET/
#     PowerShell). É diferente do "% de CPU agora" mostrado pelo
#     Gerenciador de Tarefas (que exige amostragem de contadores de
#     desempenho ao longo de um intervalo); optou-se pela métrica de
#     Get-Process por ser oficial, de uma única chamada e muito mais
#     robusta (contadores de desempenho corrompidos são uma causa
#     conhecida de falha em ambientes Windows reais). A UI identifica
#     a coluna como "tempo de processador" para não confundir com um
#     percentual instantâneo.
#   - Top RAM: ordenado por WorkingSet64 (memória física realmente
#     em uso pelo processo) — a mesma métrica usada pelo Gerenciador
#     de Tarefas na coluna "Memória".
# ==========================================================

import json
import subprocess

_TIMEOUT_SEGUNDOS = 20
_LIMITE = 8

_SCRIPT_PS = f"""
$ErrorActionPreference = 'SilentlyContinue'
$porCpu = @(Get-Process | Sort-Object CPU -Descending | Select-Object -First {_LIMITE} Name, Id, @{{N='CpuSeg';E={{[math]::Round($_.CPU,1)}}}})
$porRam = @(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First {_LIMITE} Name, Id, @{{N='RamMB';E={{[math]::Round($_.WorkingSet64/1MB,1)}}}})
$resultado = @{{
    top_cpu = @($porCpu | ForEach-Object {{ @{{ nome = $_.Name; pid_processo = $_.Id; cpu_segundos = $_.CpuSeg }} }})
    top_ram = @($porRam | ForEach-Object {{ @{{ nome = $_.Name; pid_processo = $_.Id; ram_mb = $_.RamMB }} }})
}}
$resultado | ConvertTo-Json -Depth 3 -Compress
"""


def obter_processos_top() -> dict:
    """Retorna {"top_cpu": [...], "top_ram": [...]}, cada item com
    "nome", "pid_processo" e a métrica correspondente
    ("cpu_segundos" ou "ram_mb"). Nunca lança exceção: em caso de
    falha, devolve {"erro": ...}."""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return {"erro": f"Não foi possível consultar os processos: {e}"}

    saida = (resultado.stdout or "").strip()
    if not saida:
        return {"erro": "O PowerShell não retornou nenhuma informação de processos."}

    try:
        bruto = json.loads(saida)
    except (json.JSONDecodeError, ValueError):
        return {"erro": "Não foi possível interpretar o resultado da consulta de processos."}

    def _normaliza(lista, campo_metrica):
        if isinstance(lista, dict):
            lista = [lista]
        return [
            {
                "nome": p.get("nome") or "Processo desconhecido",
                "pid": p.get("pid_processo"),
                campo_metrica: p.get(campo_metrica) or 0,
            }
            for p in (lista or [])
        ]

    return {
        "top_cpu": _normaliza(bruto.get("top_cpu"), "cpu_segundos"),
        "top_ram": _normaliza(bruto.get("top_ram"), "ram_mb"),
    }