"""Coleta os dados meteorológicos diários na API histórica do Open-Meteo.

O que este script faz:
1. Monta a requisição com as coordenadas, o período, as variáveis e o fuso.
2. Chama a API com Requests.
3. Grava a resposta exatamente como chegou, em JSON, em dados/brutos/.
4. Grava um arquivo de metadados com a data da coleta e os parâmetros usados.

Se o JSON já existir, o script não sobrescreve. Assim a resposta original
fica preservada. Para coletar de novo, rode com --forcar.

Uso:
    python src/coleta.py
    python src/coleta.py --forcar
"""

import argparse
import json
import sys
from datetime import datetime

import requests

import config


def montar_parametros() -> dict:
    return {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "start_date": config.DATA_INICIO,
        "end_date": config.DATA_FIM,
        "daily": ",".join(config.VARIAVEIS.keys()),
        "timezone": config.FUSO_HORARIO,
    }


def coletar(forcar: bool = False) -> None:
    if config.ARQUIVO_JSON.exists() and not forcar:
        print(f"O arquivo {config.ARQUIVO_JSON.name} já existe. Nada foi baixado.")
        print("Para coletar de novo e sobrescrever, use: python src/coleta.py --forcar")
        return

    parametros = montar_parametros()
    print(f"Consultando {config.URL_API}")
    print(f"Parâmetros: {parametros}")

    resposta = requests.get(config.URL_API, params=parametros, timeout=60)
    if resposta.status_code != 200:
        print(f"A API respondeu com erro {resposta.status_code}: {resposta.text[:300]}")
        sys.exit(1)

    # Confere se a resposta é um JSON com o bloco "daily" antes de gravar
    try:
        conteudo = resposta.json()
    except ValueError:
        print("A resposta não é um JSON válido. Nada foi gravado.")
        sys.exit(1)
    if "daily" not in conteudo:
        print(f"A resposta não trouxe o bloco 'daily': {str(conteudo)[:300]}")
        sys.exit(1)

    config.PASTA_BRUTOS.mkdir(parents=True, exist_ok=True)

    # Grava o texto original, sem reformatar nem alterar nenhum valor
    config.ARQUIVO_JSON.write_text(resposta.text, encoding="utf-8")

    metadados = {
        "fonte": config.FONTE,
        "url_requisicao": resposta.url,
        "parametros": parametros,
        "localidade": config.LOCALIDADE,
        "coletado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status_http": resposta.status_code,
        "arquivo_json": config.ARQUIVO_JSON.name,
        "dias_recebidos": len(conteudo["daily"].get("time", [])),
    }
    config.ARQUIVO_METADADOS.write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Resposta original gravada em {config.ARQUIVO_JSON.relative_to(config.RAIZ)}")
    print(f"Metadados gravados em {config.ARQUIVO_METADADOS.relative_to(config.RAIZ)}")
    print(f"Dias recebidos: {metadados['dias_recebidos']}")
    print(f"Coleta feita em: {metadados['coletado_em']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coleta dados do Open-Meteo.")
    parser.add_argument(
        "--forcar", action="store_true", help="sobrescreve o JSON já coletado"
    )
    args = parser.parse_args()
    coletar(forcar=args.forcar)
