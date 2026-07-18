# ==========================================================
# Arquivo: core/dashboard/system_info.py
# Responsabilidade: Informações gerais do sistema — atualmente,
# leitura do espaço em disco (total/usado/livre) das unidades
# disponíveis.
# ==========================================================

import os
import shutil


def obter_espaco_disco():
    """Retorna uma lista de dicionários com informações de espaço em
    disco para cada unidade de C a H que existir no sistema.

    Cada item: {"unidade", "total_gb", "usado_gb", "pct_usado",
    "livre_gb"} ou {"unidade", "erro"} em caso de falha na leitura.
    """
    letras = [f"{c}:\\" for c in "CDEFGH" if os.path.exists(f"{c}:\\")]
    info = []
    gb = 1024 ** 3
    for unidade in letras:
        try:
            total, usado, livre = shutil.disk_usage(unidade)
            pct_usado = (usado / total) * 100 if total else 0
            livre_gb = livre / gb

            info.append({
                "unidade": unidade,
                "total_gb": total / gb,
                "usado_gb": usado / gb,
                "pct_usado": pct_usado,
                "livre_gb": livre_gb,
            })
        except Exception as e:
            info.append({"unidade": unidade, "erro": str(e)})
    return info