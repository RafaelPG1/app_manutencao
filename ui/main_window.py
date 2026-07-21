# ==========================================================
# Arquivo: ui/main_window.py
# Responsabilidade: Construção da interface principal — janela,
# estilo do tema escuro, navegação por sidebar (Dashboard +
# categorias) e orquestração da execução em lote das tarefas
# selecionadas, delegando o trabalho real aos módulos em core/.
#
# A execução em lote é DONA de si mesma através do ExecutionManager
# (core/execution/execution_manager.py): ela roda independente da
# tela atual, e a navegação pela sidebar fica livre mesmo com uma
# execução em andamento. A tela "Execução" e o indicador no topo da
# janela apenas OBSERVAM o estado do ExecutionManager.
#
# Cada tarefa agora recebe um único TaskReporter (via
# execution_manager.obter_reporter), em vez de uma lista solta de
# callbacks — nenhuma lógica de negócio das tarefas foi alterada,
# apenas a forma como elas relatam progresso e como a UI observa isso.
#
# FECHAMENTO DO APLICATIVO: todo caminho que destrói `self.root` (o X
# da janela / Alt+F4 / fechar pela barra de tarefas — que no Tkinter
# são o mesmo protocolo WM_DELETE_WINDOW — e também o caminho de saída
# antecipada por falta de privilégio de admin em `_inicializar()`)
# passa exclusivamente por `_ao_fechar_app()`, que garante
# `terminal.encerrar()` antes de `self.root.destroy()`. Isso vale
# igualmente rodando via VS Code, `python main.py` ou o .exe do
# PyInstaller, porque os três cenários executam o mesmo `main.py` e o
# mesmo `mainloop()` — o que muda é só como o processo Python é
# lançado, não os caminhos que destroem a janela.
# ==========================================================

import math
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import APP_TITULO, APP_GEOMETRIA, APP_TAM_MINIMO
from utils.constants import (
    CATEGORIAS, CATEGORIAS_EM_BREVE,
    COR_BG, COR_BG_ELEVADO, COR_BG_CARD, COR_BG_CARD_HOVER, COR_BORDA,
    COR_TEXTO, COR_TEXTO_FRACO, COR_ACCENT, COR_ACCENT_HOVER,
    COR_OK, COR_AVISO, COR_ERRO,
)
from utils.tasks import TAREFAS, tarefas_por_categoria
from utils.helpers import agora
from utils.logger import LOGFILE, log, log_init

from core.shared.admin import is_admin, relaunch_as_admin
from core.shared.disk_info import detectar_tipo_disco
from core.shared.terminal_manager import terminal
from core.dashboard.system_info import obter_espaco_disco
from core.manutencao.dism import executar_dism, executar_dism_component_cleanup
from core.manutencao.sfc import executar_sfc
from core.manutencao.reset_rede import resetar_rede
from core.manutencao.trim_ssd import otimizar_ssd
from core.manutencao.windows_update_diagnostico import obter_diagnostico_windows_update
from core.limpeza.dns import limpar_dns
from core.limpeza.cleanup import limpar_temporarios
from core.limpeza.recyclebin import esvaziar_lixeira
from core.limpeza.update_cache import limpar_cache_windows_update
from core.limpeza.thumbnail_cache import limpar_cache_miniaturas
from core.limpeza.windows_old import limpar_windows_old
from core.limpeza.delivery_optimization import limpar_delivery_optimization
from core.limpeza.logs_antigos import limpar_logs_antigos
from core.limpeza.cache_sistema import limpar_cache_adicional_sistema
from core.limpeza.analise_espaco import calcular_espaco_recuperavel
from core.diagnostico.chkdsk import agendar_chkdsk
from core.diagnostico.dism_diagnostico import executar_dism_checkhealth, executar_dism_scanhealth
from core.diagnostico.smart_disco import obter_saude_discos
from core.diagnostico.espaco_disco import analisar_espaco_pastas
from core.diagnostico.eventos_criticos import obter_eventos_criticos
from core.recuperacao.restore_point import criar_ponto_restauracao
from core.recuperacao.system_restore_wizard import abrir_restaurar_sistema
from core.recuperacao.startup_repair import iniciar_reparo_inicializacao
from core.recuperacao.driver_backup import fazer_backup_drivers
from core.recuperacao.relatorios_powercfg import (
    gerar_relatorio_bateria, gerar_relatorio_energia, gerar_relatorio_eficiencia,
)
from core.laboratorio.rapido import teste_rapido
from core.laboratorio.medio import teste_medio
from core.laboratorio.longo import teste_longo
from core.laboratorio.logs import teste_muitos_logs
from core.laboratorio.indeterminado import teste_indeterminado
from core.laboratorio.erro import teste_erro
from core.laboratorio.aviso import teste_aviso
from core.laboratorio.reinicializacao import teste_reinicializacao
from core.laboratorio.aleatorio import teste_aleatorio
from core.execution.execution_manager import ExecutionManager

from ui import dialogs
from ui.sidebar import Sidebar
from ui.dashboard import Dashboard
from ui.task_view import TaskView
from ui.execution_panel import ExecutionPanel
from ui.sistema_view import SistemaView
from ui.historico_view import HistoricoView
from ui.resultado_window import exibir_resultado


class ManutencaoApp:
    # Reexpõe a lista de tarefas (mesma origem usada pela interface original)
    TAREFAS = TAREFAS

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITULO)
        self.root.geometry(APP_GEOMETRIA)
        self.root.minsize(*APP_TAM_MINIMO)
        self.root.configure(bg=COR_BG)

        # Único ponto de entrada para QUALQUER fechamento da janela: X,
        # Alt+F4 e "Fechar" na barra de tarefas disparam todos o mesmo
        # protocolo WM_DELETE_WINDOW no Tkinter. Sem este registro, o
        # Tkinter destrói a janela direto, sem chamar nenhum código do
        # app. Ver `_ao_fechar_app` para a sequência garantida.
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar_app)

        self.disco_tipo = "detectando..."
        self.categoria_atual = "dashboard"
        self.vars_tarefas = {t.chave: tk.BooleanVar(value=False) for t in self.TAREFAS}

        # Controlador global da execução — vive durante toda a vida do
        # app, independente de qual tela está visível.
        self.execution_manager = ExecutionManager()
        self.execution_manager.adicionar_listener(self._ao_evento_execucao_global)
        self._listener_tela_execucao = None  # listener ativo só enquanto a tela "Execução" está aberta
        # Flag de UI (não faz parte do estado do ExecutionManager): diz se a
        # próxima abertura da tela "Execução" é o INÍCIO de uma execução nova
        # ou apenas o usuário revisitando uma execução já em andamento/finalizada
        # — usado só para decidir se o console abre expandido automaticamente.
        self._nova_execucao_iniciada = False

        self._configurar_estilo()
        self._montar_ui()
        self.root.after(150, self._inicializar)

    # -------------------- ESTILO --------------------
    def _configurar_estilo(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background=COR_BG)
        style.configure("Sidebar.TFrame", background=COR_BG_ELEVADO)
        style.configure("Card.TFrame", background=COR_BG_CARD)
        style.configure("TLabel", background=COR_BG, foreground=COR_TEXTO, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=COR_BG_CARD, foreground=COR_TEXTO, font=("Segoe UI", 10, "bold"))
        style.configure("CardDesc.TLabel", background=COR_BG_CARD, foreground=COR_TEXTO_FRACO, font=("Segoe UI", 8))
        style.configure("StatIcone.TLabel", background=COR_BG_CARD, foreground=COR_TEXTO, font=("Segoe UI", 16))
        style.configure("Titulo.TLabel", background=COR_BG, foreground=COR_TEXTO, font=("Segoe UI", 18, "bold"))
        style.configure("TituloSecao.TLabel", background=COR_BG, foreground=COR_TEXTO, font=("Segoe UI", 15, "bold"))
        style.configure("Badge.TLabel", background=COR_ACCENT, foreground="#ffffff",
                         font=("Segoe UI", 9, "bold"), padding=(10, 4))
        style.configure("Status.TLabel", background=COR_BG, foreground=COR_TEXTO_FRACO, font=("Segoe UI", 9))

        style.configure("TCheckbutton", background=COR_BG_CARD, foreground=COR_TEXTO,
                         font=("Segoe UI", 10), focuscolor=COR_BG_CARD)
        style.map("TCheckbutton", background=[("active", COR_BG_CARD)])

        style.configure("Accent.TButton", background=COR_ACCENT, foreground="#ffffff",
                         font=("Segoe UI", 11, "bold"), padding=(14, 10), borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", COR_ACCENT_HOVER), ("disabled", "#3a3d4d")],
                  foreground=[("disabled", "#8c92a8")])

        style.configure("Secundario.TButton", background=COR_BG_CARD, foreground=COR_TEXTO,
                         font=("Segoe UI", 9), padding=(10, 6), borderwidth=1)
        style.map("Secundario.TButton",
                  background=[("active", COR_BG_CARD_HOVER)])

        style.configure("Horizontal.TProgressbar", background=COR_ACCENT,
                         troughcolor=COR_BG_CARD, borderwidth=0)

    # -------------------- UI --------------------
    def _montar_ui(self):
        # ---------- Barra superior ----------
        topo = ttk.Frame(self.root, padding=(20, 14, 20, 10))
        topo.pack(fill="x")
        self.lbl_titulo_topo = ttk.Label(topo, text="Dashboard", style="Titulo.TLabel")
        self.lbl_titulo_topo.pack(side="left")

        sep = tk.Frame(self.root, bg=COR_BORDA, height=1)
        sep.pack(fill="x")

        # ---------- Corpo: sidebar + conteúdo ----------
        corpo = tk.Frame(self.root, bg=COR_BG)
        corpo.pack(fill="both", expand=True)

        self.sidebar = Sidebar(corpo, ao_selecionar=self.navegar_para)
        self.sidebar.pack(side="left", fill="y")

        sep_v = tk.Frame(corpo, bg=COR_BORDA, width=1)
        sep_v.pack(side="left", fill="y")

        self.content = tk.Frame(corpo, bg=COR_BG)
        self.content.pack(side="left", fill="both", expand=True)
        self._content_padding = dict(padx=24, pady=20)

        # ---------- Rodapé (status) ----------
        rodape = ttk.Frame(self.root, padding=(20, 8, 20, 12))
        rodape.pack(fill="x")
        self.lbl_status = ttk.Label(rodape, text="", style="Status.TLabel")
        self.lbl_status.pack(side="right")

        # painel de execução: só existe enquanto a tela "Execução" está aberta
        self.execution_panel = None

        self.navegar_para("dashboard")

    # -------------------- Navegação --------------------
    def _limpar_conteudo(self):
        # Se a tela "Execução" estava aberta, desinscreve o listener
        # específico dela ANTES de destruir os widgets — evita que um
        # evento chegue depois e tente atualizar um painel morto.
        if self._listener_tela_execucao is not None:
            self.execution_manager.remover_listener(self._listener_tela_execucao)
            self._listener_tela_execucao = None
        self.execution_panel = None

        for w in self.content.winfo_children():
            w.destroy()

    def navegar_para(self, categoria: str):
        # A navegação é sempre livre, mesmo com uma execução em lote em
        # andamento — a execução roda no ExecutionManager, independente
        # da tela exibida (ver core/execution/execution_manager.py).
        # Iniciar uma NOVA execução continua bloqueado (ver
        # executar_selecionadas).
        self.categoria_atual = categoria
        if categoria in self.sidebar.botoes:
            self.sidebar.definir_ativo(categoria)
        self._limpar_conteudo()

        # O texto de tarefa atual (ex.: "[1/1] Verificar arquivos do
        # sistema") é exclusivo da tela "Execução". Em qualquer outra
        # tela, a barra inferior volta ao texto padrão — ao entrar em
        # "Execução", _mostrar_tela_execucao() define o texto certo a
        # partir do snapshot do ExecutionManager.
        if categoria != "execucao":
            self.set_status("")

        wrapper = ttk.Frame(self.content, padding=(24, 20, 24, 20))
        wrapper.pack(fill="both", expand=True)

        if categoria == "dashboard":
            self.lbl_titulo_topo.config(text="Dashboard")
            self.dashboard = Dashboard(wrapper, self)
            self.dashboard.pack(fill="both", expand=True)
            self.dashboard.atualizar_disco(self.disco_tipo)
            self._atualizar_espaco_dashboard()
        elif categoria == "execucao":
            self.lbl_titulo_topo.config(text="Execução")
            self._mostrar_tela_execucao(wrapper)
        elif categoria == "sistema":
            self.lbl_titulo_topo.config(text="Sistema")
            SistemaView(wrapper, self).pack(fill="both", expand=True)
        elif categoria == "historico":
            self.lbl_titulo_topo.config(text="Histórico")
            HistoricoView(wrapper, self).pack(fill="both", expand=True)
        elif categoria in CATEGORIAS_EM_BREVE:
            meta = next(c for c in CATEGORIAS if c[0] == categoria)
            self.lbl_titulo_topo.config(text=meta[2])
            TaskView(wrapper, self, categoria, []).pack(fill="both", expand=True)
        else:
            meta = next(c for c in CATEGORIAS if c[0] == categoria)
            self.lbl_titulo_topo.config(text=meta[2])
            tarefas = tarefas_por_categoria(categoria)
            # As "consultas rápidas" (ações instantâneas) que antes
            # apareciam aqui foram centralizadas no Dashboard (ver
            # ui/dashboard.py e consultas_rapidas_para_dashboard) —
            # não são mais passadas para a TaskView de cada categoria,
            # para não ficarem duplicadas em dois lugares.
            TaskView(wrapper, self, categoria, tarefas).pack(fill="both", expand=True)

    def _mostrar_tela_execucao(self, wrapper):
        """Cria a tela 'Execução' como uma VIEW que observa o
        ExecutionManager: popula-se com o estado atual (obter_snapshot)
        e passa a receber eventos incrementais enquanto estiver aberta.
        Pode ser aberta a qualquer momento — inclusive com a execução
        já em andamento há tempo, ou já finalizada."""
        painel = ExecutionPanel(wrapper)
        painel.pack(fill="both", expand=True)
        self.execution_panel = painel

        snapshot = self.execution_manager.obter_snapshot()
        painel.exibir_estado(snapshot)
        self._nova_execucao_iniciada = False
        self.set_status(snapshot["tarefa_atual_texto"])

        def listener(evento, dados):
            self.root.after(0, lambda: self._aplicar_evento_na_tela(painel, evento, dados))

        self._listener_tela_execucao = listener
        self.execution_manager.adicionar_listener(listener)

    def _aplicar_evento_na_tela(self, painel, evento, dados):
        # A tela pode ter sido trocada entre o evento ser emitido (em
        # segundo plano) e este callback rodar na thread principal —
        # nesse caso o painel já foi destruído; ignora silenciosamente.
        if not painel.winfo_exists():
            return
        if evento == "progresso":
            painel.definir_progresso(dados["concluidas"], dados["total"])
        elif evento == "estado_tarefa":
            painel.marcar_estado(dados["chave"], dados["estado"])
        elif evento == "tarefa_atual":
            painel.definir_tarefa_atual(dados["texto"])
            self.set_status(dados["texto"])
        elif evento == "capacidades":
            painel.definir_capacidades(dados["capacidades"])
        elif evento == "percentual":
            painel.definir_percentual_tarefa(dados["valor"])
        elif evento == "mensagem":
            painel.definir_ultima_mensagem(dados["texto"])
        elif evento == "finalizado":
            painel.finalizar()

    # -------------------- Indicador global de execução --------------------
    def _ao_evento_execucao_global(self, evento, dados):
        """Listener permanente (nunca removido) — só cuida do indicador
        visível em qualquer tela e da limpeza de seleção ao final. Não
        toca em widgets de nenhuma tela específica, então é seguro
        mantê-lo vivo o tempo todo."""
        if evento in ("iniciado", "finalizado"):
            self.root.after(0, self._atualizar_indicador_execucao)
        if evento == "finalizado":
            self.root.after(0, self._limpar_selecoes_apos_execucao)

    def _limpar_selecoes_apos_execucao(self):
        """Ao final de uma execução em lote (com sucesso ou não), todas
        as tarefas que estavam marcadas voltam a ficar desmarcadas — a
        próxima seleção começa sempre do zero. Isso não afeta o
        ExecutionManager nem a execução em si, apenas o estado das
        checkboxes na interface."""
        for var in self.vars_tarefas.values():
            var.set(False)

    def _atualizar_indicador_execucao(self):
        if self.execution_manager.esta_rodando():
            self.sidebar.mostrar_card_execucao()
        else:
            self.sidebar.ocultar_card_execucao()
            self.set_status("")

    # -------------------- Inicialização --------------------
    def _inicializar(self):
        if not is_admin():
            dialogs.avisar_permissao_admin()
            relaunch_as_admin()
            # Mesmo caminho de fechamento usado pelo X da janela — ver
            # `_ao_fechar_app`. Antes chamava self.root.destroy() direto,
            # o que pulava terminal.encerrar() (inofensivo aqui, já que o
            # CMD gerenciado normalmente nem chegou a ser criado neste
            # ponto, mas passa a ser consistente com todo o resto).
            self._ao_fechar_app()
            return

        log_init()
        threading.Thread(target=self._detectar_disco_thread, daemon=True).start()

    def _detectar_disco_thread(self):
        tipo = detectar_tipo_disco()
        self.disco_tipo = tipo
        log(f"[INFO] Tipo de disco detectado: {tipo}")
        if self.categoria_atual == "dashboard" and hasattr(self, "dashboard"):
            self.root.after(0, lambda: self.dashboard.atualizar_disco(tipo))
        self.root.after(0, lambda: self.set_status(""))

    # -------------------- Encerramento do aplicativo --------------------
    def _ao_fechar_app(self):
        """Callback ÚNICO para todo fechamento do aplicativo.

        É chamado tanto pelo protocolo WM_DELETE_WINDOW do Tkinter
        (registrado no __init__: cobre X da janela, Alt+F4 e fechar
        pela barra de tarefas — as três ações disparam o mesmo
        protocolo) quanto pelo caminho de saída antecipada em
        `_inicializar()` quando falta privilégio de admin.

        Garante a sequência: terminal.encerrar() (fecha exclusivamente
        o CMD gerenciado pelo TerminalManager, se houver um vivo, e
        libera seus handles) e só DEPOIS self.root.destroy() (o que
        faz `root.mainloop()` retornar e o processo terminar
        normalmente). Isso vale igual rodando pelo VS Code, por
        `python main.py` ou pelo .exe do PyInstaller, porque os três
        cenários executam o mesmo `main.py`/`mainloop()` — nenhuma
        lógica aqui depende de como o processo foi lançado."""
        terminal.encerrar()
        self.root.destroy()

    # -------------------- Utilitários de UI --------------------
    def set_status(self, texto: str):
        self.lbl_status.config(text=texto)

    def abrir_pasta_log(self):
        pasta = os.path.dirname(LOGFILE)
        try:
            os.startfile(pasta)
        except Exception as e:
            dialogs.informar_local_log(LOGFILE, e)

    # -------------------- Espaço em disco --------------------
    @staticmethod
    def _fmt_gb_br(valor: float, casas: int = 1) -> str:
        """Formata um valor em GB com casas decimais fixas, usando
        vírgula como separador (padrão pt-BR) e TRUNCANDO (não
        arredondando) a casa decimal extra.

        O Windows Explorer trunca o valor de espaço em disco ao
        exibi-lo em GB (descarta as casas decimais além da exibida,
        sem arredondar para cima). Usar round()/format ":.1f" comum
        faz o app arredondar (ex.: 49,55 -> 49,6) enquanto o Explorer
        mostra 49,5 para o mesmo valor. Truncar aqui replica o
        comportamento do Explorer e elimina essa divergência.
        """
        fator = 10 ** casas
        valor_truncado = math.floor(valor * fator) / fator
        return f"{valor_truncado:.{casas}f}".replace(".", ",")

    def _formatar_espaco_unidade(self, item: dict):
        """Formata o texto/cor do card 'Espaço livre' do Dashboard a
        partir de um item retornado por obter_espaco_disco().

        Usa a mesma origem de dados e a mesma casa decimal exibida por
        'Ver espaço em disco', evitando divergência entre os dois."""
        if "erro" in item:
            return "Erro ao ler espaço", COR_ERRO
        livre = self._fmt_gb_br(item["livre_gb"])
        total = self._fmt_gb_br(item["total_gb"])
        pct = self._fmt_gb_br(item["pct_usado"])
        return (
            f"{livre} GB livres de {total} GB "
            f"({pct}% usado)",
            None,
        )

    def _atualizar_espaco_dashboard(self):
        """Consulta o espaço em disco automaticamente sempre que o
        Dashboard é exibido, sem exigir clique do usuário."""
        if not hasattr(self, "dashboard"):
            return
        self.dashboard.atualizar_espaco("Consultando...")
        threading.Thread(target=self._consultar_espaco_thread, daemon=True).start()

    def _consultar_espaco_thread(self):
        itens = obter_espaco_disco()
        self.root.after(0, lambda: self._aplicar_espaco_dashboard(itens))

    def _aplicar_espaco_dashboard(self, itens):
        # Evita atualizar um card que já foi destruído (usuário navegou
        # para outra categoria antes da consulta terminar).
        if self.categoria_atual != "dashboard" or not hasattr(self, "dashboard"):
            return
        for item in itens:
            if item.get("unidade", "").upper().startswith("C"):
                texto, cor = self._formatar_espaco_unidade(item)
                self.dashboard.atualizar_espaco(texto, cor=cor)
                break

    # -------------------- Espaço em disco (ação instantânea) --------------------
    def ver_espaco_disco(self):
        itens = obter_espaco_disco()
        if hasattr(self, "dashboard") and self.categoria_atual == "dashboard":
            self._aplicar_espaco_dashboard(itens)

        # O painel de Execução não tem mais um console interno onde
        # escrever isto — o resultado sempre é mostrado numa caixa de
        # mensagem simples, independente da tela atual.
        linhas = []
        for item in itens:
            if "erro" in item:
                linhas.append(f"{item['unidade']}  [erro ao ler: {item['erro']}]")
            else:
                total_fmt = self._fmt_gb_br(item['total_gb'])
                usado_fmt = self._fmt_gb_br(item['usado_gb'])
                pct_fmt = self._fmt_gb_br(item['pct_usado'])
                livre_fmt = self._fmt_gb_br(item['livre_gb'])
                linhas.append(
                    f"{item['unidade']}  Total: {total_fmt} GB   "
                    f"Usado: {usado_fmt} GB ({pct_fmt}%)   "
                    f"Livre: {livre_fmt} GB"
                )
        texto = "\n".join(linhas)
        messagebox.showinfo(
            f"Espaço em disco ({agora()})", texto or "Nenhuma unidade encontrada."
        )

    # -------------------- Ações instantâneas por categoria --------------------
    def _acoes_instantaneas_para(self, categoria: str):
        """Lista de ações instantâneas (ver ui/task_view.py) para a
        categoria informada, ou None se ela não tiver nenhuma."""
        if categoria == "manutencao":
            return [
                {"icone": "\U0001F5A5", "titulo": "Diagnóstico do Windows Update", "comando": self.diagnostico_windows_update},
            ]
        if categoria == "limpeza":
            return [
                {"icone": "\U0001F4CA", "titulo": "Analisar espaço recuperável", "comando": self.analisar_espaco_recuperavel},
            ]
        if categoria == "diagnostico":
            return [
                {"icone": "\U0001FA7A", "titulo": "Saúde SMART dos discos", "comando": self.ver_saude_discos},
                {"icone": "\U0001F4CA", "titulo": "Espaço por pasta (C:)", "comando": self.ver_espaco_por_pasta},
                {"icone": "\u26A0", "titulo": "Eventos críticos recentes", "comando": self.ver_eventos_criticos},
            ]
        if categoria == "recuperacao":
            return [
                {"icone": "\u23EA", "titulo": "Restaurar o Sistema", "comando": self.restaurar_sistema},
                {"icone": "\U0001F6E0", "titulo": "Reparo de Inicialização", "comando": self.reparo_inicializacao},
                {"icone": "\U0001F4E6", "titulo": "Backup dos drivers", "comando": self.backup_drivers},
                {"icone": "\U0001F50B", "titulo": "Relatório de bateria", "comando": self.relatorio_bateria},
                {"icone": "\u26A1", "titulo": "Relatório de energia", "comando": self.relatorio_energia},
                {"icone": "\U0001F4C8", "titulo": "Relatório de eficiência", "comando": self.relatorio_eficiencia},
            ]
        return None

    def consultas_rapidas_para_dashboard(self):
        """Agrupa, por categoria de origem, todas as consultas/ações
        instantâneas que antes apareciam dentro da tela de cada
        categoria (ver `_acoes_instantaneas_para` — continua sendo a
        única fonte de verdade dessa lista). O Dashboard passou a
        concentrar essas consultas rápidas (ver ui/dashboard.py); elas
        não aparecem mais dentro de Manutenção/Limpeza/Diagnóstico/
        Recuperação, evitando duplicação.

        Retorna uma lista de (titulo_categoria, acoes) — apenas para as
        categorias que de fato têm alguma ação instantânea."""
        grupos = []
        for chave, titulo in (
            ("manutencao", "Manutenção"),
            ("limpeza", "Limpeza"),
            ("diagnostico", "Diagnóstico"),
            ("recuperacao", "Recuperação"),
        ):
            acoes = self._acoes_instantaneas_para(chave)
            if acoes:
                grupos.append((titulo, acoes))
        return grupos

    # -------------------- Manutenção: diagnóstico do Windows Update (Fase 5) --------------------
    def diagnostico_windows_update(self):
        self.set_status("Consultando serviços do Windows Update...")
        threading.Thread(target=self._diagnostico_wu_thread, daemon=True).start()

    def _diagnostico_wu_thread(self):
        info = obter_diagnostico_windows_update()
        self.root.after(0, lambda: self._exibir_diagnostico_wu(info))

    def _exibir_diagnostico_wu(self, info: dict):
        self.set_status("")
        if "erro" in info:
            exibir_resultado(self.root, "Diagnóstico do Windows Update", f"Erro: {info['erro']}")
            return

        linhas = []
        linhas.append("SERVIÇOS NECESSÁRIOS")
        linhas.append("-" * 40)
        for s in info["servicos"]:
            marca = "  [ALERTA - desabilitado]" if s["problema"] else ""
            linhas.append(f"{s['rotulo']:<45} {s['status']:<12} (início: {s['tipo_inicializacao']}){marca}")

        linhas.append("")
        linhas.append("CACHE DO WINDOWS UPDATE")
        linhas.append("-" * 40)
        if info["cache_mb"] is not None:
            linhas.append(f"Tamanho atual: {info['cache_mb']:.1f} MB".replace(".", ","))
        else:
            linhas.append("Não foi possível determinar o tamanho do cache.")

        linhas.append("")
        if info["saudavel"]:
            linhas.append("RESULTADO: o Windows Update aparenta estar saudável.")
        else:
            linhas.append(
                "RESULTADO: um ou mais serviços necessários ao Windows Update estão "
                "DESABILITADOS — isso normalmente impede o funcionamento do Windows Update."
            )

        exibir_resultado(self.root, f"Diagnóstico do Windows Update ({agora()})", "\n".join(linhas))

    # -------------------- Limpeza: análise de espaço recuperável (Fase 6) --------------------
    def analisar_espaco_recuperavel(self):
        self.set_status("Calculando espaço recuperável... (pode levar até 1 minuto)")
        threading.Thread(target=self._analise_espaco_thread, daemon=True).start()

    def _analise_espaco_thread(self):
        resultado = calcular_espaco_recuperavel()
        self.root.after(0, lambda: self._exibir_analise_espaco(resultado))

    def _exibir_analise_espaco(self, resultado: dict):
        self.set_status("")

        def _gb(valor):
            return f"{valor:.1f} GB".replace(".", ",")

        texto = (
            f"Arquivos Temporários:\n{_gb(resultado['temp_gb'])}\n\n"
            f"Delivery Optimization:\n{_gb(resultado['delivery_optimization_gb'])}\n\n"
            f"Windows.old:\n{_gb(resultado['windows_old_gb'])}\n\n"
            f"Total Recuperável:\n{_gb(resultado['total_gb'])}\n\n"
            "Para liberar esse espaço, marque as tarefas correspondentes na lista "
            "abaixo e clique em \"Executar selecionadas\"."
        )
        exibir_resultado(self.root, f"Espaço recuperável ({agora()})", texto, largura=420, altura=420)

    # -------------------- Diagnóstico: SMART dos discos (ação instantânea) --------------------
    def ver_saude_discos(self):
        self.set_status("Consultando saúde dos discos...")
        threading.Thread(target=self._consultar_smart_thread, daemon=True).start()

    def _consultar_smart_thread(self):
        discos = obter_saude_discos()
        self.root.after(0, lambda: self._exibir_resultado_smart(discos))

    def _exibir_resultado_smart(self, discos: list):
        self.set_status("")
        if discos and "erro" in discos[0]:
            exibir_resultado(self.root, "Saúde SMART dos discos", f"Erro: {discos[0]['erro']}")
            return

        blocos = []
        for d in discos:
            linhas = [
                f"Modelo:              {d['modelo']}",
                f"Tipo:                {d['tipo']}",
                f"Status SMART:        {d['status_smart']}",
            ]
            if d.get("status_operacional"):
                linhas.append(f"Status operacional:  {d['status_operacional']}")
            if d.get("tamanho_gb") is not None:
                linhas.append(f"Tamanho:             {d['tamanho_gb']} GB")
            if d.get("temperatura_c") is not None:
                linhas.append(f"Temperatura:         {d['temperatura_c']} °C")
            if d.get("horas_uso") is not None:
                linhas.append(f"Horas de uso:        {d['horas_uso']}")
            if d.get("desgaste_pct") is not None:
                linhas.append(f"Vida útil usada:     {d['desgaste_pct']}%")
            if d.get("erros_leitura") is not None:
                linhas.append(f"Erros de leitura:    {d['erros_leitura']}")
            if d.get("erros_escrita") is not None:
                linhas.append(f"Erros de escrita:    {d['erros_escrita']}")
            if d.get("serial") and d["serial"] != "Não disponível":
                linhas.append(f"Número de série:     {d['serial']}")
            if d["status_smart"].lower() not in ("healthy", "saudável", ""):
                linhas.append("")
                linhas.append("[ALERTA] Este disco não está reportando status saudável.")
            blocos.append("\n".join(linhas))

        texto = f"\n{'-'*50}\n\n".join(blocos) if blocos else "Nenhum disco encontrado."
        exibir_resultado(self.root, f"Saúde SMART dos discos ({agora()})", texto)

    # -------------------- Diagnóstico: espaço por pasta (ação instantânea) --------------------
    def ver_espaco_por_pasta(self):
        self.set_status("Analisando espaço em disco... (pode levar até 1 minuto)")
        threading.Thread(target=self._analisar_espaco_pastas_thread, daemon=True).start()

    def _analisar_espaco_pastas_thread(self):
        def callback(msg):
            self.root.after(0, lambda: self.set_status(msg))

        resultado = analisar_espaco_pastas("C:\\", callback_status=callback)
        self.root.after(0, lambda: self._exibir_resultado_espaco_pastas(resultado))

    def _exibir_resultado_espaco_pastas(self, resultado: dict):
        self.set_status("")
        if "erro" in resultado:
            exibir_resultado(self.root, "Espaço por pasta", f"Erro: {resultado['erro']}")
            return

        linhas = [f"Maiores pastas em {resultado['unidade']}\n"]
        for i, (nome, tamanho_bytes) in enumerate(resultado["itens"], start=1):
            tamanho_gb = tamanho_bytes / (1024 ** 3)
            linhas.append(f"{i:>2}. {nome:<40} {self._fmt_gb_br(tamanho_gb)} GB")
        if not resultado["itens"]:
            linhas.append("Nenhuma pasta encontrada.")
        exibir_resultado(self.root, f"Espaço por pasta ({agora()})", "\n".join(linhas))

    # -------------------- Diagnóstico: eventos críticos (ação instantânea) --------------------
    def ver_eventos_criticos(self):
        self.set_status("Consultando o Log de Eventos do Windows...")
        threading.Thread(target=self._consultar_eventos_thread, daemon=True).start()

    def _consultar_eventos_thread(self):
        resultado = obter_eventos_criticos()
        self.root.after(0, lambda: self._exibir_resultado_eventos(resultado))

    def _exibir_resultado_eventos(self, resultado: dict):
        self.set_status("")
        if "erro" in resultado:
            exibir_resultado(self.root, "Eventos críticos recentes", f"Erro: {resultado['erro']}")
            return

        eventos = resultado.get("eventos", [])
        dias = resultado.get("dias_janela", 7)
        if not eventos:
            texto = f"Nenhum evento Crítico ou de Erro encontrado nos últimos {dias} dias."
        else:
            blocos = []
            for e in eventos:
                blocos.append(
                    f"[{e['data']}] {e['nivel']}  —  {e['origem']} (ID {e['id_evento']})\n"
                    f"    {e['mensagem']}"
                )
            texto = f"Últimos {len(eventos)} evento(s) nos últimos {dias} dias:\n\n" + "\n\n".join(blocos)
        exibir_resultado(self.root, f"Eventos críticos recentes ({agora()})", texto, largura=760)

    # -------------------- Recuperação: ações instantâneas (Fase 3) --------------------
    def restaurar_sistema(self):
        resultado = abrir_restaurar_sistema()
        if resultado["sucesso"]:
            messagebox.showinfo("Restaurar o Sistema", resultado["mensagem"])
        else:
            messagebox.showerror("Restaurar o Sistema", resultado["mensagem"])

    def reparo_inicializacao(self):
        if not dialogs.confirmar_reparo_inicializacao():
            return
        resultado = iniciar_reparo_inicializacao()
        if not resultado["sucesso"]:
            messagebox.showerror("Reparo de Inicialização", resultado["mensagem"])
        # Em caso de sucesso, o computador reinicia em seguida — não há
        # necessidade (nem tempo útil) de mostrar mais nenhuma mensagem.

    def backup_drivers(self):
        pasta = filedialog.askdirectory(title="Escolha a pasta para salvar o backup dos drivers")
        if not pasta:
            return
        self.set_status("Fazendo backup dos drivers instalados...")
        threading.Thread(target=self._backup_drivers_thread, args=(pasta,), daemon=True).start()

    def _backup_drivers_thread(self, pasta: str):
        resultado = fazer_backup_drivers(pasta)
        self.root.after(0, lambda: self._exibir_resultado_simples("Backup dos drivers", resultado))

    def relatorio_bateria(self):
        self.set_status("Gerando relatório de bateria...")
        threading.Thread(target=self._relatorio_thread, args=(gerar_relatorio_bateria, "Relatório de bateria"), daemon=True).start()

    def relatorio_energia(self):
        self.set_status("Gerando relatório de energia... (leva cerca de 1 minuto)")
        threading.Thread(target=self._relatorio_thread, args=(gerar_relatorio_energia, "Relatório de energia"), daemon=True).start()

    def relatorio_eficiencia(self):
        self.set_status("Gerando relatório de eficiência (Sleep Study)...")
        threading.Thread(target=self._relatorio_thread, args=(gerar_relatorio_eficiencia, "Relatório de eficiência"), daemon=True).start()

    def _relatorio_thread(self, funcao_geradora, titulo: str):
        resultado = funcao_geradora()
        self.root.after(0, lambda: self._exibir_resultado_simples(titulo, resultado))

    def _exibir_resultado_simples(self, titulo: str, resultado: dict):
        """Mostra o resultado {"sucesso": bool, "mensagem": str} de uma
        ação instantânea da categoria Recuperação numa messagebox
        simples — as mensagens dessas ações são curtas (um parágrafo),
        diferente das consultas de Diagnóstico (SMART, eventos,
        espaço em disco), que usam ui/resultado_window.py por
        poderem ter várias linhas de dados."""
        self.set_status("")
        if resultado["sucesso"]:
            messagebox.showinfo(titulo, resultado["mensagem"])
        else:
            messagebox.showerror(titulo, resultado["mensagem"])

    # -------------------- Execução em lote --------------------
    def executar_selecionadas(self):
        # Regra: apenas UMA execução por vez. Verifica isso antes de
        # qualquer diálogo (não faz sentido perguntar sobre /r do CHKDSK
        # ou confirmar a execução se ela nem vai poder começar).
        if self.execution_manager.esta_rodando():
            dialogs.avisar_operacao_em_andamento()
            return

        selecionadas = [chave for chave, var in self.vars_tarefas.items() if var.get()]
        if not selecionadas:
            dialogs.avisar_nada_selecionado()
            return

        usar_r = False
        if "chkdsk" in selecionadas and self.disco_tipo.upper() == "HDD":
            usar_r = dialogs.perguntar_chkdsk_r()

        if not dialogs.confirmar_execucao(len(selecionadas)):
            return

        titulos_por_chave = {t.chave: t.titulo for t in self.TAREFAS}

        # Cada tarefa recebe um único TaskReporter — a função em core/
        # não conhece o ExecutionManager nem nenhum detalhe de UI, só
        # chama reporter.log()/progress()/message() (ver
        # core/execution/reporter.py).
        obter_reporter = self.execution_manager.obter_reporter
        mapa_funcoes = {
            "dism": lambda: executar_dism(obter_reporter("dism")),
            "sfc": lambda: executar_sfc(obter_reporter("sfc")),
            "reset_rede": lambda: resetar_rede(obter_reporter("reset_rede")),
            "trim_ssd": lambda: otimizar_ssd(obter_reporter("trim_ssd"), self.disco_tipo),
            "dism_cleanup": lambda: executar_dism_component_cleanup(obter_reporter("dism_cleanup")),
            "dns": lambda: limpar_dns(obter_reporter("dns")),
            "temp": lambda: limpar_temporarios(obter_reporter("temp")),
            "recycle": lambda: esvaziar_lixeira(obter_reporter("recycle")),
            "winupdate": lambda: limpar_cache_windows_update(obter_reporter("winupdate")),
            "thumbnail": lambda: limpar_cache_miniaturas(obter_reporter("thumbnail")),
            "windows_old": lambda: limpar_windows_old(obter_reporter("windows_old")),
            "delivery_optimization": lambda: limpar_delivery_optimization(obter_reporter("delivery_optimization")),
            "logs_antigos": lambda: limpar_logs_antigos(obter_reporter("logs_antigos")),
            "cache_sistema": lambda: limpar_cache_adicional_sistema(obter_reporter("cache_sistema")),
            "chkdsk": lambda: agendar_chkdsk(obter_reporter("chkdsk"), self.disco_tipo, usar_r),
            "dism_check": lambda: executar_dism_checkhealth(obter_reporter("dism_check")),
            "dism_scan": lambda: executar_dism_scanhealth(obter_reporter("dism_scan")),
            "restore_point": lambda: criar_ponto_restauracao(obter_reporter("restore_point")),
            "lab_rapido": lambda: teste_rapido(obter_reporter("lab_rapido")),
            "lab_medio": lambda: teste_medio(obter_reporter("lab_medio")),
            "lab_longo": lambda: teste_longo(obter_reporter("lab_longo")),
            "lab_logs": lambda: teste_muitos_logs(obter_reporter("lab_logs")),
            "lab_indeterminado": lambda: teste_indeterminado(obter_reporter("lab_indeterminado")),
            "lab_erro": lambda: teste_erro(obter_reporter("lab_erro")),
            "lab_aviso": lambda: teste_aviso(obter_reporter("lab_aviso")),
            "lab_reinicializacao": lambda: teste_reinicializacao(obter_reporter("lab_reinicializacao")),
            "lab_aleatorio": lambda: teste_aleatorio(obter_reporter("lab_aleatorio")),
        }

        iniciou = self.execution_manager.iniciar(titulos_por_chave, selecionadas, mapa_funcoes)
        if not iniciou:
            # Condição de corrida: outra execução começou entre a checagem
            # do início do método e agora. Mesma mensagem amigável.
            dialogs.avisar_operacao_em_andamento()
            return

        self._nova_execucao_iniciada = True
        self.navegar_para("execucao")