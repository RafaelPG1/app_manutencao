#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================================================
# Arquivo: main.py
# Responsabilidade: Ponto de entrada do aplicativo — cria a
# janela Tkinter, instancia a interface principal e inicia o
# loop de eventos.
# ==========================================================
"""
Manutenção e Limpeza do Sistema - v3.0 (GUI)

Requisitos:
- Windows 10/11
- Executar como Administrador (o próprio script tenta se reabrir elevado)

Como rodar:
    python main.py

Como gerar um .exe (opcional, com PyInstaller):
    pip install pyinstaller
    pyinstaller --onefile --noconsole --uac-admin main.py
"""

import sys
import tkinter as tk

from ui.main_window import ManutencaoApp


def main():
    if sys.platform != "win32":
        print("Este programa foi feito para Windows 10/11.")
        sys.exit(1)

    root = tk.Tk()
    app = ManutencaoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
