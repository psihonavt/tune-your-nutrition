import re
from collections.abc import Sequence
from datetime import date, datetime
from hashlib import md5
from operator import itemgetter
from typing import Any, ClassVar

from nutrition101.domain import NEntry, NBreakdown
from pydantic import BaseModel


class DailyEntrySection(BaseModel, Sequence):
    content: str

    def __getitem__(self, key: Any) -> Any:
        return self._lines[key]

    def __len__(self) -> int:
        return len(self._lines)

    @property
    def _lines(self) -> list[str]:
        return self.content.splitlines()

    @property
    def is_meal(self) -> bool:
        return self.content.strip(" ").startswith("==")

    @property
    def is_meal_n_breakdown(self) -> bool:
        return self.content.strip(" ").startswith(
            f"| {DailyEntryNBreakdownSubSection.MEAL_BREAKDOWN_FIRST_COLUMN}"
        )

    @property
    def is_meal_anchor(self) -> bool:
        return self[0].startswith("######")

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
        return self[0].strip(" =")

    def get_meal_anchor(self) -> str:
        assert self.is_meal_anchor, f"Not a meal anchor - {self[0]}"
        assert len(self) == 2, f"Not a meal anchor - {self}"
        return self[1]


class NotesManipulator2:
    def __init__(self) -> None:
        self._


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

    def set_meal_breakdown(
        self, n_breakdown: NBreakdown, after_meal: DailyEntrySection
    ) -> "DailyEntry":
        sections = self.sections.copy()
        assert after_meal in self.sections, "Provided meal section couldn't be found"
        n_breakdown_table = DailyEntryNBreakdownSubSection(
            is_daily_total=False,
            meal_hash=after_meal.get_meal_hash(),
            breakdown=n_breakdown,
        ).to_md_table()
        n_breakdown_as_section = DailyEntrySection(content=n_breakdown_table)
        insert_idx = self.sections.index(after_meal) + 1
        from ipdb import set_trace

        set_trace()
        if insert_idx <= len(self.sections) - 1:
            if sections[insert_idx].is_meal_n_breakdown:
                sections[insert_idx] = n_breakdown_as_section
            else:
                sections.insert(insert_idx, n_breakdown_as_section)
        else:
            sections.append(n_breakdown_as_section)
        de = DailyEntry(date=self.date, sections=sections)
        de = de._set_daily_breakdown()
        return de

    def _set_daily_breakdown(self) -> "DailyEntry":
        sections = self.sections.copy()
        meal_breakdowns = [
            (
                sections[sections.index(mb) - 1].get_meal_name(),
                DailyEntryNBreakdownSubSection.from_md_table(mb.content).breakdown,
            )
            for mb in self.sections
            if mb.is_meal_n_breakdown
        ]
        if not meal_breakdowns:
            return self

        daily_breakdown_table = DailyEntryNBreakdownSubSection(
            is_daily_total=True,
            breakdown=NBreakdown(
                entries=[
                    mb.get_total_as_entry(meal_name)
                    for meal_name, mb in meal_breakdowns
                ]
            ),
            meal_hash="",
        ).to_md_table()
        daily_breakdown = DailyEntrySection(content=daily_breakdown_table)
        if sections[-1].is_daily_n_breakdown:
            sections[-1] = daily_breakdown
        else:
            sections.append(daily_breakdown)
        return DailyEntry(date=self.date, sections=sections)

    def to_md_content(self) -> str:
        md_sections = [self.date.strftime("%m/%d/%Y")]
        for section in self.sections:
            md_sections.append(section.content)
        return "\n\n".join(md_sections)

    def is_all_meals_have_breakdowns(self) -> bool:
        meals_and_breakdowns = self.get_meals_with_breakdowns()
        return all([mb is not None for _, mb in meals_and_breakdowns])

    def get_meals_with_breakdowns(
        self,
    ) -> list[tuple[DailyEntrySection, NBreakdown | None]]:
        result = []
        for section in self.sections:
            if section.is_meal:
                meal_breakdown = None
                maybe_breakdown_idx = self.sections.index(section) + 1
                if maybe_breakdown_idx <= len(self.sections) - 1:
                    if self.sections[maybe_breakdown_idx].is_meal_n_breakdown:
                        maybe_meal_breakdown = (
                            DailyEntryNBreakdownSubSection.from_md_table(
                                self.sections[maybe_breakdown_idx].content,
                            )
                        )
                        if maybe_meal_breakdown.meal_hash == section.get_meal_hash():
                            meal_breakdown = maybe_meal_breakdown.breakdown
                result.append((section, meal_breakdown))
        return result


class NotesManipulator:
    def __init__(self, md_content: str | None = None) -> None:
        if md_content:
            self._entries_map = {
                de.date: de for de in self._parse_daily_entries(md_content)
            }

    def read_notes(self, path: str) -> None:
        with open(path) as f:
            self._entries_map = {
                de.date: de for de in self._parse_daily_entries(f.read())
            }

    @property
    def entries(self) -> list[DailyEntry]:
        return [de for _, de in sorted(self._entries_map.items(), key=itemgetter(0))]

    def write_notes(self, path: str) -> None:
        md_content = "\n\n".join([de.to_md_content() for de in self.entries])
        with open(path, "w") as f:
            f.write(md_content)

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

    def add_meal_breakdown(
        self, date: date, section: DailyEntrySection, breakdown: NBreakdown
    ) -> None:
        assert date in self._entries_map, (
            f"There is not daily entry for {date.isoformat()}"
        )
        daily_entry = self._entries_map[date]
        daily_entry = daily_entry.set_meal_breakdown(breakdown, section)
        self._entries_map[date] = daily_entry


if __name__ == "__main__":
    nm = NotesManipulator(md_content=None)
    nm.read_notes("/Users/cake-icing/Documents/amkoval/daily/2025/06 June.md")
    de_06012025 = nm.entries[0]

    nm_n = NotesManipulator(md_content=None)
    nm_n.read_notes("/Users/cake-icing/Documents/amkoval/daily/2025/06 June-n.md")
    from ipdb import set_trace

    set_trace()
    # breakfast_06012025 = de_06012025.sections[1]
    # breakfast_06012025_n_breakdown = NBreakdown(
    #     meal_hash=breakfast_06012025.get_meal_hash(),
    #     is_daily_total=False,
    #     entries=[
    #         NEntry(
    #             item="2 Eggs",
    #             calories=15,
    #             carbs_g=12,
    #             sugars_g=45,
    #             protein_g=15,
    #             fat_g=42,
    #             fiber_g=1,
    #             sodium_mg=14,
    #         ),
    #         NEntry(
    #             item="Bread",
    #             calories=150,
    #             carbs_g=24,
    #             sugars_g=1,
    #             protein_g=2,
    #             fat_g=15,
    #             fiber_g=100,
    #             sodium_mg=300,
    #         ),
    #     ],
    # )
    # nm.add_meal_breakdown(
    #     de_06012025.date, breakfast_06012025, breakfast_06012025_n_breakdown
    # )
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
