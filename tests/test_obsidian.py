from datetime import date
import shutil
from pathlib import Path

import pytest
from flexmock import flexmock

from nutrition101.llm.models import ILLMAnalyzer
from nutrition101.obsidian import NotesManipulator, ObsidianNotesEnricher

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


@pytest.fixture()
def notes_enricher(llm_analyzer: ILLMAnalyzer):
    return ObsidianNotesEnricher(analyzer=llm_analyzer)


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


def test_it_enriches_notes(
    staged_notes_file: str,
    nutrition_dir: str,
    llm_analyzer: ILLMAnalyzer,
    notes_enricher: ObsidianNotesEnricher,
):
    knowledge_base = "A knowledge_base"
    nm = NotesManipulator(staged_notes_file, nutrition_dir)
    assert not nm.n101_entries

    for de in nm.source_entries:
        meal_descriptions = [s.get_meal_description() for s in de.sections if s.is_meal]
        flexmock(llm_analyzer).should_receive("get_meal_breakdowns").with_args(
            meal_descriptions, knowledge_base
        ).and_return(NBreakdownFactory.build_batch(len(meal_descriptions))).once()

    notes_enricher.enrich_notes(
        notes_file=staged_notes_file,
        nutrition_dir=nutrition_dir,
        knowledge_base=knowledge_base,
        only_date=None,
        override_existing=False,
        write_notes_to=None,
    )

    nm = NotesManipulator(staged_notes_file, nutrition_dir)
    assert nm.n101_entries

    # enriching already enriched notes shouldn't call the LLM
    notes_enricher.enrich_notes(
        notes_file=staged_notes_file,
        nutrition_dir=nutrition_dir,
        knowledge_base=knowledge_base,
        only_date=None,
        override_existing=False,
        write_notes_to=None,
    )
    flexmock(llm_analyzer).should_receive("get_meal_breakdowns").never()

    # modify the description of one of the already enriched meal sections, it should call LLM again
    meal_description = next(
        s for s in nm.source_entries[0].sections if s.is_meal
    ).content
    updated_meal_description = f"{meal_description} - updated"
    staged_notes_file_p = Path(staged_notes_file)

    staged_notes_file_p.write_text(
        staged_notes_file_p.read_text().replace(
            meal_description, updated_meal_description
        )
    )

    class _M:
        def __eq__(self, other: str) -> bool:
            return "- updated" in other

    flexmock(llm_analyzer).should_receive("get_meal_breakdowns").with_args(
        [_M()], knowledge_base
    ).and_return([NBreakdownFactory.build()]).once()

    notes_enricher.enrich_notes(
        notes_file=staged_notes_file,
        nutrition_dir=nutrition_dir,
        knowledge_base=knowledge_base,
        only_date=None,
        override_existing=False,
        write_notes_to=None,
    )
