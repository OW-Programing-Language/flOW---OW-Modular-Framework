#!/usr/bin/env python3
"""Confirm order, shutdown, rollback and lifecycle state from OW process output."""
import sys
from pathlib import Path

shop, rollback, reactivation = (Path(name).read_text(encoding="utf-8")
                                for name in sys.argv[1:4])

def in_order(log: str, markers: tuple[str, ...]) -> None:
    positions = [log.index(marker) for marker in markers]
    assert positions == sorted(positions), f"out-of-order markers: {markers}"

in_order(shop, ("START inventory", "START orders", "START notifications"))
in_order(shop, ("STOP notifications", "STOP orders", "STOP inventory"))
for expected in ("EVENT notifications 7", "EVENT notifications 9",
                 "EVENT inventory 8", "PASS flOW v2: native functors"):
    assert expected in shop, f"missing event/result {expected}"
assert "EVENT notifications 8" not in shop, "disabled subscriber received event"
in_order(rollback, ("START good", "FAIL failing", "STOP good"))
assert "ERROR: failing never started" not in rollback
assert "PASS lifecycle rollback" in rollback
assert "PASS flOW 70 native restart cycles" in reactivation
print("PASS flOW startup order, shutdown, rollback and events")
