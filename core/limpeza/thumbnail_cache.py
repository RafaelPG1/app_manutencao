# ==========================================================
# Arquivo: core/limpeza/thumbnail_cache.py
# Responsabilidade: Limpeza do cache de miniaturas do Explorer
# (arquivos thumbcache_*.db do usuário atual).
#
# O app já controla totalmente este loop (lista os arquivos antes de
# remover), então o percentual reportado é sempre real: contagem
# verdadeira de arquivos encontrados / itens já processados.
# ==========================================================

import os

from utils.helpers import agora
from utils.logger import log


def limpar_cache_miniaturas(reporter):
    log(f"[THUMBNAIL] Iniciado em {agora()}")
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    pasta = os.path.join(local_appdata, "Microsoft", "Windows", "Explorer") if local_appdata else ""
    removidos, ignorados = 0, 0

    if pasta and os.path.isdir(pasta):
        arquivos = [
            nome for nome in os.listdir(pasta)
            if nome.lower().startswith("thumbcache_") and nome.lower().endswith(".db")
        ]
        total = len(arquivos)
        for i, nome in enumerate(arquivos, start=1):
            try:
                os.remove(os.path.join(pasta, nome))
                removidos += 1
            except Exception:
                ignorados += 1
            if total:
                reporter.progress((i / total) * 100)
                reporter.message(f"{nome} ({i}/{total})")

    reporter.progress(100)
    reporter.log(
        f"[SUCESSO] Cache de miniaturas: {removidos} removidos, {ignorados} em uso (ignorados).\n",
        "ok"
    )
    log(f"[THUMBNAIL] SUCESSO - {removidos} removidos, {ignorados} ignorados - {agora()}")