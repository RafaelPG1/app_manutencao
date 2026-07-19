# ==========================================================
# Arquivo: core/shared/terminal_manager.py
# Responsabilidade: ÚNICO módulo do aplicativo autorizado a falar
# diretamente com a API do Windows para abrir/controlar um Prompt de
# Comando (cmd.exe) REAL e VISÍVEL, persistente entre chamadas.
# Nenhum outro módulo (tarefas de core/, ExecutionManager, UI) deve
# abrir seu próprio cmd.exe visível para este fim — todos passam a
# usar apenas:
#
#       from core.shared.terminal_manager import terminal
#       rc = terminal.executar("sfc /scannow")
#
# IMPORTANTE — o que esta exclusividade NÃO cobre: comandos rápidos e
# silenciosos, sem necessidade de um CMD visível para o usuário (ex.:
# "ipconfig /flushdns", "net stop/start", uma consulta PowerShell),
# continuam usando utils.helpers.executar_comando (subprocess direto,
# sem janela) — ver core/limpeza/dns.py, core/shared/disk_info.py,
# core/limpeza/update_cache.py e core/diagnostico/chkdsk.py. A regra
# de exclusividade existe para impedir que MAIS DE UM cmd.exe visível
# e gerenciado seja aberto ao mesmo tempo (o que quebraria a garantia
# de "no máximo um" descrita abaixo) — não para proibir subprocess em
# geral no projeto.
#
# --------------------------------------------------------------
# O QUE ESTE MÓDULO GARANTE
# --------------------------------------------------------------
#   1. Existe NO MÁXIMO um cmd.exe gerenciado pelo aplicativo, com
#      título exclusivo, criado por este módulo (nunca pelo usuário).
#   2. Esse CMD é reaproveitado por todas as tarefas (SFC, DISM etc.):
#      nunca abrimos um novo CMD por comando.
#   3. Se o usuário fechar a janela, o próximo comando enviado detecta
#      isso e recria o terminal automaticamente.
#   4. O comando é executado EXATAMENTE como se tivesse sido digitado
#      manualmente por um usuário na janela: nenhum stdout/stderr do
#      cmd.exe é redirecionado ou capturado. A saída na tela continua
#      100% nativa do Windows.
#   5. Sabemos com certeza — não por suposição — quando cada comando
#      terminou, e qual foi seu código de saída real. Ver a seção
#      "COMO A DETECÇÃO DE TÉRMINO FUNCIONA" abaixo.
#   6. O usuário só vê, no CMD, exatamente o comando "de verdade" que
#      pediu para rodar (ex.: "sfc /scannow") seguido da saída nativa
#      dele — nunca a instrumentação interna usada para detectar o
#      término (ver "COMO A SENTINELA FICA INVISÍVEL" abaixo).
#   7. O CMD gerenciado permanece vivo durante toda a vida útil do
#      aplicativo e só é fechado por uma ação explícita e proposital
#      deste módulo (ver "COMO O CMD PERMANECE VIVO" e o método
#      público `encerrar()` mais abaixo) — nunca sozinho.
#
# --------------------------------------------------------------
# COMO A DETECÇÃO DE TÉRMINO FUNCIONA (sem timeout, sem heurística)
# --------------------------------------------------------------
# Um cmd.exe interativo não tem um "wait()" por comando individual —
# só o processo inteiro tem um exit code, e o processo aqui nunca sai
# entre uma tarefa e outra (é reaproveitado). Por isso, a confirmação
# de término não pode vir de "o processo encerrou": ela precisa vir de
# dentro da própria sessão do CMD.
#
# A solução usa apenas garantias nativas do cmd.exe: o operador `&` do
# CMD SÓ executa o que vem depois dele quando o que vem antes já
# terminou de verdade — não importa se o comando teve sucesso, erro,
# gerou muita saída, travou por alguns segundos etc. Essa é a única
# premissa usada, e ela vale para QUALQUER comando, porque é uma regra
# do interpretador de comandos, não algo específico do SFC/DISM.
#
# Em vez de terminar o CMD com `exit`, encadeamos um comando interno
# `title` com um token único (UUID) gerado a cada chamada:
#
#     <comando> & title __FIM_<token>_%errorlevel%__
#
# O `%errorlevel%` é expandido pelo próprio cmd.exe no momento em que
# o `title` roda — ou seja, DEPOIS que <comando> terminou — para o
# código de saída real dele. O título do console só pode mudar para
# esse valor depois que <comando> terminou; não há como isso
# acontecer antes.
#
# Este módulo então:
#   a) "digita" essa linha no CMD gerenciado através de
#      WriteConsoleInput (a mesma API que o Windows usa para entregar
#      teclas digitadas pelo usuário ao console) — não é stdin
#      redirecionado, é o buffer de entrada do próprio console;
#   b) fica consultando o TÍTULO da janela do console (GetConsoleTitle
#      — a mesma informação exibida na barra de título, nunca no corpo
#      da tela) até localizar o token exato daquela chamada;
#   c) assim que o token aparece, extrai o número que veio junto
#      (o errorlevel real), restaura o título original do CMD
#      gerenciado e retorna.
#
# Isso NÃO é um timeout nem uma espera arbitrária: não há prazo
# máximo, não presumimos duração nenhuma, e não paramos de esperar até
# a confirmação realmente aparecer. O laço de checagem (a cada poucos
# milissegundos) existe só porque a API de console do Windows não
# oferece um "avise-me quando isso acontecer" — ela obriga a consulta
# ativa. A diferença central para um timeout é que aqui NUNCA
# desistimos por tempo: só paramos de esperar quando (i) o token
# realmente aparece, ou (ii) detectamos, também de forma definitiva
# (Popen.poll()), que o próprio processo do CMD morreu — nunca por
# "já deve ter terminado".
#
# --------------------------------------------------------------
# COMO A SENTINELA FICA INVISÍVEL PARA O USUÁRIO
# --------------------------------------------------------------
# O sinal de término em si usa `title`, não `echo`: mudar o título da
# janela NUNCA escreve nada no corpo/texto do console (só na barra de
# título) — diferente de `echo`, que imprimiria o token na tela como
# uma linha de saída normal. Assim a sentinela nunca entra na área de
# texto do console, nem por um instante.
#
# Falta então esconder a PARTE DIGITADA da sentinela (o texto
# " & title __FIM_...%errorlevel%__" que é injetado junto do comando
# real na mesma linha, para o `&` funcionar). Uma primeira versão
# deste módulo tentava alternar ENABLE_ECHO_INPUT NO MEIO da linha
# digitada (eco ligado só para o comando visível, eco desligado só
# para a parte da sentinela, eco ligado de novo para o Enter). Isso
# tem uma CONDIÇÃO DE CORRIDA real: WriteConsoleInput apenas
# ENFILEIRA os eventos de teclado — quem realmente ecoa cada
# caractere na tela é a thread interna de processamento de console do
# Windows, de forma assíncrona, sem nenhuma API pública para saber
# quando ela já "drenou" os eventos anteriores. Como todos os eventos
# (visível + sentinela + Enter) são enfileirados quase instantaneamente
# e o modo já é restaurado para "eco ligado" logo em seguida, na
# prática a linha inteira — incluindo a sentinela — podia acabar
# sendo ecoada, dependendo de quando o processamento assíncrono do
# console realmente acontecia.
#
# A correção NÃO usa nenhum atraso ou heurística de tempo para tentar
# "acertar" essa corrida (isso seria não-determinístico e violaria a
# garantia 5 do topo deste arquivo). Em vez disso:
#
#   1) O eco de ENTRADA (ENABLE_ECHO_INPUT) fica DESLIGADO durante a
#      digitação da linha INTEIRA (comando real + sentinela + Enter)
#      — ou seja, nada do que é injetado é ecoado automaticamente
#      pelo console, eliminando a corrida por completo (não existe
#      "meio da linha" com eco ligado para competir com o resto).
#   2) O "eco" do comando que o usuário efetivamente vê é escrito por
#      ESTE módulo, diretamente, via WriteConsole no handle de SAÍDA
#      do console (não no de entrada) — uma chamada síncrona que, ao
#      retornar, já escreveu de fato no buffer de tela, sem fila e
#      sem processamento assíncrono envolvido. O texto escrito é
#      exatamente `comando` seguido de quebra de linha — nada além
#      disso.
#
# Resultado: o usuário vê apenas o comando real "digitado" e a saída
# nativa dele, exatamente como veria digitando à mão — a sentinela
# interna permanece 100% invisível, de forma determinística, sem abrir
# mão de nenhuma garantia de confiabilidade descrita acima.
#
# --------------------------------------------------------------
# COMO O CMD PERMANECE VIVO (causa raiz do fechamento espontâneo)
# --------------------------------------------------------------
# O CMD gerenciado é criado com CREATE_NEW_CONSOLE. Essa flag já
# isola o processo em seu PRÓPRIO console e, como consequência
# automática do Windows, também em seu próprio *process group* — ou
# seja, um Ctrl+C ou fechamento do console do aplicativo principal
# (se ele tiver um) já NÃO se propaga para o CMD gerenciado por essa
# via. Adicionar CREATE_NEW_PROCESS_GROUP não mudaria nada aqui: a
# própria documentação do Windows diz que essa flag é ignorada quando
# combinada com CREATE_NEW_CONSOLE, porque a segunda já implica a
# primeira.
#
# O que CREATE_NEW_CONSOLE **não** isola é o *Job Object*: por padrão
# do Windows, todo processo filho entra automaticamente no mesmo Job
# do processo que o criou, se esse processo pai pertencer a algum
# (isso vale mesmo com um console novo/próprio — Job Object é um
# mecanismo independente de console/process group). Se esse Job tiver
# o limite JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE configurado — comum em
# empacotadores como o PyInstaller (citado na seção de dependências
# abaixo) e em vários terminais/IDEs/lançadores que usam Job Objects
# para limpar processos filhos — o Windows mata TODOS os processos
# daquele Job, incluindo o CMD gerenciado, no momento em que o Job é
# fechado, sem que nenhuma linha deste módulo tenha pedido isso. Essa
# é a causa raiz real do fechamento espontâneo: nenhum código deste
# arquivo mata o processo; é o próprio SO matando um processo que,
# sem querer, herdou associação com o Job do aplicativo.
#
# A correção é usar a flag nativa CREATE_BREAKAWAY_FROM_JOB ao criar
# o processo, para que o CMD "escape" do Job do aplicativo e não seja
# afetado por essa política de limpeza. Essa flag não é exposta por
# subprocess.CREATE_* (só as mais comuns são), então seu valor
# numérico oficial do Windows é declarado manualmente logo abaixo
# (_CREATE_BREAKAWAY_FROM_JOB). Como alguns Jobs não permitem
# breakaway (não têm JOB_OBJECT_LIMIT_BREAKAWAY_OK habilitado), nesse
# caso o próprio CreateProcess do Windows REJEITA a flag com um erro
# real — não é algo que possamos silenciar por heurística. Por isso
# `_criar_terminal()` tenta primeiro com a flag e, somente se o
# Windows recusar (OSError real, não suposição), recria sem ela; o
# CMD gerenciado continua funcional, apenas sem essa proteção extra
# contra kill-on-job-close.
#
# --------------------------------------------------------------
# LIMITAÇÃO CONHECIDA E ACEITA (não é um ponto cego, é inerente a
# qualquer terminal real, inclusive um aberto manualmente pelo usuário)
# --------------------------------------------------------------
# Se o comando enviado ficar esperando uma entrada interativa do
# usuário (ex.: um "Pressione qualquer tecla para continuar" ou um
# prompt de confirmação S/N que a tarefa não tenha previsto), o
# TerminalManager corretamente NUNCA verá o token e ficará aguardando
# — porque o comando, de fato, ainda não terminou. Esse é o
# comportamento correto (mesma coisa aconteceria com um usuário
# humano parado na frente do CMD); não é resolvido por heurística
# alguma.
#
# --------------------------------------------------------------
# DEPENDÊNCIA (ATUALIZADO — SEM PYWIN32)
# --------------------------------------------------------------
# Versões anteriores deste módulo usavam o pacote externo `pywin32`
# (win32api, win32con, win32console, win32process) para chamar as
# APIs de console do Windows. Esse pacote foi removido por completo.
#
# Motivo da mudança: `pywin32` é uma dependência externa (exige
# `pip install pywin32`), complica um pouco o empacotamento com
# PyInstaller e, por ser um binário compilado sem stubs completos,
# gera avisos permanentes do Pylance ("reportMissingModuleSource")
# mesmo quando tudo funciona normalmente.
#
# O que substitui cada parte:
#   • Criação/controle do PROCESSO do cmd.exe (antes
#     win32process.CreateProcess): agora usa `subprocess.Popen`, que
#     já é biblioteca padrão. De brinde, `Popen.poll()` oferece uma
#     forma definitiva (não-suposta) de saber se o processo ainda
#     está vivo — o mesmo tipo de garantia que antes vinha de
#     GetExitCodeProcess/STILL_ACTIVE.
#   • APIs de console sem equivalente em `subprocess` (AttachConsole,
#     FreeConsole, WriteConsoleInput, GetConsoleTitle, SetConsoleTitle,
#     GetConsoleMode/SetConsoleMode): chamadas diretamente via
#     `ctypes` — também biblioteca padrão, sem `pip install` algum —
#     apontando para a mesma DLL do sistema (kernel32.dll) que o
#     pywin32 usava por baixo dos panos. O comportamento é IDÊNTICO ao
#     anterior (mesma técnica de digitação simulada + sentinela via
#     título); só a forma de chamar a API do Windows mudou.
#
# Não foi possível eliminar 100% o uso de APIs nativas do Windows
# porque a técnica central deste módulo (anexar a um console já
# existente e injetar eventos de teclado nele para simular digitação
# real, detectando o término de forma 100% confiável via título da
# janela) não tem equivalente em `subprocess` puro. Uma alternativa
# com `subprocess.Popen(..., stdin=PIPE)` foi considerada e
# descartada: nesse modelo o cmd.exe ecoa cada linha lida do pipe como
# texto normal na tela, então a sentinela de término deixaria de ser
# invisível (apareceria como uma linha extra na saída), violando a
# garantia 6 descrita no topo deste arquivo. Usar `ctypes` preserva
# 100% do comportamento original sem exigir nenhum pacote externo.
# ==========================================================

import ctypes
import re
import subprocess
import threading
import time
import uuid
from ctypes import wintypes

from utils.logger import log

TITULO_BASE = "Assistente de Manutencao - Terminal Gerenciado"

# Pasta em que o CMD gerenciado sempre é criado. Fixa (não é a pasta
# do projeto) para que os comandos exibidos ao usuário tenham a
# aparência natural de um Prompt de Comando comum do Windows.
_PASTA_INICIAL = r"C:\Windows\System32"

# Intervalo entre checagens do título do console. NÃO é um prazo
# máximo de espera (ver explicação acima) — é só a cadência da
# consulta ativa; o laço que o usa é ilimitado enquanto o CMD
# continuar vivo.
_INTERVALO_POLL = 0.05  # 50 ms

# Tempo máximo que encerrar() espera pelo lock de execução antes de
# forçar o encerramento do CMD gerenciado mesmo com um comando ainda
# em andamento (ver encerrar() para o motivo). Propositalmente curto:
# o objetivo é apenas evitar que o fechamento do aplicativo trave
# indefinidamente enquanto um comando longo (SFC/DISM) está rodando.
_TIMEOUT_ENCERRAR = 2.0  # segundos

# Formato da sentinela interna de término. É sempre enviada via
# `title` (nunca `echo`), então nunca aparece no corpo do console —
# só, por uma fração de segundo, na barra de título da janela — e é
# restaurada para o título original assim que lida (ver executar()).
_PADRAO_SENTINELA = "__FIM_{token}_"


# ==========================================================
# Bindings ctypes para as APIs de console do Windows (kernel32.dll).
# Substitui integralmente o antigo uso de win32console/win32api.
# ==========================================================
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_STD_INPUT_HANDLE = -10
_STD_OUTPUT_HANDLE = -11
_ENABLE_ECHO_INPUT = 0x0004
_ENABLE_EXTENDED_FLAGS = 0x0080
_ENABLE_QUICK_EDIT_MODE = 0x0040
_KEY_EVENT = 0x0001
_VK_RETURN = 0x0D

# Flag nativa do Windows (CreateProcess / winbase.h) que faz o
# processo recém-criado "escapar" de qualquer Job Object ao qual o
# processo ATUAL (o aplicativo) pertença. Não está entre as flags que
# `subprocess.CREATE_*` expõe, por isso o valor numérico oficial é
# declarado aqui manualmente. Ver "COMO O CMD PERMANECE VIVO" no
# cabeçalho do arquivo para o porquê disso ser necessário.
_CREATE_BREAKAWAY_FROM_JOB = 0x01000000


class _KeyEventRecord(ctypes.Structure):
    """Equivalente ctypes de KEY_EVENT_RECORD (winuser/wincon)."""
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar", wintypes.WCHAR),
        ("dwControlKeyState", wintypes.DWORD),
    ]


class _InputRecord(ctypes.Structure):
    # A struct real do Windows (INPUT_RECORD) tem um `union` com vários
    # tipos de evento possíveis (teclado, mouse, etc.). Como este
    # módulo só escreve eventos de teclado, usamos apenas o layout de
    # _KeyEventRecord — ele tem o mesmo tamanho em bytes (16) que os
    # demais membros da union, então o Windows interpreta corretamente
    # qualquer registro do tipo KEY_EVENT que escrevemos aqui.
    _fields_ = [
        ("EventType", wintypes.WORD),
        ("KeyEvent", _KeyEventRecord),
    ]


_kernel32.AttachConsole.argtypes = [wintypes.DWORD]
_kernel32.AttachConsole.restype = wintypes.BOOL

_kernel32.FreeConsole.argtypes = []
_kernel32.FreeConsole.restype = wintypes.BOOL

_kernel32.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
_kernel32.GetConsoleTitleW.restype = wintypes.DWORD

_kernel32.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
_kernel32.SetConsoleTitleW.restype = wintypes.BOOL

_kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
_kernel32.GetStdHandle.restype = wintypes.HANDLE

_kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_kernel32.GetConsoleMode.restype = wintypes.BOOL

_kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_kernel32.SetConsoleMode.restype = wintypes.BOOL

_kernel32.WriteConsoleInputW.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(_InputRecord),
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
_kernel32.WriteConsoleInputW.restype = wintypes.BOOL

_kernel32.WriteConsoleW.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.c_void_p,
]
_kernel32.WriteConsoleW.restype = wintypes.BOOL


def _checar(sucesso: bool, mensagem: str):
    """Levanta um OSError com a mensagem real do Windows (via
    GetLastError) quando uma chamada ctypes ao kernel32 falha."""
    if not sucesso:
        erro = ctypes.WinError(ctypes.get_last_error())
        raise OSError(f"{mensagem}: {erro}")


class TerminalIndisponivelError(RuntimeError):
    """Levantado quando o CMD gerenciado foi fechado (ou morreu) ANTES
    de confirmarmos, pelo token real, que o comando em andamento
    havia terminado. Quem chama (ex.: uma tarefa de core/) deve tratar
    isso como falha daquele comando — nunca presumimos sucesso nem
    término nessa situação."""


class TerminalManager:
    """Dono único do Prompt de Comando (cmd.exe) real e persistente do
    aplicativo. Ver o cabeçalho deste arquivo para o funcionamento
    completo. Uso típico (de dentro de uma tarefa em core/<dominio>/):

        from core.shared.terminal_manager import terminal
        codigo_saida = terminal.executar("sfc /scannow")

    `executar()` bloqueia a thread chamadora até o comando realmente
    terminar (confirmado, nunca suposto) e devolve o código de saída
    real (%errorlevel%). Como o ExecutionManager já roda cada tarefa
    em sua própria thread de segundo plano, esse bloqueio não trava a
    interface.

    O CMD gerenciado permanece vivo durante toda a vida útil do
    aplicativo (ver "COMO O CMD PERMANECE VIVO" no cabeçalho) e só é
    fechado por uma chamada explícita a `encerrar()`, feita no
    encerramento do aplicativo.
    """

    _instancia = None
    _instancia_lock = threading.Lock()

    def __new__(cls):
        # Singleton: o aplicativo inteiro deve compartilhar o MESMO
        # TerminalManager (e, portanto, o mesmo CMD gerenciado).
        with cls._instancia_lock:
            if cls._instancia is None:
                cls._instancia = super().__new__(cls)
                cls._instancia._inicializado = False
            return cls._instancia

    def __init__(self):
        if self._inicializado:
            return
        self._inicializado = True
        # Serializa o uso do terminal: só um executar() (ou um
        # encerrar()) por vez.
        self._lock = threading.RLock()
        self._processo = None  # subprocess.Popen do cmd.exe gerenciado
        self._titulo_atual = None
        # True depois que encerrar() roda (aplicativo em fechamento).
        # Existe para impedir que uma tarefa seguinte do MESMO lote,
        # rodando em segundo plano e alheia ao fechamento da janela,
        # recrie um CMD novo bem no instante em que o app está sendo
        # fechado (ver _garantir_terminal). Um CMD criado nesse
        # instante sobreviveria ao processo Python (graças ao proprio
        # CREATE_BREAKAWAY_FROM_JOB que evita o fechamento espontaneo)
        # e nunca mais seria encerrado, pois encerrar() ja rodou.
        self._encerrado = False

    # -------------------- Propriedades de consulta --------------------
    @property
    def titulo(self):
        """Título exclusivo do CMD atualmente gerenciado (ou None se
        ainda não foi criado nenhum)."""
        return self._titulo_atual

    @property
    def pid(self):
        return self._processo.pid if self._processo is not None else None

    def esta_ativo(self) -> bool:
        """True se o CMD gerenciado existe e ainda está vivo (não foi
        fechado pelo usuário, não travou/encerrou)."""
        with self._lock:
            return self._esta_vivo()

    # -------------------- Ciclo de vida do CMD gerenciado --------------------
    def _esta_vivo(self) -> bool:
        if self._processo is None:
            return False
        # Popen.poll() é uma consulta DEFINITIVA (não suposição):
        # retorna None enquanto o processo do CMD ainda está rodando,
        # ou o código de saída real assim que ele encerra — a mesma
        # garantia que antes vinha de GetExitCodeProcess/STILL_ACTIVE.
        return self._processo.poll() is None

    def _flags_criacao(self, tentar_breakaway: bool) -> int:
        """Monta as creationflags do CreateProcess usadas para o CMD
        gerenciado. CREATE_NEW_CONSOLE por si só já isola o processo
        em seu próprio console/process group (ver "COMO O CMD
        PERMANECE VIVO" no cabeçalho). CREATE_BREAKAWAY_FROM_JOB é
        adicionada quando `tentar_breakaway` for True, para o processo
        escapar do Job Object do aplicativo (a causa raiz real de
        fechamentos espontâneos em processos empacotados/lançados sob
        um Job com kill-on-job-close)."""
        flags = subprocess.CREATE_NEW_CONSOLE
        if tentar_breakaway:
            flags |= _CREATE_BREAKAWAY_FROM_JOB
        return flags

    def _criar_terminal(self):
        """Cria um novo cmd.exe real e visível (console próprio,
        janela padrão do Windows, sem nenhum stdio redirecionado) com
        um título exclusivo, e passa a gerenciá-lo.

        Como o aplicativo inteiro já roda elevado (ver
        core/shared/admin.py), este cmd.exe filho herda o mesmo token
        de Administrador automaticamente — nenhuma elevação extra é
        necessária aqui.

        Inicia sempre em `_PASTA_INICIAL` (C:\\Windows\\System32),
        nunca na pasta do projeto — assim o prompt exibido ao usuário
        (ex.: "C:\\Windows\\System32>") tem a aparência de um Prompt
        de Comando comum do Windows.

        Tenta criar o processo com CREATE_BREAKAWAY_FROM_JOB (ver
        "COMO O CMD PERMANECE VIVO" no cabeçalho do arquivo) para que
        ele não seja derrubado junto com o Job do aplicativo. Se o Job
        atual não permitir breakaway, o próprio Windows rejeita a
        flag com um erro real (não é uma suposição nossa) — nesse
        caso, e somente nesse caso, recriamos sem a flag.
        """
        token_titulo = uuid.uuid4().hex[:8]
        self._titulo_atual = f"{TITULO_BASE} [{token_titulo}]"

        # "/k title <titulo>" define o título da janela como primeiro
        # comando e mantém o CMD aberto aguardando o PRÓXIMO comando —
        # exatamente como uma sessão que um usuário deixaria aberta.
        # Passar a linha de comando como STRING (e não como lista) faz
        # o subprocess entregá-la ao Windows sem reprocessar aspas,
        # preservando o mesmo truque de quoting usado antes com
        # win32process.CreateProcess.
        linha_comando = f'cmd.exe /k "title {self._titulo_atual}"'

        try:
            self._processo = subprocess.Popen(
                linha_comando,
                creationflags=self._flags_criacao(tentar_breakaway=True),
                cwd=_PASTA_INICIAL,  # sempre System32
            )
        except OSError as erro_breakaway:
            # O Job atual não permite breakaway
            # (JOB_OBJECT_LIMIT_BREAKAWAY_OK ausente) — o próprio
            # CreateProcess recusou a flag. Recriamos sem ela; o CMD
            # gerenciado continua funcional, só perde a proteção
            # extra contra kill-on-job-close.
            log(
                "[TERMINAL_MANAGER] CREATE_BREAKAWAY_FROM_JOB recusado pelo "
                f"Windows ({erro_breakaway}) - recriando sem a flag"
            )
            self._processo = subprocess.Popen(
                linha_comando,
                creationflags=self._flags_criacao(tentar_breakaway=False),
                cwd=_PASTA_INICIAL,
            )

        log(
            f"[TERMINAL_MANAGER] Novo CMD criado - PID {self._processo.pid} - "
            f"Titulo: {self._titulo_atual}"
        )

        try:
            self._aguardar_console_existir()
        except TerminalIndisponivelError:
            # O processo chegou a ser criado, mas seu console nunca
            # ficou pronto dentro do prazo — sem esta limpeza, ele
            # ficaria órfão (rodando elevado, possivelmente
            # sobrevivendo ao próprio fechamento do aplicativo por
            # causa do CREATE_BREAKAWAY_FROM_JOB) até ser fechado
            # manualmente pelo usuário.
            try:
                if self._processo is not None and self._processo.poll() is None:
                    self._processo.terminate()
                    self._processo.wait(timeout=5)
            except Exception as erro_limpeza:
                log(
                    "[TERMINAL_MANAGER] Falha ao limpar CMD orfao apos "
                    f"timeout de inicializacao: {erro_limpeza}"
                )
            self._processo = None
            self._titulo_atual = None
            raise

    def _aguardar_console_existir(self, tempo_max: float = 5.0):
        """Espera o OBJETO de console do processo recém-criado passar
        a existir no Windows (etapa de criação do processo — ordem de
        milissegundos). IMPORTANTE: isto não tem relação com "esperar
        um comando terminar" — é apenas aguardar o SO acabar de montar
        o console do processo filho antes de tentarmos anexar a ele.
        Se isso não acontecer dentro de `tempo_max`, o processo não
        chegou a criar um console válido e consideramos falha real de
        criação (não um comando que "ainda não terminou").

        Assim que o console fica alcançável, aproveita o anexo para
        DESLIGAR o QuickEdit Mode dele (ver `_desligar_quick_edit`) —
        precisa ser feito uma única vez aqui, pois é uma propriedade
        do objeto de console que persiste por toda a vida útil dele,
        não algo que precise ser reaplicado a cada comando."""
        inicio = time.time()
        ultimo_erro = None
        while time.time() - inicio < tempo_max:
            _kernel32.FreeConsole()
            if _kernel32.AttachConsole(wintypes.DWORD(self._processo.pid)):
                self._desligar_quick_edit()
                _kernel32.FreeConsole()
                return
            ultimo_erro = ctypes.WinError(ctypes.get_last_error())
            time.sleep(0.02)
        raise TerminalIndisponivelError(
            f"O console do CMD recem-criado (PID {self._processo.pid}) nao ficou "
            f"disponivel a tempo: {ultimo_erro}"
        )

    @staticmethod
    def _desligar_quick_edit():
        """Desliga o QuickEdit Mode (modo de seleção de texto por
        mouse) do console ATUALMENTE anexado.

        CORREÇÃO DE BUG: por padrão do próprio Windows, todo cmd.exe
        clássico nasce com QuickEdit Mode LIGADO. Enquanto uma seleção
        de texto está ativa nesse modo (ex.: um clique do usuário
        dentro da janela, mesmo que seja só o foco mudando), o Windows
        PAUSA qualquer escrita pendente no buffer de tela do console
        — de qualquer processo anexado a ele — até a seleção ser
        cancelada. Isso travava `_escrever_texto_na_tela` (WriteConsole)
        no meio de `_digitar_linha`, dentro do lock de `executar()`,
        fazendo a tarefa seguinte esperar indefinidamente por esse
        lock — e explica por que apertar uma tecla (ex.: Ctrl+C) na
        janela do CMD, que cancela a seleção, destravava tudo na hora.

        Desligar QuickEdit remove a causa raiz: sem ele, cliques do
        mouse na janela não iniciam mais seleção nenhuma, então nunca
        mais pausam a escrita no console."""
        handle_entrada = _kernel32.GetStdHandle(wintypes.DWORD(_STD_INPUT_HANDLE))
        modo_atual = wintypes.DWORD(0)
        _checar(
            _kernel32.GetConsoleMode(handle_entrada, ctypes.byref(modo_atual)),
            "Falha ao ler o modo de entrada do console para desligar o QuickEdit Mode",
        )
        # ENABLE_EXTENDED_FLAGS precisa estar LIGADO para que mudanças
        # em ENABLE_QUICK_EDIT_MODE tenham efeito (exigência da própria
        # API do Windows - SetConsoleMode ignora esse bit sem ele).
        novo_modo = (modo_atual.value & ~_ENABLE_QUICK_EDIT_MODE) | _ENABLE_EXTENDED_FLAGS
        _checar(
            _kernel32.SetConsoleMode(handle_entrada, novo_modo),
            "Falha ao desligar o QuickEdit Mode do console gerenciado",
        )

    def _garantir_terminal(self):
        """Cria o CMD na primeira vez, ou recria automaticamente se o
        anterior não estiver mais ativo (fechado pelo usuário, morto,
        etc.). Chamado sempre no início de executar().

        Se `encerrar()` já rodou (aplicativo em fechamento), NÃO
        recria — levanta TerminalIndisponivelError. Sem essa checagem,
        uma tarefa do mesmo lote que ainda não chamou executar() no
        momento exato do fechamento recriaria um CMD novo, órfão, que
        sobreviveria ao processo (ver o comentário de `_encerrado` no
        __init__)."""
        if self._encerrado:
            raise TerminalIndisponivelError(
                "O TerminalManager ja foi encerrado (aplicativo em "
                "fechamento); nao e possivel executar mais comandos."
            )
        if not self._esta_vivo():
            if self._processo is not None:
                log("[TERMINAL_MANAGER] CMD gerenciado nao esta mais ativo - recriando...")
            self._criar_terminal()

    # -------------------- Anexação ao console do CMD gerenciado --------------------
    def _anexar(self):
        # NOTA: AttachConsole/FreeConsole afetam o console do PROCESSO
        # INTEIRO (não por thread). Se este aplicativo já tinha um
        # console próprio no momento em que o primeiro _anexar() é
        # chamado (ex.: rodando via "python main.py" em um terminal,
        # durante desenvolvimento — nunca no empacotamento oficial via
        # PyInstaller --noconsole, que não tem console próprio para
        # perder), esse console original é liberado por FreeConsole()
        # e nunca é reanexado: não há como recuperar um console já
        # liberado, apenas anexar-se a um console de OUTRO processo
        # ainda vivo (via PID) — o que não se aplica ao console
        # original do próprio processo. Na prática, isso só afeta
        # print()/tracebacks não tratados durante depuração via
        # "python main.py"; o comportamento do CMD gerenciado em si
        # (o que o usuário final vê) não é afetado.
        _kernel32.FreeConsole()
        _checar(
            _kernel32.AttachConsole(wintypes.DWORD(self._processo.pid)),
            "Falha ao anexar ao console do CMD gerenciado",
        )

    def _desanexar(self):
        _kernel32.FreeConsole()

    # -------------------- Envio de comando (digitação real via console) --------------------
    @staticmethod
    def _registros_para(texto: str):
        """Converte cada caractere de `texto` em um registro de evento
        de teclado (KEY_EVENT), no formato aceito por
        WriteConsoleInput."""
        registros = []
        for caractere in texto:
            registro = _InputRecord()
            registro.EventType = _KEY_EVENT
            registro.KeyEvent.bKeyDown = True
            registro.KeyEvent.wRepeatCount = 1
            registro.KeyEvent.uChar = caractere
            registro.KeyEvent.wVirtualKeyCode = 0
            registro.KeyEvent.wVirtualScanCode = 0
            registro.KeyEvent.dwControlKeyState = 0
            registros.append(registro)
        return registros

    @staticmethod
    def _escrever_eventos(handle_entrada, registros):
        if not registros:
            return
        n = len(registros)
        array_registros = (_InputRecord * n)(*registros)
        escritos = wintypes.DWORD(0)
        _checar(
            _kernel32.WriteConsoleInputW(handle_entrada, array_registros, n, ctypes.byref(escritos)),
            "Falha ao escrever entrada no console do CMD gerenciado",
        )

    @staticmethod
    def _escrever_texto_na_tela(handle_saida, texto: str):
        """Escreve `texto` diretamente no buffer de tela do console
        (WriteConsole no handle de SAÍDA) — uma chamada síncrona que,
        ao retornar, já escreveu de fato na tela. NÃO é eco de
        entrada: é este módulo produzindo, ele mesmo, exatamente o
        texto que apareceria se o usuário tivesse digitado `texto` e
        apertado Enter. Ver "COMO A SENTINELA FICA INVISÍVEL" no
        cabeçalho do arquivo para o motivo de não depender do eco
        automático do console para isso."""
        if not texto:
            return
        escritos = wintypes.DWORD(0)
        _checar(
            _kernel32.WriteConsoleW(handle_saida, texto, len(texto), ctypes.byref(escritos), None),
            "Falha ao escrever no buffer de tela do console",
        )

    def _digitar_linha(self, visivel: str, oculto: str = ""):
        """Envia `visivel` + `oculto` + Enter ao CMD ANEXADO no
        momento, através do buffer de ENTRADA do console
        (WriteConsoleInput) — a mesma via usada pelo Windows para
        entregar teclas digitadas pelo usuário. Não é stdin
        redirecionado: o cmd.exe lê isso do jeito que sempre leu, sem
        saber (nem precisar saber) que quem "digitou" foi o aplicativo
        em vez de uma pessoa.

        O eco de ENTRADA (ENABLE_ECHO_INPUT) fica DESLIGADO durante a
        linha INTEIRA — `visivel`, `oculto` e o Enter — para que nada
        disso seja ecoado automaticamente pelo console (ver "COMO A
        SENTINELA FICA INVISÍVEL" no cabeçalho do arquivo: alternar o
        eco NO MEIO da linha tem uma condição de corrida real e foi
        abandonado). No lugar do eco automático, `visivel` é escrito
        por este módulo diretamente na tela (`_escrever_texto_na_tela`)
        — é isso que o usuário vê, ex.: "sfc /scannow" seguido de
        quebra de linha, exatamente como uma digitação normal. `oculto`
        (a sentinela de término, se houver) nunca é escrito na tela,
        nem por este módulo nem pelo console — só entra no buffer de
        ENTRADA, para o cmd.exe processar."""
        handle_entrada = _kernel32.GetStdHandle(wintypes.DWORD(_STD_INPUT_HANDLE))
        handle_saida = _kernel32.GetStdHandle(wintypes.DWORD(_STD_OUTPUT_HANDLE))

        modo_original = wintypes.DWORD(0)
        _checar(
            _kernel32.GetConsoleMode(handle_entrada, ctypes.byref(modo_original)),
            "Falha ao ler o modo de entrada do console",
        )
        _checar(
            _kernel32.SetConsoleMode(handle_entrada, modo_original.value & ~_ENABLE_ECHO_INPUT),
            "Falha ao desligar o eco de entrada do console",
        )
        try:
            # Eco manual e síncrono do comando visível — substitui o
            # eco automático do console para essa parte da linha.
            self._escrever_texto_na_tela(handle_saida, f"{visivel}\r\n")

            if visivel:
                self._escrever_eventos(handle_entrada, self._registros_para(visivel))
            if oculto:
                self._escrever_eventos(handle_entrada, self._registros_para(oculto))

            registro_enter = _InputRecord()
            registro_enter.EventType = _KEY_EVENT
            registro_enter.KeyEvent.bKeyDown = True
            registro_enter.KeyEvent.wRepeatCount = 1
            registro_enter.KeyEvent.uChar = "\r"
            registro_enter.KeyEvent.wVirtualKeyCode = _VK_RETURN
            registro_enter.KeyEvent.wVirtualScanCode = 0
            registro_enter.KeyEvent.dwControlKeyState = 0
            self._escrever_eventos(handle_entrada, [registro_enter])
        finally:
            # Sempre restaura o modo original, mesmo se algo falhar —
            # nunca deixamos o console de um CMD real do usuário com
            # o eco de entrada desligado por engano.
            _kernel32.SetConsoleMode(handle_entrada, modo_original.value)

    # -------------------- Espera pela confirmação real de término --------------------
    def _ler_titulo_console(self) -> str:
        buffer = ctypes.create_unicode_buffer(1024)
        _kernel32.GetConsoleTitleW(buffer, 1024)
        return buffer.value

    def _esperar_sentinela(self, token: str) -> int:
        """Consulta o TÍTULO do console anexado (nunca o corpo da
        tela) até localizar a sentinela daquela chamada. Mudar o
        título nunca escreve nada na área de texto do console — por
        isso a sentinela nunca é visível para o usuário, nem por um
        instante (ver "COMO A SENTINELA FICA INVISÍVEL" no
        cabeçalho)."""
        padrao = re.compile(rf"__FIM_{token}_(-?\d+)__")
        while True:
            # Consulta DEFINITIVA (não suposição) sobre o processo:
            # ou ele está vivo, ou já morreu com um exit code real.
            if not self._esta_vivo():
                raise TerminalIndisponivelError(
                    "O Prompt de Comando foi fechado (ou encerrou) enquanto "
                    "um comando ainda estava em execucao; nao e possivel "
                    "confirmar seu termino real nem seu codigo de saida."
                )

            titulo_atual = self._ler_titulo_console()
            encontrado = padrao.search(titulo_atual)
            if encontrado:
                return int(encontrado.group(1))

            # Não é um prazo máximo: apenas a cadência da consulta
            # ativa. O laço só termina pelas duas condições acima.
            time.sleep(_INTERVALO_POLL)

    # -------------------- API pública --------------------
    def executar(self, comando: str) -> int:
        """Envia `comando` ao CMD real e persistente do aplicativo e
        bloqueia até que o PRÓPRIO cmd.exe confirme (nunca por
        suposição) que ele terminou, devolvendo o código de saída real
        (equivalente a %errorlevel%).

        Funciona para QUALQUER comando de linha (`sfc /scannow`,
        `DISM /Online ...`, `ipconfig /flushdns`, comandos compostos
        com `&`/`&&`/`|`, etc.) — a detecção de término não depende do
        formato da saída do comando em nenhum momento; depende apenas
        da semântica sequencial do próprio interpretador de comandos.
        Ver o cabeçalho deste arquivo para os detalhes.

        O usuário só vê `comando` (ex.: "sfc /scannow") e a saída
        nativa dele; a sentinela interna de término é digitada de
        forma invisível e sinalizada via título da janela — nunca
        aparece no corpo do console (ver "COMO A SENTINELA FICA
        INVISÍVEL" no cabeçalho).

        Levanta TerminalIndisponivelError se o CMD gerenciado for
        fechado/morrer enquanto este comando específico ainda estava
        em execução (nesse caso o próximo executar() recria o
        terminal automaticamente).
        """
        with self._lock:
            self._garantir_terminal()

            token = uuid.uuid4().hex
            sentinela = f" & title {_PADRAO_SENTINELA.format(token=token)}%errorlevel%__"
            titulo_original = self._titulo_atual

            log(f"[TERMINAL_MANAGER] Enviando comando (PID {self._processo.pid}): {comando}")

            try:
                self._anexar()
                self._digitar_linha(comando, sentinela)
                codigo = self._esperar_sentinela(token)
                # Restaura o título original do CMD gerenciado — ele
                # foi trocado momentaneamente pela sentinela interna,
                # que nunca aparece no corpo do console, só na barra
                # de título, e só até este ponto. Falha aqui é apenas
                # cosmética (não invalida o código já obtido acima),
                # por isso só é registrada, nunca propagada.
                if not _kernel32.SetConsoleTitleW(titulo_original):
                    log(
                        f"[TERMINAL_MANAGER] Aviso: falha ao restaurar o "
                        f"titulo original do CMD (erro nao fatal, codigo "
                        f"do comando ja obtido: {ctypes.get_last_error()})"
                    )
            except OSError as erro:
                # Se uma chamada de API do console falhou (ex.:
                # AttachConsole) e o processo do CMD está confirmado
                # morto, é o mesmo cenário que _esperar_sentinela já
                # trata como TerminalIndisponivelError — só que aqui a
                # morte ocorreu um pouco mais cedo (entre a checagem em
                # _garantir_terminal() e o uso efetivo do console). Sem
                # esta conversão, sfc.py/dism.py (que só capturam
                # TerminalIndisponivelError) deixariam esse OSError
                # escapar como erro genérico e inesperado.
                if not self._esta_vivo():
                    raise TerminalIndisponivelError(
                        f"O Prompt de Comando foi encerrado durante o "
                        f"envio do comando; nao e possivel confirmar seu "
                        f"termino real: {erro}"
                    ) from erro
                raise
            finally:
                self._desanexar()

            log(f"[TERMINAL_MANAGER] Comando concluido - codigo {codigo}: {comando}")
            return codigo

    def encerrar(self):
        """Encerra EXCLUSIVAMENTE o CMD gerenciado por esta instância,
        usando o handle de processo que o próprio `subprocess.Popen`
        já mantém desde a criação (`_criar_terminal`) — nunca uma
        varredura por nome/imagem (ex.: "taskkill /IM cmd.exe"), que
        fecharia qualquer cmd.exe aberto pelo usuário. `Popen.terminate()`
        chama `TerminateProcess` diretamente sobre esse handle, então é
        garantidamente o mesmo processo criado por este módulo.

        Deve ser chamado uma única vez, no encerramento do aplicativo
        (ex.: no fechamento da janela principal). É seguro chamar mais
        de uma vez ou quando nenhum CMD foi criado ainda (nesses casos
        não faz nada além de marcar o estado de encerrado). Depois de
        chamado, `esta_ativo()` passa a retornar False e qualquer
        `executar()` seguinte (de uma tarefa que ainda estivesse em
        andamento em segundo plano) levanta TerminalIndisponivelError
        em vez de recriar um novo CMD — este TerminalManager não deve
        mais criar processos depois que o aplicativo pediu para
        fechar.

        IMPORTANTE sobre o lock: `executar()` mantém o lock de
        execução adquirido durante toda a espera por um comando (que
        pode durar dezenas de minutos, ex.: SFC/DISM). Por isso este
        método NÃO espera o lock indefinidamente — isso travaria o
        encerramento do aplicativo pela duração inteira do comando em
        andamento. Em vez disso, espera no máximo
        `_TIMEOUT_ENCERRAR` segundos pelo lock; se não conseguir,
        encerra o processo do CMD mesmo assim (`TerminateProcess` é
        seguro de chamar mesmo com outra thread usando o console
        naquele instante) e deixa a limpeza final do estado
        (`self._processo = None`) para quando o lock puder mesmo ser
        obtido — a thread que estava em `executar()` detecta a morte
        do processo em até ~50 ms (via `_esta_vivo()`, chamado no
        laço de `_esperar_sentinela`) e sai sozinha, levantando
        TerminalIndisponivelError e liberando o lock logo em seguida.
        """
        self._encerrado = True

        adquirido = self._lock.acquire(timeout=_TIMEOUT_ENCERRAR)
        try:
            processo = self._processo
            if processo is None:
                return

            if processo.poll() is None:
                pid = processo.pid
                try:
                    processo.terminate()
                    processo.wait(timeout=5)
                except Exception as erro:
                    log(
                        f"[TERMINAL_MANAGER] Falha ao encerrar o CMD gerenciado "
                        f"(PID {pid}): {erro}"
                    )
                else:
                    log(
                        f"[TERMINAL_MANAGER] CMD gerenciado (PID {pid}) encerrado "
                        f"junto com o aplicativo"
                    )

            # Só reseta o estado compartilhado se o lock foi
            # realmente obtido: sem o lock, outra thread pode estar no
            # meio de um `executar()` lendo `self._processo` neste
            # exato momento, e zerá-lo aqui causaria uma exceção não
            # tratada nela (ao inves da TerminalIndisponivelError
            # esperada). Nesse caso, o processo já foi encerrado acima
            # (o que é o que importa para o fechamento do app); o
            # estado em si fica para a thread em `executar()` resolver
            # sozinha, como já faz normalmente ao detectar a morte do
            # processo.
            if adquirido:
                self._processo = None
                self._titulo_atual = None
        finally:
            if adquirido:
                self._lock.release()


# Instância única compartilhada por todo o aplicativo. As tarefas em
# core/<dominio>/ devem importar e usar apenas isto:
#
#     from core.shared.terminal_manager import terminal
#     rc = terminal.executar("sfc /scannow")
terminal = TerminalManager()