# ==========================================================
# Arquivo: core/limpeza/cleanup.py
# Responsabilidade: Limpeza de arquivos temporários das pastas
# TEMP do usuário e do sistema, incluindo a função auxiliar de
# remoção de conteúdo de pastas usada por outras rotinas.
#
# `limpar_pasta` agora aceita um callback opcional `ao_progredir`,
# chamado a cada item processado com (processados, total) — dados
# REAIS, contados antes de começar. Isso permite que quem chama
# (aqui e em update_cache.py) gere um percentual verdadeiro baseado
# no loop que ela mesma controla, sem estimativas nem timers.
# ==========================================================

import os
import shutil

from utils.helpers import agora
from utils.logger import log


def limpar_pasta(pasta: str, ao_progredir=None, itens=None):
    """Remove todo o conteúdo de uma pasta, ignorando itens em uso.

    ao_progredir(processados, total), quando fornecido, é chamado
    após cada item ser processado (removido ou ignorado) — total é a
    contagem REAL de itens da pasta no início da operação.

    itens, se fornecido, evita uma segunda listagem da pasta quando
    quem chama já a listou antes (ex.: para somar o total de várias
    pastas de antemão) — além de economizar uma varredura, evita que
    o total contado e o total realmente processado divirjam caso
    algum outro processo crie/remova arquivos entre as duas listagens.

    Retorna (removidos, ignorados).
    """
    if itens is None:
        itens = os.listdir(pasta)
    total = len(itens)
    removidos = 0
    ignorados = 0
    for i, nome in enumerate(itens, start=1):
        caminho = os.path.join(pasta, nome)
        try:
            if os.path.islink(caminho):
                # Link simbólico: remover apenas o link, sem seguir o
                # alvo. No Windows, um link para um diretório precisa
                # de os.rmdir() — os.remove() (DeleteFile) falha nesse
                # caso porque o item tem o atributo de diretório, ainda
                # que seja um reparse point; a falha cairia no except
                # abaixo e o link ficaria erroneamente contado como
                # "em uso" (ignorado) em vez de removido.
                if os.path.isdir(caminho):
                    os.rmdir(caminho)
                else:
                    os.remove(caminho)
            elif os.path.isdir(caminho):
                shutil.rmtree(caminho)
            else:
                os.remove(caminho)
            removidos += 1
        except Exception:
            ignorados += 1
        if ao_progredir:
            ao_progredir(i, total)
    return removidos, ignorados


def limpar_temporarios(reporter):
    """reporter: TaskReporter — progress() recebe um percentual REAL,
    calculado a partir da contagem verdadeira de itens nas pastas
    TEMP do usuário e do sistema, antes de começar a remoção."""
    log(f"[TEMP] Iniciado em {agora()}")
    temp_dir = os.environ.get("TEMP", "")
    system_root = os.environ.get("SystemRoot", "")

    alvos = []  # (rotulo, caminho)
    if temp_dir and os.path.isdir(temp_dir):
        alvos.append(("Pasta usuário", temp_dir))
    else:
        reporter.error(f"[ERRO] Pasta TEMP inválida: {temp_dir}\n")
        log(f"[TEMP] ERRO - Pasta TEMP inválida: {temp_dir}")

    if system_root:
        sys_temp = os.path.join(system_root, "Temp")
        if os.path.isdir(sys_temp):
            alvos.append(("Pasta sistema", sys_temp))

    # Listagem REAL de itens antes de começar, em todas as pastas, para
    # calcular um percentual verdadeiro ao longo de toda a operação —
    # não apenas dentro de uma pasta por vez. A mesma listagem é
    # repassada a limpar_pasta() abaixo (parâmetro itens) para não
    # listar cada pasta duas vezes.
    alvos_com_itens = [(rotulo, caminho, os.listdir(caminho)) for rotulo, caminho in alvos]
    total_geral = sum(len(itens) for _, _, itens in alvos_com_itens) or 1
    processados_total = 0

    for rotulo, caminho, itens in alvos_com_itens:
        def _ao_progredir(i, total, rotulo=rotulo):
            nonlocal processados_total
            processados_total += 1
            reporter.progress(min((processados_total / total_geral) * 100, 100))
            reporter.message(f"{rotulo}: {i}/{total}")

        removidos, ignorados = limpar_pasta(caminho, ao_progredir=_ao_progredir, itens=itens)
        reporter.log(
            f"[INFO] {rotulo}: {removidos} itens removidos, {ignorados} em uso (ignorados)\n"
        )
        log(f"[TEMP] {rotulo} limpa: {caminho} ({removidos} removidos, {ignorados} ignorados)")

    reporter.progress(100)
    reporter.log("[SUCESSO] Limpeza de temporários concluída.\n", "ok")
    log(f"[TEMP] SUCESSO - Concluído em {agora()}")