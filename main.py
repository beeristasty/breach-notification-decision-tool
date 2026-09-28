#!/usr/bin/env python3
"""
Data Breach Notification Decision Tool
----------------------------------------
Analyzes a hypothetical data breach scenario against a subset of state
breach notification statutes (CA, NY, TX, AR) and outputs which states'
notification requirements are triggered, along with deadlines and
regulator/credit bureau notification obligations.

DISCLAIMER: This tool is for educational/portfolio purposes only.
It does not constitute legal advice. Always consult qualified counsel
and verify current statutory text before relying on this analysis.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


DATA_PATH = Path(__file__).parent / "data" / "breach_notification_rules.json"


def load_state_data():
    with open(DATA_PATH, "r") as f:
        data = json.load(f)
    return {state["state_code"]: state for state in data["states"]}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Assess data breach notification obligations across CA, NY, TX, and AR."
    )
    parser.add_argument(
        "--states",
        nargs="+",
        required=True,
        help="State codes affected by the breach (e.g., CA NY TX AR)",
    )
    parser.add_argument(
        "--data-types",
        nargs="+",
        required=True,
        help="Types of data compromised (e.g., ssn drivers_license_or_state_id medical_information)",
    )
    parser.add_argument(
        "--records-affected",
        type=int,
        required=True,
        help="Total number of individuals affected across all states",
    )
    parser.add_argument(
        "--encrypted",
        action="store_true",
        help="Flag if the compromised data was encrypted",
    )
    parser.add_argument(
        "--key-compromised",
        action="store_true",
        help="Flag if the encryption key was also compromised (defeats safe harbor)",
    )
    return parser.parse_args()


def evaluate_state(state_info, data_types, records_affected, encrypted, key_compromised):
    """
    Determines whether notification is triggered for a given state and
    returns a structured result dict.
    """
    result = {
        "state_code": state_info["state_code"],
        "state_name": state_info["state_name"],
        "statute_citation": state_info["statute_citation"],
        "triggered": False,
        "reasoning": [],
        "notification_deadline": None,
        "ag_notification_required": False,
        "credit_bureau_notification_required": False,
    }

    # Step 1: Does any compromised data type match this state's PI definition?
    relevant_elements = set(data_types) & set(state_info["personal_information_elements"])
    if not relevant_elements:
        result["reasoning"].append(
            "No compromised data types match this state's statutory definition of personal information."
        )
        return result

    result["reasoning"].append(
        f"Compromised data types matching statutory PI definition: {', '.join(sorted(relevant_elements))}"
    )

    # Step 2: Encryption safe harbor check
    safe_harbor = state_info["encryption_safe_harbor"]
    if encrypted and safe_harbor["applies"] and not key_compromised:
        result["reasoning"].append(
            f"Encryption safe harbor applies: {safe_harbor['conditions']}"
        )
        return result  # Not triggered — safe harbor defeats notification duty

    if encrypted and key_compromised:
        result["reasoning"].append(
            "Data was encrypted, but encryption key was also compromised — safe harbor does not apply."
        )

    # Step 3: Arkansas-specific risk-of-harm trigger
    if state_info["state_code"] == "AR":
        result["reasoning"].append(
            "Arkansas requires a reasonable likelihood of harm before notification is triggered. "
            "This tool assumes harm likelihood exists once sensitive PI is confirmed compromised — "
            "verify with counsel for a full risk assessment."
        )

    # Step 4: Minimum threshold check
    threshold = state_info["notification_trigger_threshold"]["min_residents_affected"]
    if records_affected < threshold:
        result["reasoning"].append(
            f"Records affected ({records_affected}) below state minimum threshold ({threshold})."
        )
        return result

    # If we reach here, notification is triggered
    result["triggered"] = True

    deadline_info = state_info["notification_deadline"]
    if deadline_info["type"] == "fixed_days":
        result["notification_deadline"] = f"{deadline_info['fixed_days']} days"
    else:
        result["notification_deadline"] = "Reasonable time / without unreasonable delay (no fixed deadline)"

    result["reasoning"].append(
        f"Notification triggered. Deadline: {result['notification_deadline']}"
    )

    # Step 5: AG notification threshold
    ag_info = state_info["attorney_general_notification"]
    if ag_info["required"] and records_affected >= ag_info["threshold_residents"]:
        result["ag_notification_required"] = True
        result["reasoning"].append(
            f"Attorney General notification required (threshold: {ag_info['threshold_residents']} residents)."
        )

    # Step 6: Credit bureau notification threshold
    cb_info = state_info["credit_bureau_notification"]
    if cb_info["required"] and records_affected >= cb_info["threshold_residents"]:
        result["credit_bureau_notification_required"] = True
        result["reasoning"].append(
            f"Consumer credit reporting agency notification required "
            f"(threshold: {cb_info['threshold_residents']} residents)."
        )

    return result


def print_report(results, records_affected):
    print("\n" + "=" * 70)
    print("DATA BREACH NOTIFICATION ANALYSIS REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Total records affected: {records_affected}")
    print("=" * 70)

    triggered_states = [r for r in results if r["triggered"]]

    for r in results:
        print(f"\n--- {r['state_name']} ({r['state_code']}) ---")
        print(f"Statute: {r['statute_citation']}")
        print(f"Notification Triggered: {'YES' if r['triggered'] else 'NO'}")
        for reason in r["reasoning"]:
            print(f"  - {reason}")
        if r["triggered"]:
            print(f"  Deadline: {r['notification_deadline']}")
            print(f"  AG Notification Required: {r['ag_notification_required']}")
            print(f"  Credit Bureau Notification Required: {r['credit_bureau_notification_required']}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    if triggered_states:
        print(f"Notification is triggered in {len(triggered_states)} of {len(results)} state(s) analyzed:")
        for r in sorted(triggered_states, key=lambda x: x["state_code"]):
            print(f"  - {r['state_code']}: deadline = {r['notification_deadline']}")
    else:
        print("Notification is not triggered in any of the analyzed states.")

    print("\nDISCLAIMER: This output is for educational purposes only and does not")
    print("constitute legal advice. Consult qualified counsel before acting on a")
    print("real breach event.\n")


def main():
    args = parse_args()
    all_states = load_state_data()

    invalid_states = [s.upper() for s in args.states if s.upper() not in all_states]
    if invalid_states:
        print(f"Error: Unsupported state code(s): {', '.join(invalid_states)}")
        print(f"Supported states: {', '.join(all_states.keys())}")
        return

    results = []
    for state_code in args.states:
        state_info = all_states[state_code.upper()]
        result = evaluate_state(
            state_info=state_info,
            data_types=args.data_types,
            records_affected=args.records_affected,
            encrypted=args.encrypted,
            key_compromised=args.key_compromised,
        )
        results.append(result)

    print_report(results, args.records_affected)


if __name__ == "__main__":
    main()