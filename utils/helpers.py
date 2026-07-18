# ==========================================================
# Arquivo: utils/helpers.py
# Responsabilidade: Funções utilitárias genéricas usadas em
# várias partes do projeto (formatação de data/hora, execução
# de comandos externos via subprocess e extração de percentual
# real da saída de ferramentas como SFC/DISM).
# ==========================================================

import datetime
import re
import subprocess

# Extrai apenas o número percentual de qualquer linha, independente do
# idioma do Windows. Cobre casos como:
#   "Verificação de arquivos do sistema 35% concluída."       (SFC pt-BR)
#   "Verification 35% complete."                              (SFC en-US)
#   "[==========35,0%==========    ]"                         (DISM)
# e qualquer outra variação, pois não depende do texto ao redor —
# só do padrão "<número>%".
_PADRAO_PERCENTUAL = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")


def agora() -> str:
    """Retorna a data/hora atual formatada (dd/mm/aaaa hh:mm:ss)."""
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def extrair_percentual(texto: str):
    """Extrai o percentual real (0-100) de uma linha de saída de
    ferramentas como SFC ou DISM. Retorna None quando a linha não
    contém nenhum percentual — usado por quem chama para decidir se
    há algo novo para reportar (nunca inventa um valor)."""
    match = _PADRAO_PERCENTUAL.search(texto)
    if not match:
        return None
    valor_str = match.group(1).replace(",", ".")
    try:
        return float(valor_str)
    except ValueError:
        return None


def executar_comando(cmd, shell: bool = False):
    """Executa um comando externo e retorna (returncode, stdout, stderr).

    Mantém o mesmo comportamento usado em todo o projeto original:
    captura de saída como texto, ignorando erros de decodificação, e
    sem abrir janela de console (CREATE_NO_WINDOW).

    ATENÇÃO: esta função usa subprocess.run(capture_output=True), que
    só devolve a saída quando o processo JÁ TERMINOU (internamente é um
    Popen + communicate()). Não há streaming aqui.
    """
    resultado = subprocess.run(
        cmd, shell=shell, capture_output=True, text=True,
        errors="ignore", creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return resultado.returncode, resultado.stdout, resultado.stderr


# NOTA: as antigas executar_comando_streaming() e
# executar_comando_terminal_real() foram removidas por não terem
# nenhum uso em todo o projeto (código morto). A execução de comandos
# em um CMD real e visível, com confirmação de término, é feita
# exclusivamente por core/shared/terminal_manager.py — manter uma
# segunda função capaz de abrir seu próprio cmd.exe fora desse módulo
# era um risco latente de, no futuro, violar o invariante de "no
# máximo um cmd.exe gerenciado pelo aplicativo".