from pathlib import Path

import pytest

from trader_factory.simulation.internal_backtest import resolve_dataset_tag


def write_dataset_files(root: Path, tag: str) -> None:
    (root / f"prices_{tag}_day_-1.csv").write_text("header\n")
    (root / f"trades_{tag}_day_-1.csv").write_text("header\n")


def test_resolve_dataset_tag_single_dataset(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")
    assert resolve_dataset_tag(tmp_path) == "round_0"


def test_resolve_dataset_tag_multiple_datasets_requires_explicit_tag(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")
    write_dataset_files(tmp_path, "round_1")

    with pytest.raises(ValueError):
        resolve_dataset_tag(tmp_path)


def test_resolve_dataset_tag_accepts_explicit_valid_tag(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")
    write_dataset_files(tmp_path, "round_1")

    assert resolve_dataset_tag(tmp_path, "round_1") == "round_1"


def test_resolve_dataset_tag_rejects_unknown_tag(tmp_path: Path) -> None:
    write_dataset_files(tmp_path, "round_0")

    with pytest.raises(FileNotFoundError):
        resolve_dataset_tag(tmp_path, "missing")
