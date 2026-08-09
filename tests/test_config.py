from app.core.config import Settings


def test_render_commit_is_used_as_release_identity(monkeypatch) -> None:
    monkeypatch.delenv("APP_RELEASE_SHA", raising=False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)

    settings = Settings(_env_file=None)

    assert settings.app_release_sha == "a" * 40


def test_explicit_release_identity_takes_priority(monkeypatch) -> None:
    monkeypatch.setenv("APP_RELEASE_SHA", "local-check")
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)

    settings = Settings(_env_file=None)

    assert settings.app_release_sha == "local-check"


def test_openrouter_key_alias_is_secret_and_environment_driven(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_MODEL", "openrouter/free")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-secret-value")

    settings = Settings(_env_file=None)

    assert settings.llm_provider == "openrouter"
    assert settings.llm_model == "openrouter/free"
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "synthetic-secret-value"
    assert "synthetic-secret-value" not in repr(settings)
