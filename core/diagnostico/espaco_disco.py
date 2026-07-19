# ==========================================================
# Arquivo: core/diagnostico/espaco_disco.py
# Responsabilidade: Análise de quais pastas de nível superior de uma
# unidade ocupam mais espaço (leitura apenas — nada é apagado aqui;
# a decisão do roadmap foi explícita: "nesta etapa será apenas
# leitura").
#
# POR QUE ISTO É UMA AÇÃO INSTANTÂNEA, E NÃO UMA TAREFA DE LOTE
# (checkbox + "Executar selecionadas"):
# O painel de execução (ui/execution_panel.py) não tem mais um
# console interno — ele foi removido de propósito porque SFC/DISM já
# mostram sua saída nativamente no Prompt de Comando, então o
# console ficou redundante e foi tirado (ver o cabeçalho de
# execution_panel.py). Isso significa que reporter.log() hoje NÃO É
# EXIBIDO em lugar nenhum da interface durante uma execução — só fica
# gravado no log interno, para depuração.
#
# Para uma tarefa cujo VALOR é justamente o resultado (quais pastas
# ocupam mais espaço), rodar como tarefa de lote faria o usuário
# terminar a execução sem ver nada na tela. Por isso esta função (e,
# pelo mesmo motivo, smart_disco.py e eventos_criticos.py) foi feita
# para ser chamada diretamente pela UI, fora do ExecutionManager —
# exatamente como core/dashboard/system_info.obter_espaco_disco() já
# é chamada pelo botão "Ver espaço em disco" do Dashboard, mostrando
# o resultado numa janela dedicada. Nenhuma tarefa de lote (DISM,
# SFC, CHKDSK etc.) foi alterada por essa decisão.
#
# Sem um único cmdlet "tudo em um" que devolva tamanho por pasta, a
# varredura usa os.scandir/os.walk (biblioteca padrão do Python, sem
# nenhuma dependência externa) somando o tamanho de cada arquivo —
# abordagem padrão para esse tipo de cálculo, com tolerância a pastas
# sem permissão de leitura (são somadas parcialmente, nunca derrubam
# a análise inteira).
# ==========================================================

import os

_LIMITE_RESULTADOS = 15


def _tamanho_pasta(caminho: str) -> int:
    """Soma o tamanho de todos os arquivos dentro de `caminho`,
    recursivamente. Pastas/arquivos sem permissão de leitura são
    ignorados silenciosamente (via onerror), sem interromper a soma
    do restante — mesma tolerância a erro por item já usada em
    core/limpeza/cleanup.py."""
    total = 0
    for raiz, _subpastas, arquivos in os.walk(caminho, onerror=lambda _e: None):
        for nome in arquivos:
            try:
                total += os.path.getsize(os.path.join(raiz, nome))
            except OSError:
                continue
    return total


def analisar_espaco_pastas(unidade: str = "C:\\", callback_status=None) -> dict:
    """Varre as pastas de primeiro nível de `unidade` e devolve as
    que mais ocupam espaço, maior primeiro.

    callback_status(texto: str): chamado (se fornecido) a cada pasta
    processada, com uma mensagem curta de progresso — usado pela UI
    para atualizar um indicador de "Analisando..." enquanto a
    varredura roda em segundo plano (pode levar de alguns segundos a
    mais de um minuto em unidades grandes).

    Retorna {"unidade": ..., "itens": [(nome, tamanho_bytes), ...]}
    ou {"erro": "..."} se a unidade não existir/não puder ser lida.
    Nunca lança exceção."""
    if not os.path.isdir(unidade):
        return {"erro": f"A unidade {unidade} não foi encontrada."}

    try:
        entradas = [e for e in os.scandir(unidade) if e.is_dir(follow_symlinks=False)]
    except OSError as e:
        return {"erro": f"Não foi possível ler o conteúdo de {unidade}: {e}"}

    total = len(entradas)
    resultados = []
    for i, entrada in enumerate(entradas, start=1):
        if callback_status:
            callback_status(f"Analisando {entrada.name} ({i}/{total})...")
        try:
            tamanho = _tamanho_pasta(entrada.path)
        except Exception:
            tamanho = 0
        resultados.append((entrada.name, tamanho))

    resultados.sort(key=lambda item: item[1], reverse=True)
    return {"unidade": unidade, "itens": resultados[:_LIMITE_RESULTADOS]}
