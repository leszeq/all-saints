"""
Unit tests for domain models.
"""

from uuid import uuid4

from src.domain.geography.models import Country
from src.domain.hagiography.models import Person, PersonType, Gender
from src.domain.identity.models import Permission, Role, User, UserStatus


def test_user_model_permissions():
    user = User(
        email="editor@all-saints.local",
        hashed_password="hash",
        full_name="Test Editor",
        status=UserStatus.ACTIVE,
    )

    assert user.is_active is True
    assert user.is_locked is False
    assert len(user.get_permissions()) == 0


def test_person_model_defaults():
    person = Person(
        canonical_name="Św. Franciszek z Asyżu",
        slug="sw-franciszek-z-asyzu",
        person_type=PersonType.SAINT,
        gender=Gender.MALE,
    )

    assert person.canonical_name == "Św. Franciszek z Asyżu"
    assert person.person_type == PersonType.SAINT
    assert person.gender == Gender.MALE
    assert person.status == "draft"


def test_country_model():
    country = Country(
        name_pl="Polska",
        name_en="Poland",
        name_la="Polonia",
        iso_code_alpha2="PL",
        iso_code_alpha3="POL",
    )

    assert country.name_pl == "Polska"
    assert country.iso_code_alpha2 == "PL"
    assert country.is_historical is False
