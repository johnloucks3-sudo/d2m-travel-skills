"""
Cruise Intel Pipeline — Gold-Standard Progress Tracker
Rich ANSI terminal display with per-step stats, ETA, and final summary table.
"""
import sys
import time
from datetime import datetime
from typing import Optional

# ── ANSI 256-color palette ─────────────────────────────────────────────────────
def _c(n: int) -> str:
    """256-color foreground escape code."""
    return f'\033[38;5;{n}m'

RESET   = '\033[0m'
BOLD    = '\033[1m'
DIM     = '\033[2m'
GREEN   = _c(82)    # bright chartreuse-green
YELLOW  = _c(220)   # amber-yellow
CYAN    = _c(51)    # electric cyan
WHITE   = _c(255)   # near-white
BLUE    = _c(33)    # vivid cobalt-blue
MAGENTA = _c(135)   # medium orchid
RED     = _c(196)   # bright red
GRAY    = _c(242)   # medium-dark gray
ORANGE  = _c(214)   # amber-orange  (Wave 3 accent)
BG_DARK = '\033[40m'

# Wave accent colors
W1_COLOR = CYAN
W2_COLOR = BLUE
W3_COLOR = ORANGE

# ── Source metadata ────────────────────────────────────────────────────────────
SOURCES = [
    ('perx',         'Perx.com',            'sail-personalize.com REST API',  W1_COLOR),
    ('oat',          'OAT',                 'oattravel.com (gstack browser)', W1_COLOR),
    ('ponant',       'PONANT',              'us.ponant.com (gstack browser)', W1_COLOR),
    ('hx',           'HX Expeditions',      'travelhx.com (__NEXT_DATA__)',   W2_COLOR),
    ('seadream',     'SeaDream Yacht Club',  'seadream.com (gstack browser)', W2_COLOR),
    ('explora',      'Explora Journeys',     'explorajourneys.com (sitemap)',  W2_COLOR),
    ('cruisemapper', 'CruiseMapper',         'cruisemapper.com (requests+BS4)', W3_COLOR),
    ('cruisesonly',  'CruisesOnly',          'cruisesonly.com (gstack browser)', W3_COLOR),
    ('cruiseplum',   'CruisePlum',           'cruiseplum.com (gstack+login)', W3_COLOR),
]

WAVE_LABELS = {
    'perx': 'W1', 'oat': 'W1', 'ponant': 'W1',
    'hx': 'W2', 'seadream': 'W2', 'explora': 'W2',
    'cruisemapper': 'W3', 'cruisesonly': 'W3', 'cruiseplum': 'W3',
}

WIDTH = 70  # terminal width


def _ts() -> str:
    return datetime.now().strftime('%H:%M:%S')


def _bar(filled: int, total: int, width: int = 20) -> str:
    if total == 0:
        return '─' * width
    n = int(round(filled / total * width))
    return f'{GREEN}{"█" * n}{GRAY}{"░" * (width - n)}{RESET}'


def header(year: int, months: list) -> None:
    month_names = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',
                   7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
    months_str = ' + '.join(month_names.get(m, str(m)) for m in months)

    print()
    print(f'{BOLD}{"═" * WIDTH}{RESET}')
    print(f'{BOLD}  🛳  CRUISE INTEL PIPELINE   {year} · {months_str}{RESET}')
    print(f'{DIM}  10 sources · Euro/Med/Arctic · Oct/Nov {year}{RESET}')
    print(f'{BOLD}{"═" * WIDTH}{RESET}')
    print()


class StepTracker:
    """Context manager for a single pipeline step with live timing."""

    def __init__(
        self,
        step_num: int,
        total_steps: int,
        label: str,
        source_key: str,
        color: str = CYAN,
        skipped: bool = False,
    ):
        self.step_num = step_num
        self.total_steps = total_steps
        self.label = label
        self.source_key = source_key
        self.color = color
        self.skipped = skipped
        self.start_time: float = 0.0
        self.records: int = 0
        self.status: str = 'pending'
        self.note: str = ''

    def __enter__(self):
        self.start_time = time.time()
        wave = WAVE_LABELS.get(self.source_key, '')
        if wave == 'W3':
            wave_badge = f'{W3_COLOR}[{wave}]{RESET}'
        elif wave == 'W2':
            wave_badge = f'{W2_COLOR}[{wave}]{RESET}'
        elif wave == 'W1':
            wave_badge = f'{W1_COLOR}[{wave}]{RESET}'
        else:
            wave_badge = f'{GRAY}[{wave}]{RESET}'
        skip_tag = f' {YELLOW}(CACHED){RESET}' if self.skipped else ''

        print(f'{BOLD}{"─" * WIDTH}{RESET}')
        print(
            f'{BOLD}{self.color}  STEP {self.step_num}/{self.total_steps}{RESET}  '
            f'{wave_badge}  {BOLD}{self.label}{RESET}{skip_tag}'
        )
        sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type:
            self.status = 'error'
            icon = f'{RED}✗{RESET}'
        elif self.skipped:
            icon = f'{YELLOW}⤷{RESET}'
        elif self.records == 0:
            icon = f'{YELLOW}⚠{RESET}'
            self.status = 'empty'
        else:
            icon = f'{GREEN}✓{RESET}'
            self.status = 'ok'

        rec_str = (
            f'{GREEN}{self.records}{RESET} records'
            if self.records
            else f'{YELLOW}0 records{RESET}'
        )
        elapsed_str = f'{elapsed:.1f}s'
        note_str = f'  {DIM}{self.note}{RESET}' if self.note else ''

        print(
            f'  {icon}  {rec_str}  {DIM}({elapsed_str}){RESET}{note_str}'
        )
        sys.stdout.flush()
        return False  # don't suppress exceptions


class SummaryTable:
    """Final cross-source summary table."""

    def __init__(self):
        self._rows: list[dict] = []
        self._total_start: float = time.time()

    def add(
        self,
        source_key: str,
        label: str,
        records: int,
        cross_matched: int,
        net_new: int,
        skipped: bool = False,
        wave: str = 'W1',
    ):
        self._rows.append({
            'key': source_key,
            'label': label,
            'records': records,
            'cross_matched': cross_matched,
            'net_new': net_new,
            'skipped': skipped,
            'wave': wave,
        })

    def print(
        self,
        total_unique: int,
        total_lines: int,
        multi_source: int,
        wave2_net_new: int,
        wave3_net_new: int = 0,
    ) -> None:
        elapsed = time.time() - self._total_start
        mins, secs = divmod(int(elapsed), 60)

        print()
        print(f'{BOLD}{"═" * WIDTH}{RESET}')
        print(f'{BOLD}  PIPELINE COMPLETE   {mins}m {secs:02d}s{RESET}')
        print(f'{BOLD}{"═" * WIDTH}{RESET}')

        # Source table
        col_w = [16, 7, 9, 7, 5, 8]
        hdr = (
            f'{"Source":<{col_w[0]}} {"Wave":>{col_w[1]}} '
            f'{"Records":>{col_w[2]}} {"X-Match":>{col_w[3]}} '
            f'{"Net-New":>{col_w[4]}} {"Status":>{col_w[5]}}'
        )
        print()
        print(f'  {BOLD}{hdr}{RESET}')
        print(f'  {"─" * (sum(col_w) + 5)}')

        for r in self._rows:
            if r['wave'] == 'W3':
                wave_col = W3_COLOR
            elif r['wave'] == 'W2':
                wave_col = W2_COLOR
            else:
                wave_col = W1_COLOR
            status = f'{YELLOW}CACHED{RESET}' if r['skipped'] else (
                f'{GREEN}OK{RESET}' if r['records'] else f'{YELLOW}EMPTY{RESET}'
            )
            net_str = f'+{r["net_new"]}' if r['net_new'] else '—'
            xm_str  = str(r['cross_matched']) if r['cross_matched'] else '—'

            print(
                f'  {r["label"]:<{col_w[0]}} '
                f'{wave_col}{r["wave"]:>{col_w[1]}}{RESET} '
                f'{r["records"]:>{col_w[2]}} '
                f'{xm_str:>{col_w[3]}} '
                f'{net_str:>{col_w[4]}} '
                f'{status}'
            )

        print(f'  {"─" * (sum(col_w) + 5)}')
        print()

        # Key metrics
        metrics = [
            ('Unique sailings',          f'{BOLD}{total_unique}{RESET}'),
            ('Cruise lines',             str(total_lines)),
            ('Multi-source confidence',  f'{GREEN}{multi_source}{RESET}'),
            ('Wave 2 net-new sailings',  f'{W2_COLOR}+{wave2_net_new}{RESET}'),
            ('Wave 3 net-new sailings',  f'{W3_COLOR}+{wave3_net_new}{RESET}'),
        ]
        for label, val in metrics:
            print(f'  {label:<28}  {val}')

        print()
        print(f'{BOLD}{"═" * WIDTH}{RESET}')
        print()
        sys.stdout.flush()
