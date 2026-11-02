import pytest

from pybi.config import Settings


def test_settings_read_supported_environment_variables(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("PYBI_JWT_SECRET", "test-secret")
    monkeypatch.setenv("DUCKDB_THREADS", "3")
    monkeypatch.setenv("DUCKDB_MAX_MEMORY", "1GB")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    settings = Settings(_env_file=None)

    assert settings.data_dir == str(tmp_path / "data")
    assert settings.exports_dir == str(tmp_path / "exports")
    assert settings.jwt_secret == "test-secret"
    assert settings.duckdb_threads == 3
    assert settings.duckdb_max_memory == "1GB"
    assert settings.database_url == "sqlite:///test.db"
    assert settings.redis_url == "redis://localhost:6379/0"


@pytest.mark.parametrize("secret", [None, "", "short", "x" * 31])
def test_production_settings_reject_missing_or_short_jwt_secret(monkeypatch, secret):
    monkeypatch.setenv("PYBI_ENV", "production")
    if secret is None:
        monkeypatch.delenv("PYBI_JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("PYBI_JWT_SECRET", secret)

    with pytest.raises(ValueError, match="PYBI_JWT_SECRET"):
        Settings(_env_file=None)


def test_production_settings_accept_a_32_character_jwt_secret(monkeypatch):
    monkeypatch.setenv("PYBI_ENV", "production")
    monkeypatch.setenv("PYBI_JWT_SECRET", "x" * 32)

    assert Settings(_env_file=None).jwt_secret == "x" * 32
