# ==========================================================
# Arquivo: utils/constants.py
# Responsabilidade: Constantes globais da aplicação
# (paleta de cores do tema escuro, categorias de navegação
# e definição das tarefas disponíveis na interface).
# ==========================================================

# ---------------- PALETA DE CORES (TEMA ESCURO) ----------------
COR_BG = "#12141c"
COR_BG_ELEVADO = "#171a24"          # sidebar / topbar — um tom acima do fundo
COR_BG_CARD = "#1b1e29"
COR_BG_CARD_HOVER = "#232735"
COR_BG_CARD_SELECIONADO = "#241f3d"  # card marcado (leve tingimento accent)
COR_BORDA = "#2a2e3d"
COR_TEXTO = "#e6e8f0"
COR_TEXTO_FRACO = "#8c92a8"
COR_ACCENT = "#7c5cff"
COR_ACCENT_HOVER = "#8f73ff"
COR_ACCENT_FRACO = "#2c2645"
COR_OK = "#37d67a"
COR_AVISO = "#ffb347"
COR_ERRO = "#ff5c72"
COR_CONSOLE_BG = "#0b0c12"
COR_CONSOLE_TXT = "#8fffb0"


# ---------------- CATEGORIAS DE NAVEGAÇÃO (SIDEBAR) ----------------
# Cada item: (chave, ícone, título, subtítulo curto)
# "dashboard" é tratado como a tela inicial, fora da lista de categorias
# de tarefas propriamente ditas.
CATEGORIAS = [
    ("dashboard",   "\U0001F3E0", "Dashboard",   "Visão geral do sistema"),
    ("manutencao",  "\U0001F6E0", "Manutenção",  "Reparos e integridade do Windows"),
    ("limpeza",     "\U0001F9F9", "Limpeza",     "Liberação de espaço e cache"),
    ("diagnostico", "\U0001FA7A", "Diagnóstico", "Verificação de disco e saúde"),
    ("recuperacao", "\U0001F6E1", "Recuperação", "Rede de segurança antes de reparos"),
    ("ferramentas", "\U0001F527", "Ferramentas", "Utilitários administrativos"),
    ("sistema",     "\U0001F5A5", "Sistema",     "Informações do computador"),
    ("historico",   "\U0001F4DC", "Histórico",   "Execuções anteriores"),
    ("laboratorio", "\U0001F9EA", "Laboratório", "Testes internos de interface (dev)"),
    ("configuracoes", "\u2699",   "Configurações", "Preferências do aplicativo"),
]

# Categorias que ainda não possuem tarefas reais implementadas.
# A tela dessas categorias mostra um estado "em breve" em vez de
# funcionalidades novas. "sistema" e "historico" saíram deste
# conjunto nesta etapa (Fase 1 do roadmap) — passaram a ter telas
# próprias (ver ui/sistema_view.py e ui/historico_view.py). Fora do
# escopo desta etapa: "ferramentas" e "configuracoes" continuam
# reservadas para o futuro.
CATEGORIAS_EM_BREVE = {"ferramentas", "configuracoes"}


# ---------------- TAREFAS DISPONÍVEIS ----------------
# A lista de tarefas e seus metadados (tempo estimado, capacidades de
# execução etc.) foram movidos para utils/tasks.py — fonte única de
# verdade, que substitui esta lista e o antigo
# core/execution/capabilities.py (que ficaram duplicados e fora de
# sincronia um do outro). Ver utils/tasks.py para o histórico
# completo da mudança.
