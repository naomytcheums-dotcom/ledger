from ledger.versioning import data_snapshot, model_version, prompt_version


def test_prompt_version_same_text_same_id():
    assert prompt_version("Answer the question.") == prompt_version("Answer the question.")


def test_prompt_version_different_text_different_id():
    assert prompt_version("Answer the question.") != prompt_version("Answer differently.")


def test_model_version_differs_by_config():
    assert model_version("claude-sonnet-5", {"temperature": 0}) != model_version(
        "claude-sonnet-5", {"temperature": 1}
    )


def test_model_version_same_name_no_config_is_stable():
    assert model_version("claude-sonnet-5") == model_version("claude-sonnet-5", None)


def test_data_snapshot_differs_by_content():
    assert data_snapshot({"docs_version": "v1"}) != data_snapshot({"docs_version": "v2"})
