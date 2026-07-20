# ==========================================================
# Arquivo: core/sistema/seguranca.py
# Responsabilidade: Status de segurança do sistema — Windows
# Defender, BitLocker, TPM e Secure Boot — categoria Sistema, Fase 4.
# Somente leitura: nenhuma configuração de segurança é alterada.
#
# Usa exclusivamente cmdlets oficiais nativos do Windows/PowerShell:
#   - Get-MpComputerStatus   (módulo Defender, nativo do Windows 10/11)
#   - Get-BitLockerVolume    (módulo BitLocker — só existe em
#     edições Pro/Enterprise/Education; ausente no Windows Home, o
#     que é tratado como "indisponível", não como erro)
#   - Get-Tpm                (módulo TrustedPlatformModule, nativo)
#   - Confirm-SecureBootUEFI (cmdlet nativo; lança exceção em
#     computadores com BIOS legado em vez de UEFI — tratado como
#     "indisponível", não como erro)
#
# Cada verificação tem seu próprio try/catch no script PowerShell:
# a ausência de UM recurso (ex.: sem BitLocker por ser Windows Home)
# nunca impede a leitura dos demais.
# ==========================================================

import json
import subprocess

_TIMEOUT_SEGUNDOS = 25

_SCRIPT_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$resultado = @{}

try {
    $defender = Get-MpComputerStatus -ErrorAction Stop
    $resultado.defender_disponivel = $true
    $resultado.defender_tempo_real = [bool]$defender.RealTimeProtectionEnabled
    $resultado.defender_antivirus = [bool]$defender.AntivirusEnabled
    if ($defender.AntivirusSignatureLastUpdated) {
        $resultado.defender_definicoes_data = $defender.AntivirusSignatureLastUpdated.ToString('dd/MM/yyyy HH:mm')
    }
} catch {
    $resultado.defender_disponivel = $false
}

try {
    $bl = Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop
    $resultado.bitlocker_disponivel = $true
    $resultado.bitlocker_status = "$($bl.ProtectionStatus)"
    $resultado.bitlocker_percentual = $bl.EncryptionPercentage
} catch {
    $resultado.bitlocker_disponivel = $false
}

try {
    $tpm = Get-Tpm -ErrorAction Stop
    $resultado.tpm_presente = [bool]$tpm.TpmPresent
    $resultado.tpm_pronto = [bool]$tpm.TpmReady
    $resultado.tpm_habilitado = [bool]$tpm.TpmEnabled
} catch {
    $resultado.tpm_presente = $false
}

try {
    $sb = Confirm-SecureBootUEFI -ErrorAction Stop
    $resultado.secureboot_disponivel = $true
    $resultado.secureboot_ativo = [bool]$sb
} catch {
    $resultado.secureboot_disponivel = $false
}

$resultado | ConvertTo-Json -Depth 3 -Compress
"""


def obter_status_seguranca() -> dict:
    """Consulta Defender, BitLocker, TPM e Secure Boot. Nunca lança
    exceção: em caso de falha total na consulta, devolve um
    dicionário com "erro" preenchido. Campos individuais indisponíveis
    (ex.: sem TPM, sem BitLocker) vêm marcados com "*_disponivel":
    False / "*_presente": False — a UI decide como exibir cada caso
    sem precisar tratar exceção nenhuma."""
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_PS],
            capture_output=True, text=True, errors="ignore",
            timeout=_TIMEOUT_SEGUNDOS, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        return {"erro": f"Não foi possível consultar o status de segurança: {e}"}

    saida = (resultado.stdout or "").strip()
    if not saida:
        return {"erro": "O PowerShell não retornou nenhuma informação de segurança."}

    try:
        bruto = json.loads(saida)
    except (json.JSONDecodeError, ValueError):
        return {"erro": "Não foi possível interpretar o resultado da consulta de segurança."}

    return {
        "defender_disponivel": bool(bruto.get("defender_disponivel")),
        "defender_tempo_real": bruto.get("defender_tempo_real"),
        "defender_antivirus": bruto.get("defender_antivirus"),
        "defender_definicoes_data": bruto.get("defender_definicoes_data"),
        "bitlocker_disponivel": bool(bruto.get("bitlocker_disponivel")),
        "bitlocker_status": bruto.get("bitlocker_status"),
        "bitlocker_percentual": bruto.get("bitlocker_percentual"),
        "tpm_presente": bool(bruto.get("tpm_presente")),
        "tpm_pronto": bruto.get("tpm_pronto"),
        "tpm_habilitado": bruto.get("tpm_habilitado"),
        "secureboot_disponivel": bool(bruto.get("secureboot_disponivel")),
        "secureboot_ativo": bruto.get("secureboot_ativo"),
    }