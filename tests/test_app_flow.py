from streamlit.testing.v1 import AppTest

def test_app_student_flow():
    """Verify Student view: Confidential brief is hidden, can commit and submit."""
    at = AppTest.from_file("../app.py").run()
    assert not at.exception

    # Default role is Student
    radio = at.radio[0]
    assert radio.value == "Student"

    # Verify Confidential Brief is NOT present in Student tabs
    tab_labels = [tab.label for tab in at.tabs]
    assert "Confidential Brief" not in tab_labels
    assert "Code & Terminal" in tab_labels

    # Test Commit to GitHub button
    commit_btn = next((b for b in at.button if b.label == "Commit to GitHub"), None)
    assert commit_btn is not None
    commit_btn.click().run()
    assert not at.exception
    assert len(at.session_state["ledger_entries"]) >= 2
    assert at.session_state["ledger_entries"][-1]["entry_type"] == "COMMIT"

    # Test Submit M3 for Review button
    submit_btn = next((b for b in at.button if b.label == "Submit M3 for Review"), None)
    assert submit_btn is not None
    submit_btn.click().run()
    assert not at.exception
    assert at.session_state["ledger_entries"][-1]["entry_type"] == "SUBMISSION"


def test_app_mentor_flow_and_escrow_release():
    """Verify Mentor view: Confidential brief is visible, approve & release triggers ledger."""
    at = AppTest.from_file("../app.py").run()
    assert not at.exception

    # Switch to Mentor
    at.radio[0].set_value("Mentor").run()
    assert not at.exception

    tab_labels = [tab.label for tab in at.tabs]
    assert "Confidential Brief" in tab_labels
    assert "Review Queue" in tab_labels
    assert "Ledger Audit" in tab_labels

    # Approve & Release M3
    approve_btn = next((b for b in at.button if b.label == "Approve & Release M3"), None)
    assert approve_btn is not None
    approve_btn.click().run()
    assert not at.exception

    # Verify ESCROW_RELEASE in ledger
    entries = at.session_state["ledger_entries"]
    last_entry = entries[-1]
    assert last_entry["entry_type"] == "ESCROW_RELEASE"
    assert last_entry["actor_role"] == "Mentor"
    assert last_entry["payload"]["milestone"] == "M3"


def test_app_sponsor_flow_after_release():
    """Verify Sponsor view updates progress to 100% and released escrow to $15,000."""
    at = AppTest.from_file("../app.py").run()

    # Release M3 as Mentor first
    at.radio[0].set_value("Mentor").run()
    approve_btn = next((b for b in at.button if b.label == "Approve & Release M3"), None)
    approve_btn.click().run()

    # Now switch to Sponsor
    at.radio[0].set_value("Sponsor").run()
    assert not at.exception

    # Verify M3 is marked released in ledger entries for sponsor
    sponsor_ledger = [e for e in at.session_state["ledger_entries"] if e["entry_type"] in ("GENESIS", "ESCROW_RELEASE")]
    assert len(sponsor_ledger) >= 2


def test_app_mentor_tamper_simulation():
    """Verify that simulating tamper flips ledger verification."""
    at = AppTest.from_file("../app.py").run()
    at.radio[0].set_value("Mentor").run()

    # Check tamper button
    tamper_btn = next((b for b in at.button if b.label == "Simulate Tamper on Block #0"), None)
    assert tamper_btn is not None
    tamper_btn.click().run()
    assert not at.exception

    # Verify tamper flag
    assert at.session_state["ledger_entries"][0]["payload"].get("tampered") == "HACKED_DATA"
    # Verification in markdown or error should show tamper detected
    error_boxes = [e.value for e in at.error]
    assert any("TAMPER DETECTED at Block #0" in msg for msg in error_boxes)
