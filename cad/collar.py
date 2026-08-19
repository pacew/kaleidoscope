#!/usr/bin/env python3
"""Clamping collars for the tapered kaleidoscope.

Run:  python3 cad/collar.py

A collar slides on over the narrow end and is pushed toward the wide end.
Because the tube grows that way, a bore cut to the tube's own taper closes on
it uniformly and wedges with full-face contact — a straight bore would only
touch on its leading rim and could rock. The bore's corners are relieved so it
bears on the flats and squeezes the mitres shut, rather than riding on the
plates' outer points and prising them apart.

Two: one near the wide end at 225, one at mid-span at 112. The mid-span one was
struck off after the first 255 mm build and then earned its way back on — with
the tube squeezed by hand at mid-length the mitre faces shear against each other
slightly, and a collar there stops it. It is a hoop, so it resists the cross
section deforming directly, which is the motion that lets the faces move.

A third, near the narrow end, cannot be fitted at all: its bore would be smaller
than the small cap it has to pass over. That is a check now rather than a
discovery.

More stations are one entry in STATIONS away, but they must go on FURTHEST
FIRST: a collar for the wide end has the largest bore and slides freely past
the nearer stations, never the other way round.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import Plane, RegularPolygon, fillet, loft

from scope import Scope, rounded_tri_reach
from small_cap import SmallCap
from verify import emit, require, sits_on_bed, unsupported_area

STATIONS = (225.0, 112.0)


@dataclass(frozen=True)
class Collar:
    seat: float                 # station where it nominally wedges
    length: float = 16.0
    wall: float = 2.5
    corner: float = 0.4         # keep well under 1.5 * miter_land
    grip: float = 0.0           # radial clearance; 0 is a pure wedge


def _rtri(inradius: float, corner: float, z: float):
    sk = RegularPolygon(radius=2 * inradius, side_count=3,
                        major_radius=True, rotation=90)
    return Plane.XY.offset(z) * fillet(sk.vertices(), corner)


def build(scope: Scope, collar: Collar):
    def bore(h: float) -> float:
        return scope.r_outer(collar.seat + h) + collar.grip

    part = loft([_rtri(bore(0.0) + collar.wall, collar.corner + collar.wall, 0.0),
                 _rtri(bore(collar.length) + collar.wall,
                       collar.corner + collar.wall, collar.length)])
    part -= loft([_rtri(bore(0.0), collar.corner, 0.0),
                  _rtri(bore(collar.length), collar.corner, collar.length)])
    return part


def check(scope: Scope, collar: Collar, part, mesh) -> dict:
    facts = {}
    bb = sits_on_bed(part)
    facts["across"] = bb.max.X - bb.min.X

    require(collar.seat + collar.length < scope.length,
            "collar runs off the wide end")

    for h, tag in ((0.0, "mouth"), (collar.length, "far")):
        z = collar.seat + h
        gap = (rounded_tri_reach(scope.r_outer(z) + collar.grip, collar.corner)
               - scope.corner_reach(z))
        require(gap > 0.3, f"bore corner clearance {gap:+.2f} mm at the {tag} — "
                           "it would ride on the plates' points and prise the "
                           "mitres open instead of closing them")
        facts[f"corner_{tag}"] = gap

    # It has to slide over the small cap on its way to its station, and the cap
    # is the fattest thing on the tube. The 55 mm collar failed exactly here.
    cap = SmallCap()
    cap_reach = rounded_tri_reach(
        scope.r_outer(cap.skirt) + cap.clearance + cap.wall, cap.bore_corner + cap.wall)
    bore_reach = rounded_tri_reach(scope.r_outer(collar.seat) + collar.grip, collar.corner)
    require(bore_reach > cap_reach + 0.5,
            f"bore reaches {bore_reach:.2f} mm but the small cap reaches "
            f"{cap_reach:.2f} — this collar cannot pass over the cap, so it could "
            "only be fitted before it, which makes assembly awkward")
    facts["over_cap"] = bore_reach - cap_reach

    # A wedge trades positional accuracy for tolerance of size error, and the
    # gentler the taper the worse the trade. Harmless now that nothing has to
    # line up with the collar, but it means the printed position is a guess.
    facts["drift"] = 1.0 / scope.taper

    area, _ = unsupported_area(mesh)
    require(area < 1.0, f"{area:.1f} mm2 over air — a plain ring should have none")
    facts["unsupported"] = area
    return facts


if __name__ == "__main__":
    scope = Scope()
    print(f"scope      {scope.summary()}")
    for seat in STATIONS:
        collar = Collar(seat=seat)
        part = build(scope, collar)
        name = f"collar_{seat:.0f}"
        stl, step, mesh, tess = emit(part, name)
        f = check(scope, collar, part, mesh)
        print(f"{name}  seat {seat:.0f}-{seat + collar.length:.0f} mm, "
              f"bore {scope.r_outer(seat):.2f} -> "
              f"{scope.r_outer(seat + collar.length):.2f} mm inradius, "
              f"{f['across']:.1f} mm across, {part.volume / 1000:.2f} cm3")
        print(f"{'':11}corners clear by {f['corner_mouth']:.2f} mm, clears the cap by "
              f"{f['over_cap']:.1f} mm, {len(mesh.faces)} faces, watertight")
        print(f"{'':11}far edge nominally {scope.length - seat - collar.length:.2f} mm "
              f"from the wide opening")
    print(f"\nseat drifts {f['drift']:.0f} mm per mm of radial size error, so treat "
          "the stations as nominal")
    print("fit them furthest first — the wide-end collar will not pass a nearer one")
