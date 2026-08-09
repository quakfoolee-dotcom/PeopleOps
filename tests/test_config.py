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
