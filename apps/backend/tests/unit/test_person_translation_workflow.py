"""Policy and input-contract coverage for editorial person translations."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.application.commands.person_translations import (
    CreatePersonTranslationCommand,
    UpdatePersonTranslationCommand,
)
from src.domain.identity.models import SystemRole
from src.domain.identity.rbac import ROLE_PERMISSIONS


def test_translation_commands_normalize_locale_and_reject_empty_content() -> None:
    command = CreatePersonTranslationCommand(
        language_code="EN_us",
        canonical_name="  Saint Rita of Cascia  ",
        expected_person_version=3,
    )

    assert command.language_code == "en-us"
    assert command.canonical_name == "Saint Rita of Cascia"

    with pytest.raises(ValidationError):
        CreatePersonTranslationCommand(
            language_code="en",
            summary="   ",
            expected_person_version=1,
        )

    with pytest.raises(ValidationError):
        UpdatePersonTranslationCommand(
            expected_person_version=2,
            expected_version=1,
        )


def test_translation_role_separates_authoring_from_review() -> None:
    translator = ROLE_PERMISSIONS[SystemRole.TRANSLATOR]
    reviewer = ROLE_PERMISSIONS[SystemRole.REVIEWER]
    editor = ROLE_PERMISSIONS[SystemRole.EDITOR]

    assert {
        "translations:read",
        "translations:create",
        "translations:update",
        "translations:delete",
    } <= translator
    assert "persons:review" not in translator

    assert "translations:read" in reviewer
    assert "translations:update" not in reviewer
    assert "translations:read" in editor
    assert "translations:update" not in editor
