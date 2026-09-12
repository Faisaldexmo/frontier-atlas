from pathlib import Path

from src.storage.json_storage import JSONStorage


def test_save_and_load(tmp_path: Path):
    """Test saving and loading JSON records."""

    file_path = tmp_path / "test_data.json"

    storage = JSONStorage(file_path)

    records = [
        {
            "title": "Test Research Paper",
            "authors": ["Test Author"],
            "github_stars": 10,
        },
        {
            "title": "Another Research Paper",
            "authors": ["Another Author"],
            "github_stars": 25,
        },
    ]

    storage.save(records)

    loaded_records = storage.load()

    assert loaded_records == records


def test_count(tmp_path: Path):
    """Test counting stored records."""

    file_path = tmp_path / "test_data.json"

    storage = JSONStorage(file_path)

    records = [
        {"title": "Paper One"},
        {"title": "Paper Two"},
        {"title": "Paper Three"},
    ]

    storage.save(records)

    assert storage.count() == 3


def test_missing_file(tmp_path: Path):
    """Test loading when the storage file does not exist."""

    file_path = tmp_path / "missing.json"

    storage = JSONStorage(file_path)

    assert storage.load() == []