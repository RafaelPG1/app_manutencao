# ==========================================================
# Arquivo: core/diagnostico/smart_disco.py
# Responsabilidade: Diagnóstico de saúde (SMART) dos discos
# instalados — status, temperatura, vida útil estimada (SSD), horas
# de uso, modelo, número de série e tipo (SSD/HDD).
#
# AÇÃO INSTANTÂNEA, NÃO É UMA TAREFA DE LOTE: esta consulta é
# somente leitura e dura poucos segundos — não passa pelo
# ExecutionManager/TaskReporter (ver o comentário no topo de
# core/diagnostico/espaco_disco.py para o racional completo dessa
# escolha, que vale igualmente aqui). É chamada diretamente pela UI
# (ui/main_window.py), do mesmo jeito que
# core/dashboard/system_info.obter_espaco_disco() já é chamada pelo
# botão "Ver espaço em disco".
#
# Usa Get-PhysicalDisk (mesmo cmdlet oficial do módulo Storage já
# usado em core/shared/disk_info.py) combinado com
# Get-StorageReliabilityCounter, que expõe os contadores SMART
# tratados pelo próprio Windows (temperatura, horas ligado, taxa de
# desgaste em SSDs, contagem de erros) — API documentada pela
# Microsoft, sem necessidade de ler registradores SMART brutos.
# ==========================================================

import json
import subprocess

_TIMEOUT_SEGUNDOS = 25

_SCRIPT_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$saida = @()
$discos = @(Get-PhysicalDisk)
foreach ($disco in $discos) {
    $item = @{
        modelo = $disco.FriendlyName
        serial = $disco.SerialNumber
        tipo = "$($disco.MediaType)"
        status_smart = "$($disco.HealthStatus)"
        status_operacional = "$($disco.OperationalStatus)"
        tamanho_gb = [math]::Round($disco.Size / 1GB, 1)
    }
    try {
        $conf = Get-StorageReliabilityCounter -PhysicalDisk $disco -ErrorAction Stop
        if ($null -ne $conf.Temperature) { $item.temperatura_c = $conf.Temperature }
        if ($null -ne $conf.PowerOnHours) { $item.horas_uso = $conf.PowerOnHours }
        if ($null -ne $conf.Wear) { $item.desgaste_pct = $conf.Wear }
        if ($null -ne $conf.ReadErrorsTotal) { $item.erros_leitura = $conf.ReadErrorsTotal }
        if ($null -ne $conf.WriteErrorsTotal) { $item.erros_escrita = $conf.WriteErrorsTotal }
    } catch {}
    $saida += , $item
}
$saida | ConvertTo-Json -Depth 3 -Compress
"""


def obter_saude_discos() -> list:
    """Retorna uma lista de dicionários, um por disco físico
    instalado, com os campos disponíveis (nem todo disco/controlador
    expõe todos os contadores — campos ausentes simplesmente não
    aparecem no dicionário, nunca são inventados).

    Em caso de falha total na consulta, retorna uma lista com um
    único item contendo "erro" — a UI decide sozinha como exibir
    isso, sem precisar de try/except."""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return [{"erro": f"Não foi possível consultar a saúde dos discos: {e}"}]

    saida = (resultado.stdout or "").strip()
    if not saida:
        return [{"erro": "Nenhum disco físico foi encontrado ou o PowerShell não retornou dados."}]

    try:
        bruto = json.loads(saida)
    except (json.JSONDecodeError, ValueError):
        return [{"erro": "Não foi possível interpretar o resultado da consulta SMART."}]

    if isinstance(bruto, dict):  # um único disco -> PowerShell não devolve lista
        bruto = [bruto]

    itens = []
    for d in bruto:
        itens.append({
            "modelo": d.get("modelo") or "Disco desconhecido",
            "serial": d.get("serial") or "Não disponível",
            "tipo": d.get("tipo") or "Indefinido",
            "status_smart": d.get("status_smart") or "Desconhecido",
            "status_operacional": d.get("status_operacional"),
            "tamanho_gb": d.get("tamanho_gb"),
            "temperatura_c": d.get("temperatura_c"),
            "horas_uso": d.get("horas_uso"),
            "desgaste_pct": d.get("desgaste_pct"),
            "erros_leitura": d.get("erros_leitura"),
            "erros_escrita": d.get("erros_escrita"),
        })
    return itens
