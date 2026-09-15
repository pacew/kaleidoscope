#!/usr/bin/env python3
"""Wide-end cap for the short scope. A flanged ring with rubber-band notches.

Run:  python3 cad/large_cap.py

It closes the wide end with a lip that overhangs the mirrors' end faces, so they
cannot slide out — the taper means the wide end is the only direction they can
go. It is held on by rubber bands running the length of the tube to matching
notches on the small cap.

WHY THERE ARE NO SNAP ARMS ANY MORE

There were three sprung ears hooking onto the collar's narrow face. They engaged,
but they never held hard: even preloaded 0.3 mm through a 30 degree wedge they
clamped only about 0.5 kgf, and a PLA cantilever that thin cannot do much better
without creeping. Bands solve the same problem with a part that stores no energy
in the plastic, does not fatigue, and swallows any amount of tolerance. Dropping
the arms also took 23 mm off this cap's height.

THE BORE IS STRAIGHT, AND IT HAS TO BE

The first version cut the skirt's bore to the tube's taper, the way the small cap
and the collar are cut, and it would not go on — 0.55 mm of interference on the
flats, 0.89 at the corners. Those two enter from the NARROW end, so their mouth
is sized for the widest station they cover and everything they slide over is
smaller. This one enters from the WIDE end, which inverts the argument: its mouth
is sized for the narrowest station it covers, and the first thing that mouth
meets is the tube at its very widest. No skirt length rescues it.

So the bore is a constant r_outer(length) + clearance. The cost is that it can
only be tight at the tube's end face and opens up by taper * skirt by the time it
reaches the mouth. `skirt` is the one lever on that gap.

PRINTS APERTURE-DOWN. Each notch's shelf bridges over its own notch, and that is
the only thing on the part printing over air.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import Rot, extrude, loft

from scope import Scope, rounded_tri_reach
from shapes import band_tab, rtri, straight_run, tab_offsets
from proto_set import PROTO
from verify import emit, require, sits_on_bed, unsupported_area


@dataclass(frozen=True)
class LargeCap:
    rim: float = 3.0           # flange thickness standing past the tube end
    skirt: float = 8.0         # sets the gap at the mouth: taper * skirt
    wall: float = 2.5
    clearance: float = 0.15
    bore_corner: float = 0.7
    ap_corner: float = 0.3
    lip: float = 0.6           # over the mirrors' end faces. Generous compared
    #                            with the small cap's, because this end is the
    #                            frame of the picture rather than a triangle
    #                            drawn in the middle of it
    tab_from_vertex: float = 10.0
    tab_w: float = 6.0
    tab_out: float = 3.5       # nothing has to slide over this end, so these
    #                            can be deeper than the small cap's notches
    tab_col: float = 2.0
    tab_z: float = 2.0
    tab_t: float = 1.5
    tab_bury: float = 0.5

    def top(self) -> float:
        return self.rim + self.skirt

    def shell(self, scope: Scope, z: float) -> float:
        """Outside of the cap. Tapered like the tube, for looks."""
        return (scope.r_outer(scope.length + self.rim - z)
                + self.clearance + self.wall)

    def bore(self, scope: Scope) -> float:
        """Straight, not tapered — see the module docstring."""
        return scope.r_outer(scope.length) + self.clearance


def build(scope: Scope, cap: LargeCap):
    top = cap.top()
    part = loft([rtri(cap.shell(scope, 0.0), cap.bore_corner + cap.wall, 0.0),
                 rtri(cap.shell(scope, top), cap.bore_corner + cap.wall, top)])

    # Bore, from the tube's end face up. Overshoot the top for a clean cut.
    part -= extrude(rtri(cap.bore(scope), cap.bore_corner, cap.rim),
                    amount=cap.skirt + 1.0)

    # Aperture through the flange.
    part -= extrude(rtri(scope.r_face(scope.length) - cap.lip, cap.ap_corner, -1.0),
                    amount=cap.rim + 2.0)

    r = cap.shell(scope, 0.0)
    face = None
    for x in tab_offsets(r, cap.tab_from_vertex):
        tab = band_tab(r, x, cap.tab_w, cap.tab_out, cap.tab_col,
                       cap.tab_z, cap.tab_t, cap.tab_bury)
        face = tab if face is None else face + tab

    return part + face + Rot(0, 0, 120) * face + Rot(0, 0, 240) * face


def check(scope: Scope, cap: LargeCap, part, mesh) -> dict:
    f = {}
    bb = sits_on_bed(part)
    f["height"], f["across"] = bb.max.Z, bb.max.X - bb.min.X
    f["deep"] = bb.max.Y - bb.min.Y

    # Sliding on from the wide end, every part of the bore passes over the
    # tube's widest station, so the whole bore has to clear it — not just the
    # part that ends up there. This is the check the first version lacked.
    widest = scope.r_outer(scope.length)
    f["entry"] = cap.bore(scope) - widest
    require(f["entry"] > 0.05,
            f"bore is {f['entry']:+.3f} mm on the flats against the tube's widest "
            "station — the cap will not go on. A tapered bore cannot be entered "
            "from the wide end.")
    f["corner"] = (rounded_tri_reach(cap.bore(scope), cap.bore_corner)
                   - scope.corner_reach(scope.length))
    require(f["corner"] > 0.3, f"bore corner clearance {f['corner']:+.2f} mm")

    f["mouth_gap"] = cap.bore(scope) - scope.r_outer(scope.length - cap.skirt)
    f["min_wall"] = min(cap.shell(scope, z) - cap.bore(scope)
                        for z in (cap.rim, cap.top()))
    require(f["min_wall"] > 1.2, f"skirt wall down to {f['min_wall']:.2f} mm")

    require(0.0 < cap.lip < scope.mirror,
            f"lip {cap.lip:.2f} mm does not land on the {scope.mirror:.2f} mm mirror")
    f["lip_lands"] = scope.mirror - cap.lip
    f["corner_bite"] = 2 * cap.lip + cap.ap_corner
    f["ap_across"] = 2 * math.sqrt(3) * (scope.r_face(scope.length) - cap.lip)

    r = cap.shell(scope, 0.0)
    f["tab_edge"] = abs(tab_offsets(r, cap.tab_from_vertex)[1]) + cap.tab_w / 2
    f["tab_run"] = straight_run(r, cap.bore_corner + cap.wall)
    require(f["tab_edge"] < f["tab_run"] - 1.0,
            f"band notch reaches {f['tab_edge']:.1f} mm along a flat straight only "
            f"to {f['tab_run']:.1f} — it would sit on the corner fillet")
    f["tab_depth"] = cap.tab_out - cap.tab_col + cap.tab_bury
    require(f["tab_depth"] > 1.2, "band notch too shallow to hold a band")

    area, lowest = unsupported_area(mesh)
    budget = 6 * f["tab_depth"] * cap.tab_w
    require(area < budget + 8.0,
            f"{area:.1f} mm2 over air against {budget:.1f} mm2 of notch bridging, "
            f"lowest at z={lowest:.2f} — something else is unsupported")
    f["unsupported"], f["budget"] = area, budget
    return f


if __name__ == "__main__":
    scope, cap = PROTO, LargeCap()
    part = build(scope, cap)
    stl, step, mesh, tess = emit(part, "proto_large_cap")
    f = check(scope, cap, part, mesh)

    print(f"scope      {scope.summary()}")
    print(f"cap        {f['across']:.1f} x {f['deep']:.1f} mm, {f['height']:.1f} mm tall, "
          f"{part.volume / 1000:.2f} cm3")
    print(f"aperture   {f['ap_across']:.2f} mm across vs a "
          f"{2 * math.sqrt(3) * scope.r_face(scope.length):.2f} mm optical face")
    print(f"           lip {cap.lip:.2f} mm over the mirror, {f['lip_lands']:.2f} mm of "
          f"edge left uncovered, {f['corner_bite']:.2f} mm bite at the corners")
    print(f"bore       straight at {cap.bore(scope):.2f} mm inradius, clearing the tube's "
          f"widest by {f['entry']:.2f} mm on the flats, {f['corner']:.2f} at the corners")
    print(f"           gap opens to {f['mouth_gap']:.2f} mm at the mouth, wall down to "
          f"{f['min_wall']:.2f} mm")
    print(f"bands      6 notches {f['tab_depth']:.1f} mm deep x {cap.tab_z:.1f} tall, "
          f"{cap.tab_from_vertex:.0f} mm from each vertex")
    print(f"           reaching {f['tab_edge']:.1f} of {f['tab_run']:.1f} mm of straight flat")
    print(f"mesh       {len(mesh.faces)} faces, watertight, {f['unsupported']:.1f} mm2 "
          f"over air vs a {f['budget']:.1f} mm2 budget, tessellation {tess:.1e}")
    print(f"wrote      {stl}, {step}")
