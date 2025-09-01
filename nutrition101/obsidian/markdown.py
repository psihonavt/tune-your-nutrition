import re
from collections.abc import Sequence
from datetime import date, datetime
from hashlib import md5
from pathlib import Path
from operator import itemgetter
from typing import Any, ClassVar

from nutrition101.domain import NEntry, NBreakdown
from pydantic import BaseModel

from nutrition101.llm.models import ILLMAnalyzer


class DailyEntrySection(BaseModel, Sequence):
    content: str

    def __getitem__(self, key: Any) -> Any:
        return self.lines[key]

    def __len__(self) -> int:
        return len(self.lines)

    @property
    def lines(self) -> list[str]:
        return self.content.splitlines()

    @property
    def is_meal(self) -> bool:
        meal_name = self[0].strip()
        is_linked = meal_name.startswith("[[")
        is_anchor = meal_name.startswith("#" * 6)
        return (is_anchor or is_linked or meal_name.startswith("=")) and len(self) >= 2

    @property
    def is_meal_n_breakdown(self) -> bool:
        return (
            self.content.strip(" ").startswith(
                f"| {DailyEntryNBreakdownSubSection.MEAL_BREAKDOWN_FIRST_COLUMN}"
            )
            and DailyEntryNBreakdownSubSection.from_md_table(self.content) is not None
        )

    @property
    def n_breakdown(self) -> NBreakdown:
        assert self.is_meal_n_breakdown or self.is_daily_n_breakdown
        nb_section = DailyEntryNBreakdownSubSection.from_md_table(self.content)
        assert nb_section
        return nb_section.breakdown

    @property
    def is_breakdown_anchor(self) -> bool:
        return self[0].startswith("######")

    @property
    def has_breakdown_link(self) -> bool:
        return self[0].startswith("[[")

    @property
    def is_daily_n_breakdown(self) -> bool:
        return self.content.strip(" ").startswith(
            f"| {DailyEntryNBreakdownSubSection.DAILY_TOTAL_BREAKDOWN_FIRST_COLUMN}"
        )

    def get_meal_description(self) -> str:
        assert self.is_meal, "Not a meal section"
        return ".".join(self[1:])

    def get_meal_hash(self) -> str:
        assert self.is_meal, "Not a meal section"
        return md5("".join(self[1:]).encode()).hexdigest()

    def get_meal_name(self) -> str:
        assert self.is_meal, f"Not a meal section - {self[0]}"
        if self[0].startswith("[["):
            meal_name = self[0].strip("[]").split("|")[-1]
        elif self[0].startswith("###"):
            meal_name = self[0].strip("# ")
        else:
            meal_name = self[0]
        return meal_name.strip(" =")

    def get_meal_anchor(self) -> str:
        assert self.is_breakdown_anchor, f"Not a meal anchor - {self[0]}"
        assert len(self) == 2, f"Not a meal anchor - {self}"
        return self[1]


class DailyEntryNBreakdownSubSection(BaseModel):
    MEAL_BREAKDOWN_FIRST_COLUMN: ClassVar = "Food Item"
    DAILY_TOTAL_BREAKDOWN_FIRST_COLUMN: ClassVar = "Meal"
    USED_KNOWLEDGE_BASE_MARKER: ClassVar = "[found in kbs]"

    breakdown: NBreakdown
    meal_hash: str
    is_daily_total: bool

    def to_md_table(self) -> str:
        first_column = (
            f"{self.MEAL_BREAKDOWN_FIRST_COLUMN} ({self.meal_hash})"
            if not self.is_daily_total
            else self.DAILY_TOTAL_BREAKDOWN_FIRST_COLUMN
        )
        lines = [
            f"| {first_column} | Calories | Carbs (g) | Sugars (g) | Protein (g) | Fat (g) | Fiber (g) | Sodium (mg) |",
            "|-----------|----------|-----------|------------|-------------|---------|-----------|-------------|",
        ]
        for entry in self.breakdown.entries:
            lines.append(
                f"| {entry.item} {self.USED_KNOWLEDGE_BASE_MARKER if entry.used_knowledge_base else ''} | {entry.calories} | {entry.carbs_g} | {entry.sugars_g}({entry.added_sugars_g}) | {entry.protein_g} | {entry.fat_g} | {entry.fiber_g} | {entry.sodium_mg} |"
            )

        if self.is_daily_total:
            total_calories = sum([e.calories for e in self.breakdown.entries])
            total_carbs = sum([e.carbs_g for e in self.breakdown.entries])
            total_sugars_g = sum([e.sugars_g for e in self.breakdown.entries])
            total_added_sugars_g = sum(
                [e.added_sugars_g for e in self.breakdown.entries]
            )
            total_sugars = f"{total_sugars_g}({total_added_sugars_g})"
            total_protein = sum([e.protein_g for e in self.breakdown.entries])
            total_fat = sum([e.fat_g for e in self.breakdown.entries])
            total_fiber = sum([e.fiber_g for e in self.breakdown.entries])
            total_sodium = sum([e.sodium_mg for e in self.breakdown.entries])
            lines.append(
                f"| **TOTAL** | **{total_calories}** | **{total_carbs}** | **{total_sugars}** | **{total_protein}** | **{total_fat}** | **{total_fiber}** | **{total_sodium}** |"
            )

        return "\n".join(lines)

    @classmethod
    def from_md_table(cls, table: str) -> "DailyEntryNBreakdownSubSection | None":
        lines = table.splitlines()
        if len(lines) < 2:
            return None
        if not lines[0].startswith(f"| {cls.MEAL_BREAKDOWN_FIRST_COLUMN}"):
            return None

        hash_match = re.search(r"\((.*)\)", lines[0].split("|")[1])
        meal_hash = hash_match.group(1) if hash_match else ""
        entries = []
        for line in lines[2:]:
            try:
                (
                    item,
                    calories,
                    carbs_g,
                    sugars,
                    protein_g,
                    fat_g,
                    fiber_g,
                    sodium_mg,
                ) = line.split("|")[1:-1]
                sugars_match = re.match(r"(\d+)\((\d+)\)", sugars.strip())
                if not sugars_match:
                    sugars_g = int(sugars)
                    added_sugars_g = 0
                else:
                    sugars_g = int(sugars_match.group(1))
                    added_sugars_g = int(sugars_match.group(2))

                entries.append(
                    NEntry(
                        item=item,
                        calories=int(calories),
                        carbs_g=int(carbs_g),
                        sugars_g=sugars_g,
                        added_sugars_g=added_sugars_g,
                        protein_g=int(protein_g),
                        fat_g=int(fat_g),
                        fiber_g=int(fiber_g),
                        sodium_mg=int(sodium_mg),
                        used_knowledge_base=cls.USED_KNOWLEDGE_BASE_MARKER in item,
                    )
                )
            except (IndexError, ValueError):
                return None

        n_breakdown = NBreakdown(entries=entries)
        return DailyEntryNBreakdownSubSection(
            is_daily_total=False, breakdown=n_breakdown, meal_hash=meal_hash
        )


class DailyEntry(BaseModel):
    date: date
    sections: list[DailyEntrySection]

    def to_md_content(self) -> str:
        md_sections = [self.date.strftime("%m/%d/%Y")]
        for section in self.sections:
            md_sections.append(section.content)
        return "\n\n".join(md_sections)


class NotesManipulator:
    _DAILY_BREAKDOWN: str = "daily-breakdown"

    def __init__(self, notes_file: str, nutrition_dir: str) -> None:
        self._nutrition_dir = nutrition_dir
        self._source_notes = Path(notes_file)
        self._entries_map = {
            de.date: de
            for de in self._parse_daily_entries(self._source_notes.read_text())
        }
        self._n101_notes = Path(
            self._source_notes.parent / self._nutrition_dir / self._source_notes.name
        )
        self._n101_notes.parent.mkdir(exist_ok=True)
        self._n101_entries_map = {
            de.date: de
            for de in self._parse_daily_entries(
                self._n101_notes.read_text() if self._n101_notes.exists() else ""
            )
        }

    @property
    def source_entries(self) -> list[DailyEntry]:
        return [de for _, de in sorted(self._entries_map.items(), key=itemgetter(0))]

    @property
    def n101_entries(self) -> list[DailyEntry]:
        return [
            de for _, de in sorted(self._n101_entries_map.items(), key=itemgetter(0))
        ]

    def write_notes(self, notes_path: str | None) -> None:
        destination = Path(notes_path) if notes_path else self._source_notes
        md_content = "\n\n".join([de.to_md_content() for de in self.source_entries])
        destination.write_text(md_content)

        md_content = "\n\n".join([de.to_md_content() for de in self.n101_entries])
        self._n101_notes.write_text(md_content)

    @staticmethod
    def _get_date_from_line(line: str) -> date | None:
        date_pattern = r"\b(\d{1,2}/\d{1,2}/\d{4})\b"
        match = re.search(date_pattern, line.strip())
        return match and datetime.strptime(match.group(), "%m/%d/%Y").date()

    def _parse_daily_entries(self, content: str) -> list[DailyEntry]:
        content_lines = content.splitlines()
        current_line = 0
        entries, current_date, current_date_sections, current_section_lines = (
            [],
            None,
            [],
            [],
        )
        while current_line <= len(content_lines) - 1:
            line = content_lines[current_line]
            maybe_date = self._get_date_from_line(line)
            if maybe_date:
                if current_date is not None:
                    entries.append(
                        DailyEntry(date=current_date, sections=current_date_sections)
                    )
                current_date, current_date_sections = maybe_date, []
            elif not line.strip(" \n"):
                if current_section_lines:
                    current_date_sections.append(
                        DailyEntrySection(content="\n".join(current_section_lines))
                    )
                    current_section_lines = []
            else:
                current_section_lines.append(line)
            current_line += 1

        if current_date:
            if current_section_lines:
                current_date_sections.append(
                    DailyEntrySection(content="\n".join(current_section_lines))
                )
            entries.append(
                DailyEntry(date=current_date, sections=current_date_sections)
            )
        return entries

    @staticmethod
    def _generate_meal_anchor(date: date, meal_name: str) -> str:
        return f"^{meal_name}-{date.strftime('%m-%d-%Y')}"

    @staticmethod
    def _generate_meal_anchor_title(meal_name: str) -> str:
        return f"###### {meal_name}"

    def _generate_breakdown_link(self, date: date, meal_name: str) -> str:
        return f"[[{self._nutrition_dir}/{self._n101_notes.name}#{self._generate_meal_anchor(date, meal_name)}|{meal_name}]]"

    def _add_meal_anchor(
        self, daily_entry: DailyEntry, section: DailyEntrySection
    ) -> DailyEntry:
        assert section.is_meal
        sections = daily_entry.sections.copy()
        meal_idx = sections.index(section)
        meal_content = section.lines.copy()
        # always rewrite the anchor in case the nutrition_dir has changed
        meal_name = section.get_meal_name()
        meal_name_anchored = self._generate_breakdown_link(daily_entry.date, meal_name)
        updated_meal_section = DailyEntrySection(
            content="\n".join([meal_name_anchored] + meal_content[1:])
        )
        sections[meal_idx] = updated_meal_section

        # the same with daily breakdown anchor
        existing_daily_link_section = next(
            (
                section
                for section in sections
                if section.has_breakdown_link and self._DAILY_BREAKDOWN in section[0]
            ),
            None,
        )

        daily_link_section = DailyEntrySection(
            content=self._generate_breakdown_link(
                daily_entry.date, self._DAILY_BREAKDOWN
            )
        )

        if not existing_daily_link_section:
            sections.append(daily_link_section)
        else:
            sections[sections.index(existing_daily_link_section)] = daily_link_section

        return DailyEntry(date=daily_entry.date, sections=sections)

    def _add_meal_breakdown(
        self,
        daily_entry: DailyEntry,
        source_section: DailyEntrySection,
        breakdown: NBreakdown,
    ) -> DailyEntry:
        assert source_section.is_meal
        anchor_title = self._generate_meal_anchor_title(source_section.get_meal_name())
        n101_sections = daily_entry.sections.copy()
        if n101_sections:
            if n101_sections[-1].is_daily_n_breakdown:
                assert n101_sections[-2].is_breakdown_anchor, (
                    f"Can't detect the daily breakdown anchor {n101_sections[:-3]}"
                )
            n101_sections = n101_sections[:-2]

        n101_section = next(
            (s for s in daily_entry.sections if s[0] == anchor_title), None
        )
        if not n101_section:
            n101_section = DailyEntrySection(
                content=f"{anchor_title}\n{self._generate_meal_anchor(daily_entry.date, source_section.get_meal_name())}"
            )
            n101_sections.append(n101_section)

        breakdown_section_idx = n101_sections.index(n101_section) + 1
        breakdown_as_table = DailyEntrySection(
            content=DailyEntryNBreakdownSubSection(
                breakdown=breakdown,
                is_daily_total=False,
                meal_hash=source_section.get_meal_hash(),
            ).to_md_table()
        )
        if breakdown_section_idx <= len(n101_sections) - 1:
            if n101_sections[breakdown_section_idx].is_meal_n_breakdown:
                n101_sections[breakdown_section_idx] = breakdown_as_table
            else:
                n101_sections.insert(breakdown_section_idx, breakdown_as_table)
        else:
            n101_sections.append(breakdown_as_table)

        meal_breakdowns = [
            (
                n101_sections[n101_sections.index(mb) - 1].get_meal_name(),
                mb.n_breakdown,
            )
            for mb in n101_sections
            if mb.is_meal_n_breakdown
        ]

        daily_breakdown_table = DailyEntrySection(
            content=DailyEntryNBreakdownSubSection(
                is_daily_total=True,
                breakdown=NBreakdown(
                    entries=[
                        mb.get_total_as_entry(meal_name)
                        for meal_name, mb in meal_breakdowns
                    ]
                ),
                meal_hash="",
            ).to_md_table()
        )
        daily_anchor = DailyEntrySection(
            content="\n".join(
                [
                    self._generate_meal_anchor_title(self._DAILY_BREAKDOWN),
                    self._generate_meal_anchor(daily_entry.date, self._DAILY_BREAKDOWN),
                ]
            )
        )
        n101_sections.extend([daily_anchor, daily_breakdown_table])
        return DailyEntry(date=daily_entry.date, sections=n101_sections)

    def clear_breakdowns(self, date: date) -> None:
        self._n101_entries_map[date] = DailyEntry(date=date, sections=[])

    def add_meal_breakdown(
        self, date: date, section: DailyEntrySection, breakdown: NBreakdown
    ) -> None:
        assert date in self._entries_map, (
            f"There is not daily entry for {date.isoformat()}"
        )
        daily_entry = self._entries_map[date]
        daily_entry = self._add_meal_anchor(daily_entry, section)
        self._entries_map[date] = daily_entry

        n101_daily_entry = self._n101_entries_map.get(
            date, DailyEntry(date=date, sections=[])
        )
        n101_daily_entry = self._add_meal_breakdown(
            n101_daily_entry, section, breakdown
        )
        self._n101_entries_map[date] = n101_daily_entry

    def get_meal_breakdowns(
        self, date: date
    ) -> list[tuple[DailyEntrySection, DailyEntryNBreakdownSubSection | None]]:
        daily_entry = self._entries_map[date]
        n101_daily_entry = self._n101_entries_map.get(
            date, DailyEntry(date=date, sections=[])
        )
        result = []
        for section in daily_entry.sections:
            if section.is_meal:
                n_breakdown = None
                n101_anchor = next(
                    (
                        ns
                        for ns in n101_daily_entry.sections
                        if ns.is_meal and ns.get_meal_name() == section.get_meal_name()
                    ),
                    None,
                )
                if n101_anchor:
                    maybe_breakdown_idx = (
                        n101_daily_entry.sections.index(n101_anchor) + 1
                    )
                    if maybe_breakdown_idx <= len(n101_daily_entry.sections) - 1:
                        next_section = n101_daily_entry.sections[maybe_breakdown_idx]
                        if next_section.is_meal_n_breakdown:
                            breakdown_section = (
                                DailyEntryNBreakdownSubSection.from_md_table(
                                    next_section.content
                                )
                            )
                            if (
                                breakdown_section
                                and breakdown_section.meal_hash
                                == section.get_meal_hash()
                            ):
                                n_breakdown = breakdown_section
                result.append((section, n_breakdown))
        return result

    def do_all_meals_have_breakdowns(self, date: date) -> bool:
        return all(
            n_breakdown is not None for _, n_breakdown in self.get_meal_breakdowns(date)
        )


class ObsidianNotesEnricher:
    def __init__(self, analyzer: ILLMAnalyzer) -> None:
        self._analyzer = analyzer

    def enrich_notes(
        self,
        notes_file: str,
        knowledge_base: str,
        nutrition_dir: str,
        only_date: datetime | None,
        write_notes_to: str | None,
        override_existing: bool,
    ) -> bool:
        nm = NotesManipulator(notes_file=notes_file, nutrition_dir=nutrition_dir)
        notes_need_enrichment = False

        for daily_entry in nm.source_entries:
            if only_date and daily_entry.date != only_date.date():
                print(f"Skipping {daily_entry.date.isoformat()}")
                continue

            if (
                nm.do_all_meals_have_breakdowns(daily_entry.date)
                and not override_existing
            ):
                print(
                    f"{daily_entry.date.isoformat()} already has all meal breakdowns, skipping."
                )
                continue

            meals_and_breakdowns = nm.get_meal_breakdowns(daily_entry.date)
            meals_to_get_breakdowns = [
                ms
                for ms, n_b in meals_and_breakdowns
                if n_b is None or override_existing
            ]
            print("processing", daily_entry.date, meals_to_get_breakdowns)

            meal_breakdowns_llm = self._analyzer.get_meal_breakdowns(
                [ms.get_meal_description() for ms in meals_to_get_breakdowns],
                knowledge_base,
            )

            notes_need_enrichment = True

            try:
                assert len(meal_breakdowns_llm) == len(meals_to_get_breakdowns)
            except AssertionError:
                print(
                    "%s Wanted breakdowns for %d meals, but got %d breakdowns from LLM"
                    % (
                        daily_entry.date.isoformat(),
                        len(meals_to_get_breakdowns),
                        len(meal_breakdowns_llm),
                    )
                )
                continue

            nm.clear_breakdowns(daily_entry.date)
            for ms, n_b_section in meals_and_breakdowns:
                if ms in meals_to_get_breakdowns:
                    n_b = meal_breakdowns_llm[meals_to_get_breakdowns.index(ms)]
                else:
                    assert n_b_section is not None
                    n_b = n_b_section.breakdown
                nm.add_meal_breakdown(daily_entry.date, ms, n_b)

        if not notes_need_enrichment:
            print("No new meals and breakdowns, skipping the file.")
            return False

        if not write_notes_to:
            nm.write_notes(notes_file)
        else:
            nm.write_notes(write_notes_to)

        return True
