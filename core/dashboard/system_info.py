# ==========================================================
# Arquivo: core/dashboard/system_info.py
# Responsabilidade: Informações gerais do sistema — atualmente,
# leitura do espaço em disco (total/usado/livre) das unidades
# disponíveis.
# ==========================================================

import ctypes
import shutil


def _letras_unidades_existentes():
    """Enumera as letras de unidade atualmente atribuídas no sistema,
    via GetLogicalDrives — a API oficial do Windows para essa
    finalidade — em vez de checar uma faixa fixa (C a H) com
    os.path.exists().

    Duas vantagens sobre a checagem manual anterior:
    - Cobre TODAS as letras em uso (discos extras, pendrives, unidades
      de rede mapeadas), não apenas C–H.
    - GetLogicalDrives apenas lê o mapa de letras atribuídas; não
      sonda o dispositivo, evitando o atraso perceptível que ocorre ao
      consultar uma unidade removível sem mídia (ex.: leitor de DVD
      vazio) por outros meios.

    Ignora A: e B:, reservadas historicamente a unidades de disquete —
    mesmo ponto de partida (C:) do código anterior.
    """
    mascara = ctypes.windll.kernel32.GetLogicalDrives()
    return [chr(ord("A") + i) for i in range(2, 26) if mascara & (1 << i)]


def obter_espaco_disco():
    """Retorna uma lista de dicionários com informações de espaço em
    disco para cada unidade existente no sistema (C: em diante).

    Cada item: {"unidade", "total_gb", "usado_gb", "pct_usado",
    "livre_gb"} ou {"unidade", "erro"} em caso de falha na leitura.
    """
    letras = [f"{c}:\\" for c in _letras_unidades_existentes()]
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