# ==========================================================
# Arquivo: config.py
# Responsabilidade: Configurações gerais da aplicação
# (título/tamanho da janela e nome da pasta usada para logs).
# ==========================================================

APP_TITULO = "Manutenção e Limpeza do Sistema - v3.0"
APP_VERSAO = "3.0"
APP_GEOMETRIA = "980x640"
APP_TAM_MINIMO = (860, 560)

# Nome da pasta usada em %LOCALAPPDATA% e em TEMP para armazenar o log,
# caso a pasta do próprio executável não aceite escrita.
NOME_PASTA_LOG = "ManutencaoSistema"
NOME_ARQUIVO_LOG = "manutencao_log.txt"

# Arquivo de preferências do aplicativo (Fase 8 — tela "Configurações").
# Vive na MESMA pasta já resolvida para o log (ver utils/logger.py:
# PASTA_LOG) — não é uma configuração do Windows, apenas o app
# lembrando das próprias preferências entre uma sessão e outra.
NOME_ARQUIVO_CONFIG = "manutencao_config.json"