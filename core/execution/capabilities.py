# ==========================================================
# Arquivo: core/execution/capabilities.py
# Responsabilidade: Declarar, para cada tarefa, quais recursos de
# acompanhamento ela realmente oferece — se fornece percentual
# oficial, se produz log em tempo real, se exige reinicialização,
# tempo estimado. A interface usa essas capacidades para decidir
# sozinha o que mostrar (barra determinada, barra indeterminada,
# aviso de reinicialização), sem nenhum "if" espalhado verificando
# tarefa por tarefa.
#
# Isso NÃO afeta o comportamento das tarefas em si — é só metadado
# declarativo, lido pela UI através dos eventos do ExecutionManager.
# ==========================================================

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class TaskCapabilities:
    progresso_real: bool = False          # a tarefa informa percentual oficial (0-100)?
    log_tempo_real: bool = False          # a saída chega linha a linha durante a execução?
    requer_reinicializacao: bool = False
    tempo_estimado_min: Optional[int] = None
    permite_cancelamento: bool = False    # reservado para uma etapa futura

    def como_dict(self) -> dict:
        return asdict(self)


# Uma entrada por chave de tarefa — mesma chave usada em
# utils.constants.TAREFAS e no mapa_funcoes do main_window.
CAPACIDADES_TAREFAS = {
    "dism": TaskCapabilities(
        requer_reinicializacao=True, tempo_estimado_min=30,
    ),
    "sfc": TaskCapabilities(
        requer_reinicializacao=True, tempo_estimado_min=30,
    ),
    "dns": TaskCapabilities(
        tempo_estimado_min=1,
    ),
    "temp": TaskCapabilities(
        progresso_real=True, tempo_estimado_min=2,
    ),
    "recycle": TaskCapabilities(
        tempo_estimado_min=1,
    ),
    "winupdate": TaskCapabilities(
        progresso_real=True, tempo_estimado_min=3,
    ),
    "thumbnail": TaskCapabilities(
        progresso_real=True, tempo_estimado_min=1,
    ),
    "chkdsk": TaskCapabilities(
        requer_reinicializacao=True, tempo_estimado_min=1,
    ),
    "lab_rapido": TaskCapabilities(progresso_real=True, tempo_estimado_min=1),
    "lab_medio": TaskCapabilities(progresso_real=True, tempo_estimado_min=1),
    "lab_longo": TaskCapabilities(progresso_real=True, tempo_estimado_min=2),
    "lab_logs": TaskCapabilities(progresso_real=True, log_tempo_real=True, tempo_estimado_min=1),
    "lab_indeterminado": TaskCapabilities(tempo_estimado_min=1),
    "lab_erro": TaskCapabilities(progresso_real=True, tempo_estimado_min=1),
    "lab_aviso": TaskCapabilities(progresso_real=True, tempo_estimado_min=1),
    "lab_reinicializacao": TaskCapabilities(
        progresso_real=True, requer_reinicializacao=True, tempo_estimado_min=1
    ),
    "lab_aleatorio": TaskCapabilities(progresso_real=True, tempo_estimado_min=1),
}

CAPACIDADES_PADRAO = TaskCapabilities()


def capacidades_de(chave: str) -> TaskCapabilities:
    """Retorna as capacidades declaradas para `chave`, ou um conjunto
    padrão (tudo False/None) se a tarefa não estiver mapeada — nunca
    lança exceção, para que uma tarefa nova sem entrada aqui apareça
    simplesmente como "sem progresso real" em vez de quebrar a UI."""
    return CAPACIDADES_TAREFAS.get(chave, CAPACIDADES_PADRAO)