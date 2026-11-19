# Pasta de dados

- `brutos/`: a resposta original da API Open-Meteo, em JSON, sem nenhuma alteração. Ao lado fica um arquivo de metadados com a data da coleta e os parâmetros usados.
- `processados/`: o que sai do tratamento. Aqui ficam a base tratada (`clima_diario.csv`), o relatório de validação, os resultados das consultas e o banco `observatorio.duckdb`.

Para gerar tudo do zero, a partir da raiz do repositório:

```bash
python src/coleta.py
python src/banco.py
python src/analise.py
```

O `coleta.py` não sobrescreve um JSON que já existe. Assim, a resposta original da coleta usada no relatório fica preservada.
