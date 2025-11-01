import logging
from pathlib import Path
import sys
from datetime import datetime
from time import time

import click

from nutrition101.application import CLAUDE_LLM, GROK_LLM
from nutrition101.obsidian import ObsidianNotesEnricher
from nutrition101.misc import get_today_date

log = logging.getLogger("n101." + __name__)


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
    today = get_today_date()
    notes_file = Path(f"{daily_notes_dir}/{today.year}/{today.strftime('%m %B.md')}")
    if not notes_file.exists():
        log.info(f"The notes files {notes_file} couldn't be found.")
        sys.exit(1)

    knowledge_base = Path(f"{daily_notes_dir}/{today.year}/n101/knowledge_base.md")
    try:
        was_enriched = ObsidianNotesEnricher(
            analyzer=CLAUDE_LLM if analyzer == "claude" else GROK_LLM
        ).enrich_notes(
            notes_file=str(notes_file),
            knowledge_base=knowledge_base.read_text()
            if knowledge_base.exists()
            else "",
            nutrition_dir=nutrition_dir,
            only_date=only_date,
            write_notes_to=write_notes_to,
            override_existing=override_existing,
        )
    except Exception:
        log.exception("Error enriching daily notes.")
        sys.exit(1)

    if was_enriched:
        log.info("Done enriching daily notes. Took %.2f seconds", time() - start)


cli.add_command(enrich_notes)


if __name__ == "__main__":
    cli()
