# ==========================================================
# Arquivo: core/ferramentas/utilitarios_windows.py
# Responsabilidade: Abrir os utilitários administrativos OFICIAIS do
# Windows (Gerenciador de Dispositivos, Gerenciamento de Disco,
# Serviços, Agendador de Tarefas, Visualizador de Eventos, Monitor de
# Recursos, Monitor de Desempenho, Informações do Sistema, MSConfig,
# Editor do Registro, Firewall do Windows, Editor de Diretiva de
# Grupo, Conexões de Rede e Central de Rede e Compartilhamento) —
# categoria Ferramentas, Fase 7.
#
# Mesmo padrão de core/recuperacao/system_restore_wizard.py: NÃO
# reimplementa nenhuma lógica própria — cada função apenas abre a
# ferramenta nativa do Windows (subprocess.Popen) numa janela própria
# do sistema operacional, fora do aplicativo, e devolve
# {"sucesso": bool, "mensagem": str} — nunca lança exceção. Por isso
# são AÇÕES INSTANTÂNEAS (ver o cabeçalho de
# core/diagnostico/espaco_disco.py para o racional completo desse
# padrão): não há progresso nem resultado para acompanhar, só abre ou
# não abre.
#
# Console MMC (.msc) x Painel de Controle (.cpl) x executável comum:
# cada tipo precisa de um "lançador" diferente para funcionar de
# forma confiável a partir de subprocess (sem depender de resolução
# de associação de arquivo, que cmd.exe/Explorer fazem mas
# subprocess.Popen não faz sozinho):
#   - .msc  -> ["mmc.exe", "arquivo.msc"]  (console de gerenciamento)
#   - .cpl  -> ["control.exe", "arquivo.cpl"]  (applet do Painel de
#     Controle) — Central de Rede usa a forma com /name, também
#     documentada pela Microsoft.
#   - demais -> executável direto (já presentes no PATH do Windows).
# Todas resolvidas via PATH do sistema — nenhum caminho fixo em disco.
#
# gpedit.msc (Editor de Diretiva de Grupo) não existe nas edições
# Home do Windows — quando ausente, o próprio mmc.exe mostra seu
# aviso nativo de "arquivo não encontrado" numa janela própria; não é
# tratado aqui como caso especial, pelo mesmo motivo de "não
# implementar lógica própria" citado acima.
#
# CATÁLOGO ÚNICO (FERRAMENTAS): mesma ideia de fonte única de verdade
# já usada em utils/tasks.py para as tarefas de lote — descreve cada
# ferramenta (chave, categoria de agrupamento, ícone, título, comando)
# uma única vez. Tanto abrir_ferramenta() quanto a tela (ver
# ui/ferramentas_view.py) leem deste mesmo catálogo, sem duplicar a
# lista em dois lugares.
# ==========================================================

import subprocess
from collections import namedtuple

from utils.helpers import agora
from utils.logger import log

FerramentaDefinicao = namedtuple(
    "FerramentaDefinicao", ["chave", "categoria", "icone", "titulo", "comando"]
)

FERRAMENTAS = [
    # ---------------- Sistema ----------------
    FerramentaDefinicao(
        "gerenciador_dispositivos", "Sistema", "\U0001F5A5",
        "Gerenciador de Dispositivos", ["mmc.exe", "devmgmt.msc"],
    ),
    FerramentaDefinicao(
        "gerenciamento_disco", "Sistema", "\U0001F4BE",
        "Gerenciamento de Disco", ["mmc.exe", "diskmgmt.msc"],
    ),
    FerramentaDefinicao(
        "servicos", "Sistema", "\u2699",
        "Serviços", ["mmc.exe", "services.msc"],
    ),
    FerramentaDefinicao(
        "agendador_tarefas", "Sistema", "\u23F0",
        "Agendador de Tarefas", ["mmc.exe", "taskschd.msc"],
    ),
    # ---------------- Diagnóstico ----------------
    FerramentaDefinicao(
        "visualizador_eventos", "Diagnóstico", "\U0001F4CB",
        "Visualizador de Eventos", ["mmc.exe", "eventvwr.msc"],
    ),
    FerramentaDefinicao(
        "monitor_recursos", "Diagnóstico", "\U0001F4CA",
        "Monitor de Recursos", ["resmon.exe"],
    ),
    FerramentaDefinicao(
        "monitor_desempenho", "Diagnóstico", "\U0001F4C8",
        "Monitor de Desempenho", ["perfmon.exe"],
    ),
    FerramentaDefinicao(
        "informacoes_sistema", "Diagnóstico", "\u2139",
        "Informações do Sistema", ["msinfo32.exe"],
    ),
    # ---------------- Configuração ----------------
    FerramentaDefinicao(
        "msconfig", "Configuração", "\U0001F527",
        "Configuração do Sistema (MSConfig)", ["msconfig.exe"],
    ),
    FerramentaDefinicao(
        "editor_registro", "Configuração", "\U0001F4DD",
        "Editor do Registro", ["regedit.exe"],
    ),
    FerramentaDefinicao(
        "firewall", "Configuração", "\U0001F6E1",
        "Firewall do Windows", ["control.exe", "firewall.cpl"],
    ),
    FerramentaDefinicao(
        "editor_diretiva_grupo", "Configuração", "\U0001F4D8",
        "Editor de Diretiva de Grupo", ["mmc.exe", "gpedit.msc"],
    ),
    # ---------------- Rede ----------------
    FerramentaDefinicao(
        "conexoes_rede", "Rede", "\U0001F50C",
        "Conexões de Rede", ["control.exe", "ncpa.cpl"],
    ),
    FerramentaDefinicao(
        "central_rede", "Rede", "\U0001F4E1",
        "Central de Rede e Compartilhamento",
        ["control.exe", "/name", "Microsoft.NetworkAndSharingCenter"],
    ),
]

_POR_CHAVE = {f.chave: f for f in FERRAMENTAS}


def ferramentas_por_categoria():
    """Agrupa o catálogo por categoria de agrupamento (Sistema,
    Diagnóstico, Configuração, Rede), preservando a ordem de
    aparição em FERRAMENTAS. Usado por ui/ferramentas_view.py para
    montar os cards — mesmo papel que
    app.consultas_rapidas_para_dashboard() cumpre para o Dashboard."""
    grupos = []
    vistos = set()
    for f in FERRAMENTAS:
        if f.categoria not in vistos:
            vistos.add(f.categoria)
            grupos.append((f.categoria, [x for x in FERRAMENTAS if x.categoria == f.categoria]))
    return grupos


def abrir_ferramenta(chave: str) -> dict:
    """Abre a ferramenta nativa do Windows identificada por `chave`
    (ver FERRAMENTAS). Retorna {"sucesso": bool, "mensagem": str} —
    nunca lança exceção."""
    definicao = _POR_CHAVE.get(chave)
    if definicao is None:
        return {"sucesso": False, "mensagem": f"Ferramenta desconhecida: {chave}"}

    try:
        subprocess.Popen(definicao.comando)
    except FileNotFoundError:
        log(f"[FERRAMENTAS] ERRO - {chave} nao encontrada - {agora()}")
        return {
            "sucesso": False,
            "mensagem": f"{definicao.titulo} não foi encontrado(a) neste computador.",
        }
    except Exception as e:
        log(f"[FERRAMENTAS] ERRO - {chave} - {e} - {agora()}")
        return {"sucesso": False, "mensagem": f"Não foi possível abrir {definicao.titulo}: {e}"}

    log(f"[FERRAMENTAS] {chave} aberta em {agora()}")
    return {
        "sucesso": True,
        "mensagem": f"{definicao.titulo} foi aberto(a) em uma nova janela do Windows.",
    }