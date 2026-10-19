from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import (
    DUMMY_HASH,
    hash_password,
    hash_token,
    needs_rehash,
    new_token,
    verify_password,
)
from app.models.owner import Owner
from app.models.owner_session import OwnerSession
from app.services.owner import (
    OwnerExistsError,
    WeakPasswordError,
    create_owner,
    reset_password,
)

PASSWORD = "correct horse battery"


# ---------- security helpers ----------

def test_hash_is_not_the_password_and_verifies():
    hashed = hash_password(PASSWORD)
    assert PASSWORD not in hashed
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, PASSWORD) is True
    assert verify_password(hashed, "wrong password!!") is False


def test_same_password_gives_different_hashes():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_with_garbage_hash_is_false_not_error():
    assert verify_password("not-a-hash", PASSWORD) is False
    assert verify_password("", PASSWORD) is False


def test_dummy_hash_never_matches():
    assert verify_password(DUMMY_HASH, PASSWORD) is False


def test_fresh_hash_needs_no_rehash():
    assert needs_rehash(hash_password(PASSWORD)) is False


def test_tokens_are_long_unique_and_hashed_deterministically():
    first, second = new_token(), new_token()
    assert first != second
    assert len(first) >= 40
    assert hash_token(first) == hash_token(first)
    assert hash_token(first) != hash_token(second)
    assert len(hash_token(first)) == 64
    assert first not in hash_token(first)


# ---------- owner service ----------

def test_create_owner_stores_hash_not_password(db_session):
    owner = create_owner(db_session, "  danish  ", PASSWORD)
    assert owner.username == "danish"
    assert owner.password_hash != PASSWORD
    assert PASSWORD not in owner.password_hash
    assert verify_password(owner.password_hash, PASSWORD) is True


def test_second_owner_refused(db_session):
    create_owner(db_session, "danish", PASSWORD)
    with pytest.raises(OwnerExistsError):
        create_owner(db_session, "other", PASSWORD)
    assert len(db_session.scalars(select(Owner)).all()) == 1


def test_weak_password_refused(db_session):
    with pytest.raises(WeakPasswordError):
        create_owner(db_session, "danish", "short")
    assert db_session.scalars(select(Owner)).all() == []


def test_blank_username_refused(db_session):
    with pytest.raises(ValueError):
        create_owner(db_session, "   ", PASSWORD)


def test_reset_password_changes_hash_and_signs_out_everywhere(db_session):
    owner = create_owner(db_session, "danish", PASSWORD)
    old_hash = owner.password_hash
    db_session.add(
        OwnerSession(
            owner_id=owner.id,
            token_hash=hash_token(new_token()),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db_session.commit()

    reset_password(db_session, "danish", "another long password")

    db_session.refresh(owner)
    assert owner.password_hash != old_hash
    assert verify_password(owner.password_hash, "another long password")
    assert db_session.scalars(select(OwnerSession)).all() == []


def test_reset_unknown_owner(db_session):
    with pytest.raises(LookupError):
        reset_password(db_session, "nobody", PASSWORD)


def test_reset_with_weak_password_changes_nothing(db_session):
    owner = create_owner(db_session, "danish", PASSWORD)
    old_hash = owner.password_hash
    with pytest.raises(WeakPasswordError):
        reset_password(db_session, "danish", "short")
    db_session.refresh(owner)
    assert owner.password_hash == old_hash