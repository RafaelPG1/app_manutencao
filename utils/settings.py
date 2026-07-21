# ==========================================================
# Arquivo: utils/settings.py
# Responsabilidade: Persistência das PREFERÊNCIAS DO APLICATIVO
# (tela "Configurações" — Fase 8). Não tem nenhuma relação com
# configurações do Windows: é só o app lembrando, entre uma sessão e
# outra, de coisas como "confirmar antes de executar tarefas" ou
# "abrir sempre na última categoria utilizada".
#
# Reaproveita a MESMA pasta já resolvida por utils/logger.py
# (PASTA_LOG) para gravar um pequeno arquivo JSON — evita que o app
# passe a ter dois locais diferentes para os próprios dados (log de
# um lado, preferências de outro), com toda a lógica de fallback
# entre pasta do executável / %LOCALAPPDATA% / TEMP já resolvida e
# testada em utils/logger.py.
# ==========================================================

import json
import os
import threading

from config import NOME_ARQUIVO_CONFIG
from utils.logger import PASTA_LOG

_lock_config = threading.Lock()

ARQUIVO_CONFIG = os.path.join(PASTA_LOG, NOME_ARQUIVO_CONFIG)

# Valores padrão — usados na primeira execução, quando o arquivo não
# existe ainda, ou para completar qualquer chave que falte (ex.: um
# arquivo salvo por uma versão anterior, antes de uma preferência
# nova ser adicionada). Os padrões abaixo reproduzem exatamente o
# comportamento que o app já tinha ANTES da Fase 8, para que instalar
# esta versão não mude nada no comportamento de quem já usava o app.
PADRAO = {
    "confirmar_antes_executar": True,
    "abrir_ultima_categoria": False,
    "ultima_categoria": "dashboard",
    "max_registros_historico": 50,
}


def carregar_configuracoes() -> dict:
    """Carrega as preferências salvas, completando com os valores
    padrão quaisquer chaves ausentes. Nunca lança exceção: se o
    arquivo não existir, estiver corrompido ou não puder ser lido, o
    app simplesmente segue com os padrões — mesma postura de
    utils/logger.py, que nunca derruba o app por falha de I/O."""
    dados = dict(PADRAO)
    try:
        with _lock_config:
            with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
                salvo = json.load(f)
        if isinstance(salvo, dict):
            dados.update(salvo)
    except Exception:
        pass
    return dados


def salvar_configuracoes(config: dict):
    """Grava o dicionário de preferências inteiro no arquivo JSON.
    Chamado a cada alteração feita na tela de Configurações (sem
    exigir um botão "Salvar" separado). Falhas de escrita nunca devem
    interromper o app — mesma postura de utils/logger.py:log()."""
    try:
        with _lock_config:
            os.makedirs(os.path.dirname(ARQUIVO_CONFIG), exist_ok=True)
            with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AVISO] Não foi possível salvar configurações em {ARQUIVO_CONFIG}: {e}")