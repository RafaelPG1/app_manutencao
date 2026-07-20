# ==========================================================
# Arquivo: core/sistema/hardware.py
# Responsabilidade: Uso atual de CPU, memória RAM e disco —
# categoria Sistema, Fase 4. Somente leitura.
#
# CPU: Win32_PerfFormattedData_PerfOS_Processor — classe CIM oficial
# que já entrega o percentual PRONTO (pré-calculado pelo próprio
# Windows), sem precisar de duas amostras manuais.
# RAM: Win32_OperatingSystem (TotalVisibleMemorySize/FreePhysicalMemory)
# — mesma classe oficial já usada em core/sistema/system_info.py,
# aqui só os dois campos necessários para o percentual.
# Disco: REAPROVEITA core/dashboard/system_info.obter_espaco_disco()
# — já implementado (GetLogicalDrives + shutil.disk_usage) e usado
# pelo Dashboard; não há motivo para duplicar essa lógica aqui.
# ==========================================================

import json
import subprocess

from core.dashboard.system_info import obter_espaco_disco

_TIMEOUT_SEGUNDOS = 15

_SCRIPT_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$resultado = @{}
try {
    $cpu = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'"
    if ($cpu) { $resultado.cpu_percentual = [int]$cpu.PercentProcessorTime }
} catch {}
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $total = $os.TotalVisibleMemorySize
    $livre = $os.FreePhysicalMemory
    if ($total -gt 0) {
        $resultado.ram_percentual = [math]::Round((($total - $livre) / $total) * 100, 0)
    }
} catch {}
$resultado | ConvertTo-Json -Compress
"""


def obter_uso_hardware() -> dict:
    """Retorna {"cpu_percentual": int|None, "ram_percentual": int|None,
    "discos": [...]} — "discos" é exatamente o retorno de
    obter_espaco_disco() (cada item com "unidade", "total_gb",
    "usado_gb", "pct_usado", "livre_gb", ou "erro").

    Nunca lança exceção: campos que não puderam ser lidos vêm como
    None, e o disco reaproveita o mesmo tratamento de erro já
    existente em obter_espaco_disco()."""
    cpu_percentual = None
    ram_percentual = None
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        saida = (resultado.stdout or "").strip()
        if saida:
            bruto = json.loads(saida)
            cpu_percentual = bruto.get("cpu_percentual")
            ram_percentual = bruto.get("ram_percentual")
    except Exception:
        pass  # cpu/ram ficam None; a UI mostra "indisponível" para esses campos

    try:
        discos = obter_espaco_disco()
    except Exception:
        discos = []

    return {
        "cpu_percentual": cpu_percentual,
        "ram_percentual": ram_percentual,
        "discos": discos,
    }