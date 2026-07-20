# ==========================================================
# Arquivo: core/shared/disk_cleanup_oficial.py
# Responsabilidade: Executar categorias da ferramenta OFICIAL
# "Limpeza de Disco" do Windows (cleanmgr.exe) sem abrir a janela de
# seleção — mecanismo documentado pela própria Microsoft para uso
# programático/roteirizado da Limpeza de Disco.
#
# COMO FUNCIONA (oficial): cada categoria de limpeza (ex.: "Previous
# Installations" = Windows.old) é uma subchave do registro em
# HKLM\...\VolumeCaches. Marcar uma subchave para um "sageset"
# (gravando StateFlagsNNNN = 2, onde NNNN é um número de perfil à
# escolha) e depois rodar `cleanmgr /sagerun:NNNN` executa a limpeza
# de todas as categorias marcadas com aquele NNNN, sem nenhuma janela
# de seleção. Ao final, esta rotina volta as flags para 0 — não deixa
# nenhuma configuração residual no sistema do usuário além da própria
# limpeza executada.
#
# Reaproveitado por core/limpeza/windows_old.py, logs_antigos.py e
# cache_sistema.py (Fase 6) em vez de cada um reimplementar o mesmo
# mecanismo de registro + cleanmgr.
#
# Categorias ausentes nesta versão/edição do Windows são puladas
# SEM gerar erro — nem toda categoria existe em toda instalação.
# ==========================================================

import subprocess

from utils.helpers import agora
from utils.logger import log

_SAGESET_ID = 9876  # perfil interno deste app (não usado pelo usuário/Windows)
_CAMINHO_BASE = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
_TIMEOUT_SEGUNDOS = 900  # cleanmgr pode demorar bastante com Windows.old grande


def executar_limpeza_disco_oficial(reporter, categorias: list, tag_log: str, titulo_amigavel: str) -> dict:
    """categorias: nomes exatos das subchaves em VolumeCaches
    (ex.: ["Previous Installations"]).

    Retorna {"processadas": [...], "ausentes": [...]}. Nunca lança
    exceção — qualquer falha vira um reporter.log de aviso/erro."""
    try:
        import winreg
    except ImportError:
        reporter.log(f"[ERRO] {titulo_amigavel}: recurso disponível apenas no Windows.\n", "erro")
        log(f"[{tag_log}] ERRO - winreg indisponivel neste sistema - {agora()}")
        return {"processadas": [], "ausentes": list(categorias)}

    log(f"[{tag_log}] Iniciado em {agora()}")
    reporter.log(f"[INFO] Iniciando {titulo_amigavel}...\n", "titulo")

    processadas = []
    ausentes = []
    for categoria in categorias:
        caminho_chave = f"{_CAMINHO_BASE}\\{categoria}"
        try:
            chave = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, caminho_chave, 0, winreg.KEY_SET_VALUE
            )
        except OSError:
            ausentes.append(categoria)
            continue
        try:
            winreg.SetValueEx(chave, f"StateFlags{_SAGESET_ID:04d}", 0, winreg.REG_DWORD, 2)
            processadas.append(categoria)
        except OSError:
            ausentes.append(categoria)
        finally:
            winreg.CloseKey(chave)

    if not processadas:
        reporter.log(
            f"[INFO] Nenhuma das categorias de \"{titulo_amigavel}\" está disponível "
            "neste computador — nada a limpar.\n",
            "titulo",
        )
        log(f"[{tag_log}] INFO - nenhuma categoria disponivel - {agora()}")
        return {"processadas": [], "ausentes": ausentes}

    reporter.message(f"Executando {titulo_amigavel}...")
    try:
        subprocess.run(
            ["cleanmgr", f"/sagerun:{_SAGESET_ID}"],
            capture_output=True, timeout=_TIMEOUT_SEGUNDOS,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        reporter.log(f"[ERRO] {titulo_amigavel} demorou demais e foi cancelada.\n", "erro")
        log(f"[{tag_log}] ERRO - timeout - {agora()}")
        _limpar_flags(winreg, processadas)
        return {"processadas": [], "ausentes": ausentes}
    except Exception as e:
        reporter.log(f"[ERRO] Falha ao executar {titulo_amigavel}: {e}\n", "erro")
        log(f"[{tag_log}] ERRO - {e} - {agora()}")
        _limpar_flags(winreg, processadas)
        return {"processadas": [], "ausentes": ausentes}

    _limpar_flags(winreg, processadas)

    if ausentes:
        reporter.log(
            f"[INFO] Categorias não disponíveis neste computador (puladas): {', '.join(ausentes)}.\n"
        )
    reporter.log(f"[SUCESSO] {titulo_amigavel} concluída.\n", "ok")
    log(f"[{tag_log}] SUCESSO - processadas={processadas} ausentes={ausentes} - {agora()}")
    return {"processadas": processadas, "ausentes": ausentes}


def _limpar_flags(winreg_mod, categorias):
    """Zera as StateFlags gravadas, para não deixar nenhuma marcação
    residual no perfil de Limpeza de Disco do usuário."""
    for categoria in categorias:
        caminho_chave = f"{_CAMINHO_BASE}\\{categoria}"
        try:
            chave = winreg_mod.OpenKey(
                winreg_mod.HKEY_LOCAL_MACHINE, caminho_chave, 0, winreg_mod.KEY_SET_VALUE
            )
            winreg_mod.SetValueEx(chave, f"StateFlags{_SAGESET_ID:04d}", 0, winreg_mod.REG_DWORD, 0)
            winreg_mod.CloseKey(chave)
        except OSError:
            pass
