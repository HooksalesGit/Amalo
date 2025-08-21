import os


def test_changelog_has_entries():
    root = os.path.dirname(os.path.dirname(__file__))
    changelog = os.path.join(root, "CHANGELOG.md")
    assert os.path.exists(changelog), "CHANGELOG.md should exist"
    with open(changelog) as f:
        lines = f.readlines()
    entries = [line for line in lines if line.strip().startswith("- ")]
    assert entries, "CHANGELOG.md should contain at least one bullet entry"
