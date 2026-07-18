# ==========================================================
# Arquivo: core/shared/admin.py
# Responsabilidade: Verificação e elevação de privilégios de
# Administrador do Windows.
# ==========================================================

import sys
import ctypes


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin():
    """Reabre o próprio script/executável com privilégios de administrador."""
    if getattr(sys, "frozen", False):
        # Executável gerado pelo PyInstaller: sys.executable e
        # sys.argv[0] apontam para o MESMO arquivo .exe (é o próprio
        # interpretador embutido). Usar sys.argv[0] aqui, como no
        # cenário de script abaixo, duplicaria o caminho do executável
        # como um argumento espúrio na linha de comando relançada —
        # por isso usamos apenas os argumentos extras (sys.argv[1:]).
        extras = " ".join(f'"{a}"' for a in sys.argv[1:])
        args = extras
    else:
        # "python main.py": sys.executable é o python.exe e
        # sys.argv[0] é o caminho do script — precisam de sys.argv[0]
        # explicitamente para o script ser localizado.
        extras = " ".join(f'"{a}"' for a in sys.argv[1:])
        args = f'"{sys.argv[0]}"' + (f" {extras}" if extras else "")
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, args, None, 1
    )
