from collections import Counter, deque

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text


class Dashboard:
    def __init__(self, total, enabled=True):
        self.console = Console()
        self.enabled = enabled and self.console.is_terminal
        self.progress = Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(),
                                 TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn())
        self.task = self.progress.add_task("Models", total=total)
        self.counts = Counter()
        self.messages = deque(maxlen=7)
        self.stage = "Starting"
        self.sample = {}
        self.live = Live(self.render(), console=self.console, refresh_per_second=4) if self.enabled else None

    def __enter__(self):
        if self.live:
            self.live.start()
        return self

    def __exit__(self, *args):
        if self.live:
            self.live.update(self.render())
            self.live.stop()

    def render(self):
        table = Table.grid(expand=True)
        table.add_row("Stage", Text(self.stage))
        table.add_row("Models", Text("  ".join(f"{name}: {self.counts[name]}" for name in ("completed", "skipped", "failed", "planned"))))
        if self.sample:
            gib = 1024 ** 3
            table.add_row("Memory", f"Available {self.sample['available']/gib:.1f} GiB · owned footprint {self.sample['footprint']/gib:.1f} GiB · pressure {self.sample['pressure']}")
        messages = Group(*(Text(message) for message in self.messages))
        return Group(Panel(table, title="Local AI Benchmark"), self.progress, Panel(messages, title="Recent events"))

    def update(self, stage=None, sample=None):
        if stage is not None:
            self.stage = stage
        if sample is not None:
            self.sample = sample
        if self.live:
            self.live.update(self.render())

    def event(self, kind, message):
        if kind == "command":
            return
        if kind == "download":
            self.stage = message
        self.messages.append(f"{kind.upper()}: {message}")
        if not self.live:
            self.console.print(Text(f"{kind.upper()}: {message}"))
        self.update()

    def finish(self, status):
        self.counts[status] += 1
        self.progress.advance(self.task)
        self.update()
