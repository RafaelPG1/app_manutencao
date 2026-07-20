# ==========================================================
# Arquivo: core/sistema/rede.py
# Responsabilidade: Informações de rede — IP, gateway, DNS e lista de
# adaptadores — categoria Sistema, Fase 4. Somente leitura: nenhuma
# configuração de rede é alterada.
#
# Usa exclusivamente os cmdlets oficiais dos módulos NetTCPIP e
# NetAdapter (nativos do Windows 10/11, sucessores modernos do
# ipconfig/netsh para leitura programática):
#   - Get-NetIPConfiguration  -> IP, gateway e DNS já correlacionados
#     por adaptador, numa única chamada.
#   - Get-NetAdapter          -> lista de adaptadores com status,
#     endereço MAC e velocidade do link.
# ==========================================================

import json
import subprocess

_TIMEOUT_SEGUNDOS = 20

_SCRIPT_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$resultado = @{}

try {
    $configs = @(Get-NetIPConfiguration | Where-Object { $_.NetAdapter.Status -eq 'Up' -and $_.IPv4Address })
    if ($configs.Count -gt 0) {
        $c = $configs[0]
        $dns = @($c.DNSServer | Where-Object { $_.AddressFamily -eq 2 } | Select-Object -ExpandProperty ServerAddresses)
        $resultado.principal = @{
            adaptador = $c.InterfaceAlias
            ip = ($c.IPv4Address | Select-Object -First 1 -ExpandProperty IPAddress)
            gateway = if ($c.IPv4DefaultGateway) { $c.IPv4DefaultGateway.NextHop } else { $null }
            dns = @($dns)
        }
    }
} catch {}

try {
    $adaptadores = @(Get-NetAdapter | Select-Object Name, Status, MacAddress, LinkSpeed)
    $resultado.adaptadores = @($adaptadores | ForEach-Object {
        @{ nome = $_.Name; status = "$($_.Status)"; mac = "$($_.MacAddress)"; velocidade = "$($_.LinkSpeed)" }
    })
} catch {
    $resultado.adaptadores = @()
}

$resultado | ConvertTo-Json -Depth 4 -Compress
"""


def obter_informacoes_rede() -> dict:
    """Consulta IP/gateway/DNS do adaptador ativo principal e a lista
    de todos os adaptadores de rede. Nunca lança exceção: em caso de
    falha total, devolve {"erro": ...}; a ausência de conexão ativa
    (sem "principal") é um resultado válido, não um erro — a UI trata
    isso como "nenhuma conexão de rede ativa"."""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return {"erro": f"Não foi possível consultar as informações de rede: {e}"}

    saida = (resultado.stdout or "").strip()
    if not saida:
        return {"erro": "O PowerShell não retornou nenhuma informação de rede."}

    try:
        bruto = json.loads(saida)
    except (json.JSONDecodeError, ValueError):
        return {"erro": "Não foi possível interpretar o resultado da consulta de rede."}

    principal = bruto.get("principal")
    if principal:
        dns = principal.get("dns") or []
        if isinstance(dns, str):
            dns = [dns]
        principal = {
            "adaptador": principal.get("adaptador") or "—",
            "ip": principal.get("ip") or "—",
            "gateway": principal.get("gateway") or "Não disponível",
            "dns": dns,
        }

    adaptadores = bruto.get("adaptadores") or []
    if isinstance(adaptadores, dict):
        adaptadores = [adaptadores]

    return {
        "principal": principal,
        "adaptadores": [
            {
                "nome": a.get("nome") or "Adaptador desconhecido",
                "status": a.get("status") or "—",
                "mac": a.get("mac") or "—",
                "velocidade": a.get("velocidade") or "—",
            }
            for a in adaptadores
        ],
    }