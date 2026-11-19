"""Executa as consultas de sql/consultas.sql no banco e mostra os resultados.

Cada consulta começa com um comentário no formato "-- [CÓDIGO] descrição".
Os resultados também são gravados em dados/processados/resultados_consultas.txt,
para servir de evidência no relatório.

Uso:
    python src/analise.py
"""

import re
import sys

import duckdb

import config

ARQUIVO_RESULTADOS = config.PASTA_PROCESSADOS / "resultados_consultas.txt"


def separar_consultas(texto: str) -> list[tuple[str, str]]:
    """Divide o arquivo SQL em (título, consulta) usando os marcadores [CÓDIGO]."""
    blocos = re.split(r"\n(?=-- \[)", texto)
    consultas = []
    for bloco in blocos:
        if not bloco.strip().startswith("-- ["):
            continue
        linhas = bloco.strip().splitlines()
        titulo = linhas[0].removeprefix("-- ").strip()
        sql = "\n".join(linhas[1:]).strip()
        if sql:
            consultas.append((titulo, sql))
    return consultas


def main() -> None:
    if not config.ARQUIVO_BANCO.exists():
        print("Banco não encontrado. Rode antes: python src/coleta.py e python src/banco.py")
        sys.exit(1)

    con = duckdb.connect(str(config.ARQUIVO_BANCO), read_only=True)
    saida = []
    for titulo, sql in separar_consultas(config.ARQUIVO_SQL.read_text(encoding="utf-8")):
        resultado = con.sql(sql).df()
        saida.append(f"=== {titulo}")
        saida.append(resultado.to_string(index=False))
        saida.append("")
    con.close()

    texto = "\n".join(saida)
    print(texto)
    ARQUIVO_RESULTADOS.write_text(texto, encoding="utf-8")
    print(f"Resultados gravados em {ARQUIVO_RESULTADOS.relative_to(config.RAIZ)}")


if __name__ == "__main__":
    main()
