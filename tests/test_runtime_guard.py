from pathlib import Path

from conftest import runtime_data_changes, snapshot_runtime_data


def test_runtime_guard_allows_absent_directory_that_stays_absent(tmp_path: Path) -> None:
    directory = tmp_path / ".attractor"
    before = snapshot_runtime_data(directory)
    after = snapshot_runtime_data(directory)

    assert runtime_data_changes(before, after) == []


def test_runtime_guard_allows_preexisting_untouched_directory(tmp_path: Path) -> None:
    directory = tmp_path / ".attractor"
    directory.mkdir()
    (directory / "audit.sqlite3").write_bytes(b"preexisting audit data")

    before = snapshot_runtime_data(directory)
    after = snapshot_runtime_data(directory)

    assert runtime_data_changes(before, after) == []


def test_runtime_guard_detects_directory_created_during_session(tmp_path: Path) -> None:
    directory = tmp_path / ".attractor"
    before = snapshot_runtime_data(directory)
    directory.mkdir()
    (directory / "audit.sqlite3").write_bytes(b"new audit data")
    after = snapshot_runtime_data(directory)

    changes = runtime_data_changes(before, after)
    assert ".attractor/ directory created during the test session" in changes
    assert ".attractor/audit.sqlite3 created" in changes


def test_runtime_guard_detects_preexisting_file_modified(tmp_path: Path) -> None:
    directory = tmp_path / ".attractor"
    directory.mkdir()
    file_path = directory / "audit.sqlite3"
    file_path.write_bytes(b"original data")

    before = snapshot_runtime_data(directory)
    file_path.write_bytes(b"modified data")
    after = snapshot_runtime_data(directory)

    assert ".attractor/audit.sqlite3 modified (size/mtime/content hash changed)" in (
        runtime_data_changes(before, after)
    )
