import logging
import sys
from datetime import datetime
from pathlib import Path
from time import time

import click

from nutrition101.application import CLAUDE_LLM, GROK_LLM
from nutrition101.helpers import get_today_date
from nutrition101.markdown import NotesManipulator
from nutrition101.models import ILLMAnalyzer

log = logging.getLogger("n101." + __name__)


def _enrich_notes(
    notes_file: str,
    knowledge_base: str,
    nutrition_dir: str,
    only_date: datetime | None,
    write_notes_to: str | None,
    override_existing: bool,
    analyzer: ILLMAnalyzer,
) -> bool:
    nm = NotesManipulator(notes_file=notes_file, nutrition_dir=nutrition_dir)
    if Path(knowledge_base).exists() and Path(knowledge_base).is_file():
        with open(knowledge_base) as f:
            kbs = f.read()
    else:
        click.echo(f"knowledge_base at {knowledge_base} doesn't exist")
        kbs = ""

    notes_need_enrichment = False

    for daily_entry in nm.source_entries:
        if only_date and daily_entry.date != only_date.date():
            click.echo(f"Skipping {daily_entry.date.isoformat()}")
            continue

        if nm.is_all_meals_have_breakdowns(daily_entry.date) and not override_existing:
            click.echo(
                f"{daily_entry.date.isoformat()} already has all meal breakdowns, skipping."
            )
            continue

        meals_and_breakdowns = nm.get_meal_breakdowns(daily_entry.date)
        meals_to_get_breakdowns = [
            ms for ms, n_b in meals_and_breakdowns if n_b is None or override_existing
        ]
        print("processing", daily_entry.date, meals_to_get_breakdowns)

        meal_breakdowns_llm = analyzer.get_meals_breakdowns(
            [ms.get_meal_description() for ms in meals_to_get_breakdowns], kbs
        )

        notes_need_enrichment = True

        try:
            assert len(meal_breakdowns_llm) == len(meals_to_get_breakdowns)
        except AssertionError:
            log.error(
                "%s Wanted breakdowns for %d meals, but got %d breakdowns from LLM",
                daily_entry.date.isoformat(),
                len(meals_to_get_breakdowns),
                len(meal_breakdowns_llm),
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
        click.echo("No new meals and breakdowns, skipping updating the file.")
        return False

    if not write_notes_to:
        nm.write_notes(notes_file)
    else:
        nm.write_notes(write_notes_to)

    return True


@click.group()
def cli(): ...


@click.command()
@click.argument("daily-notes-dir")
@click.argument("nutrition-dir")
@click.option("--analyzer", type=click.Choice(["claude", "grok"]), default="claude")
@click.option("--only-date", type=click.DateTime(["%m/%d/%Y"]))
@click.option("--write-notes-to", type=click.Path(writable=True))
@click.option("--override-existing", is_flag=True)
def enrich_notes(
    daily_notes_dir: str,
    nutrition_dir: str,
    only_date: datetime | None,
    write_notes_to: str | None,
    override_existing: bool,
    analyzer: str,
):
    start = time()
    today = get_today_date().date()
    notes_file = f"{daily_notes_dir}/{today.year}/{today.strftime('%m %B.md')}"
    knowledge_base = f"{daily_notes_dir}/{today.year}/n101/knowledge_base.md"
    try:
        was_enriched = _enrich_notes(
            notes_file=notes_file,
            knowledge_base=knowledge_base,
            nutrition_dir=nutrition_dir,
            only_date=only_date,
            write_notes_to=write_notes_to,
            override_existing=override_existing,
            analyzer=CLAUDE_LLM if analyzer == "claude" else GROK_LLM,
        )
    except Exception:
        log.exception("Error enriching daily notes.")
        sys.exit(1)

    if was_enriched:
        log.info("Done enriching daily notes. Took %.2f seconds", time() - start)


@click.command()
@click.argument("notes-file")
@click.argument("nutrition-dir")
@click.option("--kbs")
@click.option("--only-date", type=click.DateTime(["%m/%d/%Y"]))
@click.option("--write-notes-to", type=click.Path(writable=True))
@click.option("--override-existing", is_flag=True)
@click.option("--analyzer", type=click.Choice(["claude", "grok"]), default="claude")
def enrich_notes_dev(
    notes_file: str,
    nutrition_dir: str,
    only_date: datetime | None,
    write_notes_to: str | None,
    kbs: str | None,
    override_existing: bool,
    analyzer: str,
):
    _enrich_notes(
        notes_file=notes_file,
        knowledge_base=kbs or "",
        nutrition_dir=nutrition_dir,
        only_date=only_date,
        write_notes_to=write_notes_to,
        override_existing=override_existing,
        analyzer=CLAUDE_LLM if analyzer == "claude" else GROK_LLM,
    )


cli.add_command(enrich_notes)
cli.add_command(enrich_notes_dev)


if __name__ == "__main__":
    cli()
