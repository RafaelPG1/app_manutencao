# ==========================================================
# Arquivo: core/sistema/system_info.py
# Responsabilidade: Coleta de informações do computador (CPU, RAM,
# versão/edição do Windows, fabricante, modelo, BIOS, placa-mãe,
# tempo ligado, discos instalados e GPU) para a categoria Sistema.
#
# NÃO CONFUNDIR com core/dashboard/system_info.py: aquele módulo é
# específico do card "Espaço livre" do Dashboard (só espaço em disco)
# e não foi alterado. Este é um módulo novo, próprio da categoria
# Sistema, com um escopo bem mais amplo.
#
# Usa exclusivamente CIM (Get-CimInstance), a interface oficial e
# recomendada pela Microsoft para consultar WMI a partir do
# PowerShell (substituta do antigo Get-WmiObject) — mesma família de
# API já usada em core/shared/disk_info.py (Get-PhysicalDisk também é
# um cmdlet CIM). Uma única chamada ao PowerShell reúne todas as
# classes necessárias e devolve tudo em JSON, evitando abrir vários
# processos powershell.exe (cada um com custo de inicialização
# relevante) para montar uma única tela.
# ==========================================================

import json
import subprocess

_TIMEOUT_SEGUNDOS = 20

# Script único: reúne CPU, memória, sistema operacional, computador,
# BIOS, placa-mãe, discos (via Get-PhysicalDisk, igual a
# disk_info.py) e GPU, e devolve tudo como um único objeto JSON.
# Cada bloco tem seu próprio try/catch: a falha ao ler UMA classe
# (ex.: GPU indisponível numa VM) nunca derruba a coleta das demais.
_SCRIPT_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$resultado = @{}

try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $resultado.cpu_nome = $cpu.Name
    $resultado.cpu_nucleos = $cpu.NumberOfCores
    $resultado.cpu_threads = $cpu.NumberOfLogicalProcessors
} catch {}

try {
    $os = Get-CimInstance Win32_OperatingSystem
    $resultado.so_nome = $os.Caption
    $resultado.so_versao = $os.Version
    $resultado.so_build = $os.BuildNumber
    $resultado.so_arquitetura = $os.OSArchitecture
    $resultado.ram_total_gb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    $resultado.ram_livre_gb = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
    $boot = $os.LastBootUpTime
    if ($boot) {
        $decorrido = (Get-Date) - $boot
        $resultado.uptime_dias = [int]$decorrido.Days
        $resultado.uptime_horas = [int]$decorrido.Hours
        $resultado.uptime_minutos = [int]$decorrido.Minutes
    }
} catch {}

try {
    $cs = Get-CimInstance Win32_ComputerSystem
    $resultado.fabricante = $cs.Manufacturer
    $resultado.modelo = $cs.Model
} catch {}

try {
    $bios = Get-CimInstance Win32_BIOS
    $resultado.bios_versao = ($bios.SMBIOSBIOSVersion)
    if ($bios.ReleaseDate) {
        $resultado.bios_data = $bios.ReleaseDate.ToString('yyyy-MM-dd')
    }
} catch {}

try {
    $placa = Get-CimInstance Win32_BaseBoard
    $resultado.placa_mae_fabricante = $placa.Manufacturer
    $resultado.placa_mae_modelo = $placa.Product
} catch {}

try {
    $discos = @(Get-PhysicalDisk | Select-Object FriendlyName, @{N='TamanhoGB';E={[math]::Round($_.Size/1GB,1)}}, MediaType)
    $resultado.discos = @($discos | ForEach-Object {
        @{ modelo = $_.FriendlyName; tamanho_gb = $_.TamanhoGB; tipo = "$($_.MediaType)" }
    })
} catch {
    $resultado.discos = @()
}

try {
    $gpus = @(Get-CimInstance Win32_VideoController | Where-Object { $_.Name } | Select-Object -ExpandProperty Name)
    $resultado.gpu = @($gpus)
} catch {
    $resultado.gpu = @()
}

$resultado | ConvertTo-Json -Depth 4 -Compress
"""


def _formatar_uptime(info: dict) -> str:
    dias = info.get("uptime_dias")
    horas = info.get("uptime_horas")
    minutos = info.get("uptime_minutos")
    if dias is None:
        return "Indisponível"
    partes = []
    if dias:
        partes.append(f"{dias} dia{'s' if dias != 1 else ''}")
    if horas:
        partes.append(f"{horas} hora{'s' if horas != 1 else ''}")
    if not dias and minutos is not None:
        partes.append(f"{minutos} minuto{'s' if minutos != 1 else ''}")
    return ", ".join(partes) if partes else "Menos de 1 minuto"


def obter_informacoes_sistema() -> dict:
    """Consulta CPU, memória, SO, fabricante/modelo, BIOS, placa-mãe,
    uptime, discos e GPU via CIM, e devolve tudo já formatado para
    exibição (nenhum campo bruto do WMI é repassado à UI sem
    tratamento).

    Nunca lança exceção: em caso de falha total na consulta, devolve
    um dicionário com "erro" preenchido — a tela de Sistema decide
    sozinha como exibir esse caso, sem precisar de try/except."""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return {"erro": f"Não foi possível consultar as informações do sistema: {e}"}

    saida = (resultado.stdout or "").strip()
    if not saida:
        return {"erro": "O PowerShell não retornou nenhuma informação."}

    try:
        bruto = json.loads(saida)
    except (json.JSONDecodeError, ValueError):
        return {"erro": "Não foi possível interpretar o resultado da consulta ao sistema."}

    discos = bruto.get("discos") or []
    if isinstance(discos, dict):  # PowerShell devolve objeto único (não lista) quando há só 1 disco
        discos = [discos]
    gpus = bruto.get("gpu") or []
    if isinstance(gpus, str):  # idem, quando há só 1 GPU
        gpus = [gpus]

    return {
        "cpu": bruto.get("cpu_nome") or "Indisponível",
        "cpu_nucleos": bruto.get("cpu_nucleos"),
        "cpu_threads": bruto.get("cpu_threads"),
        "ram_total_gb": bruto.get("ram_total_gb"),
        "ram_livre_gb": bruto.get("ram_livre_gb"),
        "sistema_operacional": bruto.get("so_nome") or "Indisponível",
        "versao": bruto.get("so_versao") or "—",
        "build": bruto.get("so_build") or "—",
        "arquitetura": bruto.get("so_arquitetura") or "—",
        "fabricante": bruto.get("fabricante") or "Indisponível",
        "modelo": bruto.get("modelo") or "—",
        "bios_versao": bruto.get("bios_versao") or "—",
        "bios_data": bruto.get("bios_data") or "—",
        "placa_mae_fabricante": bruto.get("placa_mae_fabricante") or "—",
        "placa_mae_modelo": bruto.get("placa_mae_modelo") or "—",
        "uptime": _formatar_uptime(bruto),
        "discos": [
            {
                "modelo": d.get("modelo") or "Disco desconhecido",
                "tamanho_gb": d.get("tamanho_gb"),
                "tipo": d.get("tipo") or "Indefinido",
            }
            for d in discos
        ],
        "gpu": gpus or ["Indisponível"],
    }
