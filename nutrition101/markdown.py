import re
from collections.abc import Sequence
from datetime import date, datetime
from hashlib import md5
from pathlib import Path
from operator import itemgetter
from typing import Any, ClassVar

from nutrition101.domain import NEntry, NBreakdown
from pydantic import BaseModel


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
        return self.content.strip(" ").startswith(
            f"| {DailyEntryNBreakdownSubSection.MEAL_BREAKDOWN_FIRST_COLUMN}"
        )

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
                f"| {entry.item} | {entry.calories} | {entry.carbs_g} | {entry.sugars_g} | {entry.protein_g} | {entry.fat_g} | {entry.fiber_g} | {entry.sodium_mg} |"
            )

        if self.is_daily_total:
            total_calories = sum([e.calories for e in self.breakdown.entries])
            total_carbs = sum([e.carbs_g for e in self.breakdown.entries])
            total_sugars = sum([e.sugars_g for e in self.breakdown.entries])
            total_protein = sum([e.protein_g for e in self.breakdown.entries])
            total_fat = sum([e.fat_g for e in self.breakdown.entries])
            total_fiber = sum([e.fiber_g for e in self.breakdown.entries])
            total_sodium = sum([e.sodium_mg for e in self.breakdown.entries])
            lines.append(
                f"| **TOTAL** | **{total_calories}** | **{total_carbs}** | **{total_sugars}** | **{total_protein}** | **{total_fat}** | **{total_fiber}** | **{total_sodium}** |"
            )

        return "\n".join(lines)

    @classmethod
    def from_md_table(cls, table: str) -> "DailyEntryNBreakdownSubSection":
        lines = table.splitlines()
        assert len(lines) >= 3, "Meal breakdown can't be empty"
        assert lines[0].startswith(f"| {cls.MEAL_BREAKDOWN_FIRST_COLUMN}"), (
            f"Not a meal breakdown! {lines[0]}"
        )
        hash_match = re.search(r"\((.*)\)", lines[0].split("|")[1])
        meal_hash = hash_match.group(1) if hash_match else ""
        entries = []
        for line in lines[2:]:
            item, calories, carbs_g, sugars_g, protein_g, fat_g, fiber_g, sodium_mg = (
                line.split("|")[1:-1]
            )
            entries.append(
                NEntry(
                    item=item,
                    calories=int(calories),
                    carbs_g=int(carbs_g),
                    sugars_g=int(sugars_g),
                    protein_g=int(protein_g),
                    fat_g=int(fat_g),
                    fiber_g=int(fiber_g),
                    sodium_mg=int(sodium_mg),
                )
            )
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
        return match and datetime.strptime(match.group(), "%m/%d/%Y")

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
        if not section.has_breakdown_link:
            meal_name = section.get_meal_name()
            meal_name_anchored = self._generate_breakdown_link(
                daily_entry.date, meal_name
            )
            updated_meal_section = DailyEntrySection(
                content="\n".join([meal_name_anchored] + meal_content[1:])
            )
            sections[meal_idx] = updated_meal_section

        daily_link_section = next(
            (
                section
                for section in sections
                if section.has_breakdown_link and self._DAILY_BREAKDOWN in section[0]
            ),
            None,
        )
        if not daily_link_section:
            daily_link_section = DailyEntrySection(
                content=self._generate_breakdown_link(
                    daily_entry.date, self._DAILY_BREAKDOWN
                )
            )
            sections.append(daily_link_section)
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
                DailyEntryNBreakdownSubSection.from_md_table(mb.content).breakdown,
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
                            if breakdown_section.meal_hash == section.get_meal_hash():
                                n_breakdown = breakdown_section
                result.append((section, n_breakdown))
        return result

    def is_all_meals_have_breakdowns(self, date: date) -> bool:
        return all(
            n_breakdown is not None for _, n_breakdown in self.get_meal_breakdowns(date)
        )


if __name__ == "__main__":
    nm = NotesManipulator(
        notes_file="/Users/cake-icing/Documents/amkoval/daily/2025/06 June-mod.md",
        nutrition_dir="n101_test",
    )
    de_06012025 = nm.source_entries[0]

    breakfast_06012025 = de_06012025.sections[1]
    breakfast_06012025_n_breakdown = NBreakdown(
        entries=[
            NEntry(
                item="2 Eggs",
                calories=15,
                carbs_g=12,
                sugars_g=45,
                protein_g=15,
                fat_g=42,
                fiber_g=1,
                sodium_mg=14,
            ),
            NEntry(
                item="Bread",
                calories=150,
                carbs_g=24,
                sugars_g=1,
                protein_g=2,
                fat_g=15,
                fiber_g=100,
                sodium_mg=300,
            ),
        ],
    )
    nm.add_meal_breakdown(
        de_06012025.date, breakfast_06012025, breakfast_06012025_n_breakdown
    )
    print(nm.is_all_meals_have_breakdowns(de_06012025.date))
    print(nm.get_meals_and_breakdowns(de_06012025.date))
    # nm.write_notes(None)
    #
    # dinner_06012025 = de_06012025.sections[3]
    # dinner_06012025_n_breakdown = NBreakdown(
    #     meal_hash=dinner_06012025.get_meal_hash(),
    #     is_daily_total=False,
    #     entries=[
    #         NEntry(
    #             item="STEAK",
    #             calories=1500,
    #             carbs_g=12,
    #             sugars_g=45,
    #             protein_g=350,
    #             fat_g=42,
    #             fiber_g=1,
    #             sodium_mg=14,
    #         ),
    #         NEntry(
    #             item="Broccoli (Steamed)",
    #             calories=150,
    #             carbs_g=24,
    #             sugars_g=1,
    #             protein_g=2,
    #             fat_g=15,
    #             fiber_g=999,
    #             sodium_mg=300,
    #         ),
    #     ],
    # )
    # nm.add_meal_breakdown(
    #     de_06012025.date, dinner_06012025, dinner_06012025_n_breakdown
    # )
    # breakfast_06012025_n_breakdown_overridden = NBreakdown(
    #     meal_hash=breakfast_06012025.get_meal_hash(),
    #     is_daily_total=False,
    #     entries=[
    #         NEntry(
    #             item="Water",
    #             calories=0,
    #             carbs_g=0,
    #             sugars_g=0,
    #             protein_g=0,
    #             fat_g=0,
    #             fiber_g=0,
    #             sodium_mg=0,
    #         ),
    #     ],
    # )
    # nm.add_meal_breakdown(
    #     de_06012025.date, breakfast_06012025, breakfast_06012025_n_breakdown_overridden
    # )
    #
    # nm.write_notes("/Users/cake-icing/Documents/amkoval/daily/2025/06 June-mod.md")
    #
    # nm = NotesManipulator()
    # nm.read_notes("/Users/cake-icing/Documents/amkoval/daily/2025/06 June-mod.md")
    # de_06062025 = next(de for de in nm.entries if de.date == date(2025, 6, 6))
    # snack_06062025 = de_06062025.sections[4]
    # snack_06062025_breakdown = NBreakdown(
    #     meal_hash=snack_06062025.get_meal_hash(),
    #     is_daily_total=False,
    #     entries=[
    #         NEntry(
    #             item="Peach",
    #             calories=2,
    #             carbs_g=2,
    #             sugars_g=2,
    #             protein_g=2,
    #             fat_g=2,
    #             fiber_g=2,
    #             sodium_mg=2,
    #         ),
    #         NEntry(
    #             item="Apricot",
    #             calories=3,
    #             carbs_g=3,
    #             sugars_g=3,
    #             protein_g=3,
    #             fat_g=3,
    #             fiber_g=3,
    #             sodium_mg=3,
    #         ),
    #     ],
    # )
    # nm.add_meal_breakdown(de_06062025.date, snack_06062025, snack_06062025_breakdown)
    # nm.write_notes("/Users/cake-icing/Documents/amkoval/daily/2025/06 June-mod.md")
