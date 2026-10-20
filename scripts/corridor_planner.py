"""Track assignment helpers for layout-time corridor routing."""
from __future__ import annotations


def assign_interval_tracks(
    intervals: dict[object, tuple[int, int]],
    base: int,
    step: int,
) -> dict[object, int]:
    """Assign the fewest ordered tracks to non-touching 1-D intervals."""
    track_ends: list[int] = []
    result: dict[object, int] = {}
    for key, (start, end) in sorted(
        intervals.items(),
        key=lambda item: (min(item[1]), max(item[1])),
    ):
        low, high = sorted((start, end))
        selected = None
        for index, previous_end in enumerate(track_ends):
            if previous_end + step <= low:
                selected = index
                break
        if selected is None:
            selected = len(track_ends)
            track_ends.append(high)
        else:
            track_ends[selected] = high
        result[key] = base + selected * step
    return result
