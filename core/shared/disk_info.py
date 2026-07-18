# ==========================================================
# Arquivo: core/shared/disk_info.py
# Responsabilidade: Detecção do tipo de disco (SSD/HDD) da
# unidade C: via PowerShell.
# ==========================================================

import subprocess


def detectar_tipo_disco() -> str:
    ps_cmd = (
        "try { $d = Get-PhysicalDisk | Where-Object { $_.DeviceId -eq "
        "(Get-Partition -DriveLetter C).DiskNumber }; "
        "if ($d.MediaType -eq 'SSD') { 'SSD' } else { 'HDD' } } "
        "catch { 'HDD' }"
    )
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        tipo = resultado.stdout.strip()
        return tipo if tipo in ("SSD", "HDD") else "HDD"
    except Exception:
        return "HDD"
