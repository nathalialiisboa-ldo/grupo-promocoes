"""Busca ofertas da Shopee via API e atualiza o banco local.

Rode manualmente com `python fetch_shopee.py`, ou agende no Agendador de
Tarefas do Windows para rodar 2x ao dia (veja o README, seção "Agendamento
automático da Shopee"). Não abre o navegador nem depende do app estar
rodando - só atualiza o arquivo data/app.db.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from promo import db
from promo.shopee_sync import run_sync

if __name__ == "__main__":
    db.init_db()
    summary = run_sync()

    print(
        f"Encontrados: {summary['encontrados']} | "
        f"Novos: {summary['novos']} | "
        f"Atualizados: {summary['atualizados']} | "
        f"Erros: {len(summary['erros'])}"
    )
    for erro in summary["erros"]:
        print(f"  - {erro}")
