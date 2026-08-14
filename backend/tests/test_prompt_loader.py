import pytest
from app.ai.prompt_loader import render_prompt


def test_renders_known_prompt_with_variables() -> None:
    rendered = render_prompt(
        "job_analysis", job_title="Backend Engineer", company="Acme", description="Build things."
    )

    assert "Backend Engineer" in rendered
    assert "Acme" in rendered
    assert "Build things." in rendered
    assert "{{" not in rendered


def test_missing_variable_raises_key_error() -> None:
    with pytest.raises(KeyError):
        render_prompt("job_analysis", job_title="Backend Engineer")
