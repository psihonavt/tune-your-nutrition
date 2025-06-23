import configparser
from datetime import datetime
from io import TextIOWrapper

import click

from nutrition101.models import ClaudeNAnalyzer
from nutrition101.markdown import NotesManipulator


CONFIG = configparser.ConfigParser()
CONFIG.read("config.ini")

LLM = ClaudeNAnalyzer(api_key=CONFIG["LLM"]["ANTHROPIC_API_KEY"])


@click.group()
def cli(): ...


@click.command()
@click.argument("notes", type=click.Path(exists=True))
@click.argument("nutrition-dir")
@click.option("--only-date", type=click.DateTime(["%m/%d/%Y"]))
@click.option("--write-notes-to", type=click.Path(writable=True))
@click.option("--override-exitsting", is_flag=True)
def enrich_notes(
    notes: str,
    nutrition_dir: str,
    only_date: datetime | None,
    write_notes_to: str | None,
    override_exitsting: bool,
):
    nm = NotesManipulator(notes_file=notes, nutrition_dir=nutrition_dir)
    with open(
        "/Users/cake-icing/Documents/amkoval/daily/2025/n101/knowledge_base.md"
    ) as f:
        kbs = f.read()

    for daily_entry in nm.source_entries:
        if only_date and daily_entry.date != only_date.date():
            click.echo(f"Skipping {daily_entry.date.isoformat()}")
            continue

        if nm.is_all_meals_have_breakdowns(daily_entry.date) and not override_exitsting:
            click.echo(
                f"{daily_entry.date.isoformat()} already has all meal breakdowns, skipping."
            )
            continue

        meals_and_breakdowns = nm.get_meal_breakdowns(daily_entry.date)
        meals_to_get_breakdowns = [
            ms for ms, n_b in meals_and_breakdowns if n_b is None or override_exitsting
        ]
        print("processing", daily_entry.date, meals_to_get_breakdowns)

        meal_breakdowns_llm = LLM.get_meals_breakdowns(
            [ms.get_meal_description() for ms in meals_to_get_breakdowns], kbs
        )

        try:
            assert len(meal_breakdowns_llm) == len(meals_to_get_breakdowns)
        except AssertionError:
            from ipdb import set_trace

            set_trace()
            raise

        nm.clear_breakdowns(daily_entry.date)
        for ms, n_b_section in meals_and_breakdowns:
            if ms in meals_to_get_breakdowns:
                n_b = meal_breakdowns_llm[meals_to_get_breakdowns.index(ms)]
            else:
                assert n_b_section is not None
                n_b = n_b_section.breakdown
            nm.add_meal_breakdown(daily_entry.date, ms, n_b)

    if not write_notes_to:
        nm.write_notes(notes)
    else:
        nm.write_notes(write_notes_to)


cli.add_command(enrich_notes)


if __name__ == "__main__":
    cli()
