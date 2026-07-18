# ==========================================================
# Arquivo: utils/tasks.py
# Responsabilidade: FONTE ÚNICA DE VERDADE para os metadados de
# todas as tarefas do aplicativo — identidade (chave, ícone, título),
# apresentação (descrição, comando técnico) e capacidades de
# execução (progresso real, tempo estimado, exige reinicialização
# etc.), tudo em um único objeto por tarefa.
#
# HISTÓRICO (por que este arquivo existe): antes havia duas listas
# paralelas, indexadas pela mesma chave e mantidas manualmente em
# sincronia — utils/constants.py (TAREFAS: chave/ícone/título/
# descrição/categoria) e core/execution/capabilities.py
# (CAPACIDADES_TAREFAS: progresso_real/tempo_estimado_min/...).
# A UI, por sua vez, nem lia a segunda lista para exibir o tempo
# estimado: derivava um valor por conta própria interpretando a
# DESCRIÇÃO em texto livre da primeira lista, com duas heurísticas
# de regex diferentes (uma para o card, outra para o resumo da
# categoria) — que podiam (e passaram a) divergir entre si e do
# valor declarado em capabilities.py, que nunca chegava a ser usado.
# Esse arquivo elimina as duas listas e as duas heurísticas: cada
# tarefa tem exatamente UM registro, com TODOS os seus dados, lido
# igualmente por toda a interface e pelo motor de execução. A
# descrição exibida ao usuário nunca é interpretada — é texto puro.
# ==========================================================

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class TaskDefinition:
    """Metadados completos de uma única tarefa.

    Campos de apresentação (lidos pela UI para montar sidebar,
    cards e o resumo da categoria):
        chave, icone, titulo, descricao, categoria, comando_tecnico

    Campos de execução (lidos pelo ExecutionManager e repassados à UI
    através do evento 'capacidades' — ver core/execution/reporter.py
    e ui/execution_panel.py):
        progresso_real, log_tempo_real, requer_reinicializacao,
        tempo_estimado_min, permite_cancelamento

    IMPORTANTE: `descricao` é sempre texto final, pronto para
    exibição — nunca deve ser reprocessada, dividida ou varrida por
    regex em busca de números/palavras-chave. Qualquer informação
    estruturada (tempo estimado, comando técnico) já vem em seu
    próprio campo, explícito.
    """
    chave: str
    icone: str
    titulo: str
    descricao: str
    categoria: str
    comando_tecnico: Optional[str] = None

    progresso_real: bool = False
    log_tempo_real: bool = False
    requer_reinicializacao: bool = False
    tempo_estimado_min: Optional[int] = None
    # NOTA: `requer_reinicializacao` e `log_tempo_real`, assim como
    # `permite_cancelamento` abaixo, já são declarados corretamente
    # por tarefa, mas hoje não têm nenhum consumidor na UI (só
    # `progresso_real` é lido, em ui/execution_panel.py, para decidir
    # entre barra determinada/indeterminada). Não são dado morto por
    # duplicidade — são metadado legítimo aguardando uma tela futura
    # (ex.: aviso "esta tarefa exige reinicialização"); mantidos aqui
    # de propósito, e não em capabilities.py, para não reabrir uma
    # segunda fonte de verdade.
    permite_cancelamento: bool = False  # reservado para uma etapa futura

    def capacidades_dict(self) -> dict:
        """Subconjunto de campos de EXECUÇÃO (sem os de apresentação),
        no formato que o ExecutionManager já emite no evento
        'capacidades' — mantém compatibilidade com ui/execution_panel.py
        sem nenhuma mudança nele."""
        return {
            "progresso_real": self.progresso_real,
            "log_tempo_real": self.log_tempo_real,
            "requer_reinicializacao": self.requer_reinicializacao,
            "tempo_estimado_min": self.tempo_estimado_min,
            "permite_cancelamento": self.permite_cancelamento,
        }


# ---------------- TAREFAS DISPONÍVEIS (fonte única) ----------------
TAREFAS: List[TaskDefinition] = [
    TaskDefinition(
        chave="dism", icone="\U0001F6E0", titulo="Reparar imagem do Windows",
        descricao="Verifica e repara a imagem do sistema operacional (component store).",
        categoria="manutencao", comando_tecnico="DISM /Online /Cleanup-Image /RestoreHealth",
        requer_reinicializacao=True, tempo_estimado_min=30,
    ),
    TaskDefinition(
        chave="sfc", icone="\U0001F9E9", titulo="Verificar arquivos do sistema",
        descricao="Verifica e repara arquivos protegidos do sistema.",
        categoria="manutencao", comando_tecnico="SFC /scannow",
        requer_reinicializacao=True, tempo_estimado_min=15,
    ),
    TaskDefinition(
        chave="dns", icone="\U0001F310", titulo="Limpar cache de DNS",
        descricao="Limpa o cache de resolução de nomes DNS do Windows.",
        categoria="limpeza", comando_tecnico="ipconfig /flushdns",
        tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="temp", icone="\U0001F5D1", titulo="Limpar arquivos temporários",
        descricao="Limpa pastas TEMP do usuário e do sistema.",
        categoria="limpeza",
        progresso_real=True, tempo_estimado_min=2,
    ),
    TaskDefinition(
        chave="recycle", icone="\u267B", titulo="Esvaziar a lixeira",
        descricao="Remove permanentemente os itens da lixeira.",
        categoria="limpeza",
        tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="winupdate", icone="\U0001F504", titulo="Limpar cache do Windows Update",
        descricao="Limpa a pasta SoftwareDistribution\\Download do Windows Update.",
        categoria="limpeza",
        progresso_real=True, tempo_estimado_min=3,
    ),
    TaskDefinition(
        chave="thumbnail", icone="\U0001F5BC", titulo="Limpar cache de miniaturas",
        descricao="Remove os arquivos de cache de miniaturas (thumbcache) do usuário atual.",
        categoria="limpeza",
        progresso_real=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="chkdsk", icone="\U0001F4BD", titulo="Agendar verificação de disco",
        descricao="Agenda uma verificação completa do disco para a próxima reinicialização.",
        categoria="diagnostico", comando_tecnico="CHKDSK",
        requer_reinicializacao=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_rapido", icone="\u26A1", titulo="Teste rápido",
        descricao="Simulação rápida de progresso — sobe até 100% em poucos segundos.",
        categoria="laboratorio",
        progresso_real=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_medio", icone="\U0001F550", titulo="Teste médio",
        descricao="Simulação de progresso gradual ao longo de alguns segundos.",
        categoria="laboratorio",
        progresso_real=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_longo", icone="\U0001F551", titulo="Teste longo",
        descricao="Simulação de execução contínua e mais demorada.",
        categoria="laboratorio",
        progresso_real=True, tempo_estimado_min=2,
    ),
    TaskDefinition(
        chave="lab_logs", icone="\U0001F4C4", titulo="Teste com muitos logs",
        descricao="Gera centenas de linhas de log simuladas para testar o console.",
        categoria="laboratorio",
        progresso_real=True, log_tempo_real=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_indeterminado", icone="\U0001F504", titulo="Teste barra indeterminada",
        descricao="Simulação sem percentual — testa a barra de progresso indeterminada.",
        categoria="laboratorio",
        tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_erro", icone="\u274C", titulo="Teste de erro",
        descricao="Simulação que falha propositalmente no meio da execução.",
        categoria="laboratorio",
        progresso_real=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_aviso", icone="\u26A0", titulo="Teste de aviso",
        descricao="Simulação que emite avisos e finaliza com sucesso.",
        categoria="laboratorio",
        progresso_real=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_reinicializacao", icone="\U0001F501", titulo="Teste de reinicialização",
        descricao="Simulação que sinaliza necessidade de reinício (não reinicia de verdade).",
        categoria="laboratorio",
        progresso_real=True, requer_reinicializacao=True, tempo_estimado_min=1,
    ),
    TaskDefinition(
        chave="lab_aleatorio", icone="\U0001F3B2", titulo="Teste aleatório",
        descricao="Mistura progresso, logs e avisos aleatoriamente para testar estabilidade.",
        categoria="laboratorio",
        progresso_real=True, tempo_estimado_min=1,
    ),
]

_TAREFAS_POR_CHAVE = {t.chave: t for t in TAREFAS}

# Retornada por capacidades_de() para uma chave desconhecida — nunca
# lança exceção, para que uma tarefa nova sem entrada aqui apareça
# simplesmente como "sem progresso real" em vez de quebrar a UI.
CAPACIDADES_PADRAO = TaskDefinition(
    chave="", icone="", titulo="", descricao="", categoria="",
).capacidades_dict()


def tarefas_por_categoria(categoria: str) -> List[TaskDefinition]:
    """Retorna a sublista de TAREFAS pertencentes a uma categoria."""
    return [t for t in TAREFAS if t.categoria == categoria]


def tarefa_por_chave(chave: str) -> Optional[TaskDefinition]:
    """Retorna a TaskDefinition completa de uma tarefa, ou None se a
    chave não existir."""
    return _TAREFAS_POR_CHAVE.get(chave)


def capacidades_de(chave: str) -> dict:
    """Retorna apenas o subconjunto de campos de EXECUÇÃO da tarefa
    (mesmo formato usado antes em core/execution/capabilities.py),
    para o ExecutionManager repassar no evento 'capacidades'."""
    tarefa = _TAREFAS_POR_CHAVE.get(chave)
    if tarefa is None:
        return dict(CAPACIDADES_PADRAO)
    return tarefa.capacidades_dict()
