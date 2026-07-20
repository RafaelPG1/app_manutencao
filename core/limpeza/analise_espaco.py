# ==========================================================
# Arquivo: core/limpeza/analise_espaco.py
# Responsabilidade: Estimar (somente leitura, nada é apagado) o
# espaço recuperável nas categorias mais relevantes de limpeza, para
# o usuário decidir se quer prosseguir ANTES de marcar as tarefas —
# categoria Limpeza, Fase 6.
#
# AÇÃO INSTANTÂNEA, NÃO É UMA TAREFA DE LOTE — mesmo racional já
# documentado em core/diagnostico/espaco_disco.py.
#
# Reaproveita os MESMOS caminhos oficiais já usados pelas tarefas de
# limpeza existentes, em vez de redefini-los:
#   - Temporários: os.environ["TEMP"] e SystemRoot\Temp — os mesmos
#     dois caminhos que core/limpeza/cleanup.py:limpar_temporarios()
#     já limpa.
#   - Delivery Optimization: SystemRoot\SoftwareDistribution\
#     DeliveryOptimization — pasta oficial onde o Windows guarda esse
#     cache (limpa por core/limpeza/delivery_optimization.py).
#   - Windows.old: C:\Windows.old — mesma pasta verificada por
#     core/limpeza/windows_old.py.
#
# Depois de ver esta estimativa, o usuário decide se quer marcar as
# tarefas correspondentes e clicar em "Executar selecionadas" — o
# próprio fluxo de confirmação já existente (ui/dialogs.py:
# confirmar_execucao) é o "deseja continuar?" pedido nesta etapa; não
# foi necessário criar um segundo mecanismo de confirmação.
# ==========================================================

import os

_GB = 1024 ** 3


def _tamanho_pasta(caminho: str) -> int:
    total = 0
    for raiz, _sub, arquivos in os.walk(caminho, onerror=lambda _e: None):
        for nome in arquivos:
            try:
                total += os.path.getsize(os.path.join(raiz, nome))
            except OSError:
                continue
    return total


def calcular_espaco_recuperavel() -> dict:
    """Retorna {"temp_gb", "delivery_optimization_gb",
    "windows_old_gb", "total_gb"} — valores em GB (float). Uma
    categoria sem a pasta correspondente no computador do usuário
    aparece como 0.0 (nunca gera erro)."""
    temp_dir = os.environ.get("TEMP", "")
    system_root = os.environ.get("SystemRoot", "")

    total_temp = 0
    if temp_dir and os.path.isdir(temp_dir):
        total_temp += _tamanho_pasta(temp_dir)
    if system_root:
        sys_temp = os.path.join(system_root, "Temp")
        if os.path.isdir(sys_temp):
            total_temp += _tamanho_pasta(sys_temp)

    delivery_bytes = 0
    if system_root:
        pasta_do = os.path.join(system_root, "SoftwareDistribution", "DeliveryOptimization")
        if os.path.isdir(pasta_do):
            delivery_bytes = _tamanho_pasta(pasta_do)

    windows_old_bytes = 0
    if os.path.isdir(r"C:\Windows.old"):
        windows_old_bytes = _tamanho_pasta(r"C:\Windows.old")

    temp_gb = total_temp / _GB
    delivery_gb = delivery_bytes / _GB
    windows_old_gb = windows_old_bytes / _GB

    return {
        "temp_gb": temp_gb,
        "delivery_optimization_gb": delivery_gb,
        "windows_old_gb": windows_old_gb,
        "total_gb": temp_gb + delivery_gb + windows_old_gb,
    }
