from __future__ import annotations

from dataclasses import dataclass

GRID_COLUMNS = 7
SAFE_TAIL_ROWS = 3


@dataclass(frozen=True)
class ScanStep:
    index: int
    row: int
    col: int
    movement: str
    tail_safe: bool = False


def build_console_scan_plan(total_count: int, columns: int = GRID_COLUMNS, safe_tail_rows: int = SAFE_TAIL_ROWS) -> list[ScanStep]:
    """Build a deterministic scan order for the console inventory grid.

    The normal inventory traversal is snake/S-shaped. When the last row is
    incomplete and would otherwise be scanned from right to left, the final
    2-3 rows are scanned in a safe left-to-right block to avoid landing on
    empty cells past the final item.
    """
    if total_count <= 0:
        return []
    columns = max(1, int(columns))
    full_rows, remainder = divmod(total_count, columns)
    row_count = full_rows + (1 if remainder else 0)
    partial_last_row = remainder != 0
    last_row_index = row_count - 1
    last_row_would_rtl = partial_last_row and (last_row_index % 2 == 1)
    tail_start = row_count
    if last_row_would_rtl:
        tail_start = max(0, row_count - max(2, safe_tail_rows))

    steps: list[ScanStep] = []
    for row in range(row_count):
        cols_in_row = remainder if (partial_last_row and row == last_row_index) else columns
        if row >= tail_start:
            col_order = list(range(cols_in_row))
            tail_safe = True
        else:
            col_order = list(range(columns)) if row % 2 == 0 else list(reversed(range(columns)))
            tail_safe = False
        for col in col_order:
            if len(steps) >= total_count:
                break
            if steps:
                prev = steps[-1]
                if row > prev.row:
                    movement = '다음 줄'
                elif col > prev.col:
                    movement = '우'
                elif col < prev.col:
                    movement = '좌'
                else:
                    movement = '시작'
            else:
                movement = '시작'
            steps.append(ScanStep(len(steps) + 1, row, col, movement, tail_safe))
    return steps


def describe_scan_plan(total_count: int) -> str:
    steps = build_console_scan_plan(total_count)
    if not steps:
        return '스캔할 콘솔이 없습니다.'
    rows = max(step.row for step in steps) + 1
    tail_count = sum(1 for step in steps if step.tail_safe)
    return (
        f'총 {total_count}개 / 7열 / {rows}줄 스캔 계획\n'
        f'마지막 줄 보정 대상: {tail_count}칸\n'
        '마지막 줄이 우→좌 부분 줄로 끝날 경우, 마지막 2~3줄은 S자가 아닌 좌→우 안전 스캔으로 전환합니다.'
    )
