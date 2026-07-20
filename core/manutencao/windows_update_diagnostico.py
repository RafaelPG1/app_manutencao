# ==========================================================
# Arquivo: core/manutencao/windows_update_diagnostico.py
# Responsabilidade: Diagnóstico de saúde do Windows Update —
# categoria Manutenção, Fase 5. Somente leitura, nenhuma alteração é
# feita nos serviços ou nos arquivos.
#
# AÇÃO INSTANTÂNEA, NÃO É UMA TAREFA DE LOTE — mesmo racional já
# documentado em core/diagnostico/espaco_disco.py: o resultado é o
# valor desta funcionalidade, e o console de execução não exibe mais
# reporter.log() em tempo real.
#
# Verifica:
#   - Serviços necessários ao Windows Update (Get-Service, cmdlet
#     oficial): Windows Update, BITS, Serviços de Criptografia,
#     Instalador de Módulos do Windows e Otimização de Entrega.
#     Um serviço "Parado" com início Manual é NORMAL (esses serviços
#     rodam sob demanda) — só é sinalizado como problema real um
#     serviço com início "Desabilitado", que é a causa clássica e
#     documentada de falhas no Windows Update.
#   - Estado do cache do Windows Update: tamanho da pasta
#     SoftwareDistribution\Download (mesmo caminho oficial já usado
#     por core/limpeza/update_cache.py) — um cache muito grande é um
#     indício comum de downloads presos/corrompidos.
# ==========================================================

import json
import os
import subprocess

_TIMEOUT_SEGUNDOS = 20

_SERVICOS = [
    ("wuauserv", "Windows Update"),
    ("bits", "Transferência Inteligente em Segundo Plano (BITS)"),
    ("cryptsvc", "Serviços de Criptografia"),
    ("trustedinstaller", "Instalador de Módulos do Windows"),
    ("dosvc", "Otimização de Entrega"),
]

_SCRIPT_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$nomes = @('wuauserv','bits','cryptsvc','trustedinstaller','dosvc')
$saida = @()
foreach ($nome in $nomes) {
    $s = Get-Service -Name $nome -ErrorAction SilentlyContinue
    if ($s) {
        $saida += @{ nome = $s.Name; status = "$($s.Status)"; tipo_inicializacao = "$($s.StartType)" }
    } else {
        $saida += @{ nome = $nome; status = $null; tipo_inicializacao = $null }
    }
}
$saida | ConvertTo-Json -Depth 2 -Compress
"""


def obter_diagnostico_windows_update() -> dict:
    """Retorna {"servicos": [...], "cache_mb": float|None,
    "saudavel": bool}. Nunca lança exceção: em caso de falha total na
    consulta de serviços, devolve {"erro": ...}."""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return {"erro": f"Não foi possível consultar os serviços do Windows Update: {e}"}

    saida = (resultado.stdout or "").strip()
    if not saida:
        return {"erro": "O PowerShell não retornou nenhuma informação de serviços."}

    try:
        bruto = json.loads(saida)
    except (json.JSONDecodeError, ValueError):
        return {"erro": "Não foi possível interpretar o resultado da consulta de serviços."}

    if isinstance(bruto, dict):
        bruto = [bruto]
    bruto_por_nome = {item.get("nome", "").lower(): item for item in bruto}

    servicos = []
    algum_desabilitado = False
    for nome_tecnico, rotulo in _SERVICOS:
        item = bruto_por_nome.get(nome_tecnico.lower())
        status = item.get("status") if item else None
        tipo = item.get("tipo_inicializacao") if item else None
        if tipo and tipo.lower() == "disabled":
            algum_desabilitado = True
        servicos.append({
            "nome_tecnico": nome_tecnico,
            "rotulo": rotulo,
            "status": status or "Não encontrado",
            "tipo_inicializacao": tipo or "—",
            "problema": bool(tipo and tipo.lower() == "disabled"),
        })

    cache_mb = None
    system_root = os.environ.get("SystemRoot", "")
    if system_root:
        pasta = os.path.join(system_root, "SoftwareDistribution", "Download")
        if os.path.isdir(pasta):
            try:
                total = 0
                for raiz, _sub, arquivos in os.walk(pasta, onerror=lambda _e: None):
                    for nome in arquivos:
                        try:
                            total += os.path.getsize(os.path.join(raiz, nome))
                        except OSError:
                            continue
                cache_mb = total / (1024 ** 2)
            except OSError:
                cache_mb = None

    return {
        "servicos": servicos,
        "cache_mb": cache_mb,
        "saudavel": not algum_desabilitado,
    }