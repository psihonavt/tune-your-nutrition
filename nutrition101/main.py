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
@click.option("--only-date", type=click.DateTime(["%m/%d/%Y"]))
@click.option("--write-notes-to", type=click.Path(writable=True))
@click.option("--override-exitsting", is_flag=True)
def enrich_notes(
    notes: str,
    only_date: datetime | None,
    write_notes_to: str | None,
    override_exitsting: bool,
):
    nm = NotesManipulator()
    with open(
        "/Users/cake-icing/Documents/amkoval/daily/2025/00 Knowledge Base.md"
    ) as f:
        kbs = f.read()

    nm.read_notes(notes)
    for daily_entry in nm.entries:
        if only_date and daily_entry.date != only_date.date():
            click.echo(f"Skipping {daily_entry.date.isoformat()}")
            continue

        if daily_entry.is_all_meals_have_breakdowns() and not override_exitsting:
            click.echo(
                f"{daily_entry.date.isoformat()} alread has all meal breakdowns, skipping."
            )
            continue
        meals_and_breakdowns = daily_entry.get_meals_with_breakdowns()
        meal_descriptions = [
            (ms.get_meal_description(), ms)
            for ms, mb in meals_and_breakdowns
            if mb is None or override_exitsting
        ]
        meal_breakdowns_llm = LLM.get_meals_breakdowns(
            [md for md, _ in meal_descriptions], kbs
        )
        try:
            assert len(meal_breakdowns_llm) == len(meal_descriptions)
        except AssertionError:
            from ipdb import set_trace

            set_trace()
            raise
        for (_, ms), mb_llm in zip(meal_descriptions, meal_breakdowns_llm):
            nm.add_meal_breakdown(daily_entry.date, ms, mb_llm)

    if not write_notes_to:
        nm.write_notes(notes)
    else:
        nm.write_notes(write_notes_to)


cli.add_command(enrich_notes)


if __name__ == "__main__":
    cli()
