"""Manufacturer lookup from the public IEEE registry of MAC address prefixes.

The registry is bundled as oui.tsv (rebuild with tools/build_oui.py), so no
network access is needed. Call only from the DB thread: the first lookup reads
the file.
"""
from __future__ import annotations

import re
from pathlib import Path

PRIVATE = "Private address"

_OUI: dict[str, str] | None = None
# Company-form suffixes that add length but no information.
_SUFFIX = re.compile(
    r"[,.\s]+(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|gmbh|ag|bv|sa|s\.a|"
    r"pte|plc|technologies|technology|electronics|international|intl)\.?$",
    re.IGNORECASE,
)


def _load() -> dict[str, str]:
    global _OUI
    if _OUI is None:
        table: dict[str, str] = {}
        try:
            with open(Path(__file__).parent / "oui.tsv", encoding="utf-8") as fh:
                for line in fh:
                    prefix, _, name = line.rstrip("\n").partition("\t")
                    table[prefix] = name
        except OSError:
            pass
        _OUI = table
    return _OUI


def _tidy(name: str) -> str:
    for _ in range(4):
        short = _SUFFIX.sub("", name).strip(" ,.")
        if short == name or not short:
            break
        name = short
    return name.title() if name.isupper() and len(name) > 4 else name


def is_private(mac: str) -> bool:
    """True for randomised (locally administered) addresses, which have no manufacturer."""
    digits = re.sub(r"[^0-9A-Fa-f]", "", mac)
    return len(digits) >= 2 and digits[1].upper() in "26AE"


def vendor(mac: str, omada_vendor: str | None = None) -> str | None:
    """Manufacturer for a MAC, combining Omada's guess with the registry.

    Omada guesses the device maker from how the device behaves; the registry
    names who made the network chip. When both are known and disagree, both
    are returned as "Omada / registry" since either may be the useful one.
    """
    guess = omada_vendor if omada_vendor and omada_vendor.lower() != "unknown" else None
    if is_private(mac):
        return guess or PRIVATE
    digits = re.sub(r"[^0-9A-Fa-f]", "", mac).upper()
    name = _load().get(digits[:6])
    registered = _tidy(name) if name else None
    if not registered or not guess:
        return registered or guess
    if guess.lower() in registered.lower() or registered.lower() in guess.lower():
        return guess
    return f"{guess} / {registered}"
