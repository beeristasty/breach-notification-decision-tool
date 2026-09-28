"""
Unit tests for the Data Breach Notification Decision Tool.

Run with: pytest test_main.py -v
"""

import pytest
from main import load_state_data, evaluate_state


@pytest.fixture(scope="module")
def state_data():
    return load_state_data()


def test_california_unencrypted_ssn_triggers_notification(state_data):
    """CA should trigger notification for unencrypted SSN regardless of record count."""
    result = evaluate_state(
        state_info=state_data["CA"],
        data_types=["ssn"],
        records_affected=10,
        encrypted=False,
        key_compromised=False,
    )
    assert result["triggered"] is True
    assert result["ag_notification_required"] is False  # below 500 threshold


def test_encrypted_data_with_intact_key_does_not_trigger(state_data):
    """Encrypted data with an uncompromised key should hit the safe harbor and not trigger notice."""
    result = evaluate_state(
        state_info=state_data["NY"],
        data_types=["ssn"],
        records_affected=5000,
        encrypted=True,
        key_compromised=False,
    )
    assert result["triggered"] is False


def test_encrypted_data_with_compromised_key_still_triggers(state_data):
    """Encrypted data with a compromised key should defeat the safe harbor and trigger notice."""
    result = evaluate_state(
        state_info=state_data["NY"],
        data_types=["ssn"],
        records_affected=5000,
        encrypted=True,
        key_compromised=True,
    )
    assert result["triggered"] is True


def test_texas_deadline_is_fixed_60_days(state_data):
    """Texas has a fixed 60-day statutory deadline, unlike CA/NY's reasonable-time standard."""
    result = evaluate_state(
        state_info=state_data["TX"],
        data_types=["ssn"],
        records_affected=100,
        encrypted=False,
        key_compromised=False,
    )
    assert result["triggered"] is True
    assert result["notification_deadline"] == "60 days"


def test_arkansas_ag_notification_requires_1000_threshold(state_data):
    """Arkansas AG notification should only trigger above 1,000 residents affected."""
    below_threshold = evaluate_state(
        state_info=state_data["AR"],
        data_types=["ssn"],
        records_affected=999,
        encrypted=False,
        key_compromised=False,
    )
    above_threshold = evaluate_state(
        state_info=state_data["AR"],
        data_types=["ssn"],
        records_affected=1000,
        encrypted=False,
        key_compromised=False,
    )
    assert below_threshold["ag_notification_required"] is False
    assert above_threshold["ag_notification_required"] is True


def test_arkansas_has_no_credit_bureau_requirement(state_data):
    """Arkansas statute does not require consumer credit reporting agency notification."""
    result = evaluate_state(
        state_info=state_data["AR"],
        data_types=["ssn"],
        records_affected=5000,
        encrypted=False,
        key_compromised=False,
    )
    assert result["credit_bureau_notification_required"] is False


def test_irrelevant_data_type_does_not_trigger(state_data):
    """If compromised data doesn't match the state's PI definition, notice should not trigger."""
    result = evaluate_state(
        state_info=state_data["CA"],
        data_types=["nonexistent_data_type"],
        records_affected=10000,
        encrypted=False,
        key_compromised=False,
    )
    assert result["triggered"] is False


def test_texas_ag_threshold_is_250_residents(state_data):
    """Texas AG notification threshold should be lower than CA/NY (250 vs 500)."""
    result = evaluate_state(
        state_info=state_data["TX"],
        data_types=["ssn"],
        records_affected=300,
        encrypted=False,
        key_compromised=False,
    )
    assert result["ag_notification_required"] is True