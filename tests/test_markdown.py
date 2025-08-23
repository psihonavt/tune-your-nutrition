from datetime import date
import shutil
from pathlib import Path

import pytest

from nutrition101.markdown import NotesManipulator

from .fixtures import NBreakdownFactory


@pytest.fixture()
def daily_notes() -> str:
    return "daily1.md"


@pytest.fixture()
def nutrition_dir() -> str:
    return "n101"


@pytest.fixture()
def kbs() -> str:
    return "A Knowledge Base"


@pytest.fixture()
def staged_notes_file(daily_notes: str):
    data_dir = Path(__file__).parent / "data/"
    staging_area = data_dir / "staging/"
    shutil.rmtree(staging_area, ignore_errors=True)
    staging_area.mkdir()
    staged_notes_file = staging_area / daily_notes
    shutil.copy(data_dir / daily_notes, staged_notes_file)
    yield staged_notes_file
    shutil.rmtree(staging_area)


@pytest.fixture()
def nm(staged_notes_file: str, nutrition_dir: str):
    return NotesManipulator(staged_notes_file, nutrition_dir)


def test_it_reads_daily_entries(nm: NotesManipulator):
    assert len(nm.source_entries) == 3
    jul_01 = nm.source_entries[0]
    assert jul_01.date == date(2025, 7, 1)
    breakfast, snack, lunch, dinner, tea = [s for s in jul_01.sections if s.is_meal]
    assert breakfast.get_meal_name() == "breakfast"
    assert snack.get_meal_name() == "snack"
    assert lunch.get_meal_name() == "lunch"
    assert dinner.get_meal_name() == "dinner"
    assert tea.get_meal_name() == "tea"


def test_it_writes_markdown(
    nm: NotesManipulator, staged_notes_file: str, nutrition_dir: str
):
    jul_01 = nm.source_entries[0]
    breakfast, snack, lunch, dinner, tea = [s for s in jul_01.sections if s.is_meal]

    breakfast_b, snack_b, lunch_b, dinner_b, tea_b = NBreakdownFactory.build_batch(5)
    nm.add_meal_breakdown(jul_01.date, breakfast, breakfast_b)
    nm.add_meal_breakdown(jul_01.date, snack, snack_b)
    nm.add_meal_breakdown(jul_01.date, lunch, lunch_b)
    nm.add_meal_breakdown(jul_01.date, dinner, dinner_b)
    nm.add_meal_breakdown(jul_01.date, tea, tea_b)
    nm.write_notes(None)

    nm = NotesManipulator(staged_notes_file, nutrition_dir)
    jul_01 = nm.source_entries[0]
    breakfast, snack, lunch, dinner, tea = [s for s in jul_01.sections if s.is_meal]
    assert all(s.has_breakdown_link for s in (breakfast, snack, lunch, dinner, tea))

    jul_01_breakdowns = nm.n101_entries[0]
    assert next((s for s in jul_01_breakdowns.sections if s.is_daily_n_breakdown), None)
    assert len([s for s in jul_01_breakdowns.sections if s.is_meal_n_breakdown]) == 5
