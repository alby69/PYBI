"""Unit tests for CSV separator detection and handling in the ETL executor."""

from pybi.etl.connectors.csv import detect_csv_separator, read_csv
from pybi.etl.executor import execute_dag
import polars as pl


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_detect_semicolon(tmp_path):
    path = _write(tmp_path, "a.csv", "region;revenue\nEU;10\nUS;20\n")
    assert detect_csv_separator(path) == ";"


def test_detect_tab(tmp_path):
    path = _write(tmp_path, "a.csv", "region\trevenue\nEU\t10\nUS\t20\n")
    assert detect_csv_separator(path) == "\t"


def test_detect_pipe(tmp_path):
    path = _write(tmp_path, "a.csv", "region|revenue\nEU|10\nUS|20\n")
    assert detect_csv_separator(path) == "|"


def test_detect_defaults_to_comma_when_ambiguous(tmp_path):
    path = _write(tmp_path, "a.csv", "a,b,c\n1,2,3\n4,5,6\n")
    assert detect_csv_separator(path) == ","


def test_read_csv_auto_sniffs_semicolon(tmp_path):
    path = _write(tmp_path, "a.csv", "region;revenue\nEU;10\n")
    df = read_csv(path)
    assert list(df.columns) == ["region", "revenue"]
    assert df["revenue"].sum() == 10


def test_read_csv_explicit_separator_name(tmp_path):
    path = _write(tmp_path, "a.csv", "a,b\n1,2\n")
    df = read_csv(path, separator="comma")
    assert list(df.columns) == ["a", "b"]


def test_read_csv_explicit_raw_separator_char(tmp_path):
    path = _write(tmp_path, "a.csv", "a,b\n1,2\n")
    df = read_csv(path, separator=",")
    assert list(df.columns) == ["a", "b"]


def test_execute_dag_reads_semicolon_csv_automatically(tmp_path):
    _write(tmp_path, "records.csv", "region;revenue\nEU;10\nUS;20\n")
    dag = {
        "nodes": [
            {
                "id": "n1",
                "label": "CSV Source (records.csv)",
                "data": {"node_type": "DataSource", "source_type": "csv", "file_path": "records.csv"},
            },
            {
                "id": "n2",
                "label": "DuckDB Table (records)",
                "data": {"node_type": "Output", "table_name": "records"},
            },
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }

    result = execute_dag(dag, base_dir=str(tmp_path))

    assert result.status == "success"
    assert set(result.output_tables["records"].columns) == {"region", "revenue"}
    assert result.output_tables["records"].height == 2


def test_execute_dag_uses_explicit_separator_when_configured(tmp_path):
    _write(tmp_path, "pipes.csv", "a|b\n1|2\n3|4\n")
    dag = {
        "nodes": [
            {
                "id": "n1",
                "data": {
                    "node_type": "DataSource",
                    "source_type": "csv",
                    "file_path": "pipes.csv",
                    "csv_separator": "pipe",
                },
            },
            {
                "id": "n2",
                "data": {"node_type": "Output", "table_name": "pipes"},
            },
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }

    result = execute_dag(dag, base_dir=str(tmp_path))

    assert result.status == "success"
    assert set(result.output_tables["pipes"].columns) == {"a", "b"}
    assert result.output_tables["pipes"].height == 2


def test_read_csv_normalises_comma_decimals_after_parse_failure(tmp_path):
    path = _write(
        tmp_path,
        "prezzi.csv",
        "Prodotto;Prezzo\nGPL;330\nGPL;362,14\nAZOTO;21,84\n",
    )
    df = read_csv(path)

    assert list(df.columns) == ["Prodotto", "Prezzo"]
    assert df["Prezzo"].dtype == pl.Float64
    assert df["Prezzo"].to_list() == [330.0, 362.14, 21.84]


def test_read_csv_keeps_free_text_with_commas(tmp_path):
    path = _write(
        tmp_path,
        "clienti.csv",
        "Nome;Citta\n\"Smith, John\";Roma\nAnna;Bari\n",
    )
    df = read_csv(path)

    assert df["Nome"].dtype == pl.Utf8
    assert df["Nome"].to_list() == ["Smith, John", "Anna"]
    assert df["Citta"].dtype == pl.Utf8


def test_normalisation_handles_thousands_and_decimal_comma(tmp_path):
    path = _write(tmp_path, "importi.csv", "Importo;Codice\n1.234,56;A\n980;B\n")
    df = read_csv(path)

    assert df["Importo"].dtype == pl.Float64
    assert df["Importo"].to_list() == [1234.56, 980.0]
    assert df["Codice"].to_list() == ["A", "B"]