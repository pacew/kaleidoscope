#!/usr/bin/env python3
"""First-layer adhesion test, laid out over the side plate's actual footprint.

Run:  python3 cad/bed_test.py

Seven thin pads at the places the plate has to stick: its four corners, the
midpoints of its two long edges, and the middle. A few minutes of printing
instead of gambling an hour and three quarters.

Each pad carries that many raised ribs, so a pad can be named without having
to work out which corner of the bed it was on. Report a failure by rib count.

Print it with NO brim and NO other changes — the point is to see what the bed
does unaided. Then try to peel each pad up with a thumbnail: a sound one
resists and tears rather than lifting cleanly.
"""

from __future__ import annotations

import sys
import math
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import Box, Pos, Rot

from scope import Scope
from side_plate import SidePlate, build as build_plate
from small_cap import SmallCap
from verify import emit, require, sits_on_bed, unsupported_area


@dataclass(frozen=True)
class BedTest:
    pad: float = 15.0        # the narrow end is only 39 mm wide; two 18 mm
    #                          pads plus any inset will not fit across it
    thick: float = 0.4       # two layers at 0.2
    rib: float = 0.4         # raised on top, so the count is legible
    rib_len: float = 9.0
    rib_wide: float = 1.0
    rib_gap: float = 2.0
    inset: float = 13.0      # pull the outer pads in off the very edge


def stations(plate, angle: float, test: BedTest):
    """Where the plate has to stick: four corners, both long-edge midpoints,
    and the middle.

    Worked out in the plate's own frame rather than the bed's. Un-rotating by
    the bed angle makes the footprint axis-aligned, so the corners fall out of
    min/max — no convex hull, and no trouble from the end faces, which lean by
    the taper angle and project as slivers rather than clean edges.
    """
    a = math.radians(-angle)
    c, s_ = math.cos(a), math.sin(a)
    pts = [(v.X * c - v.Y * s_, v.X * s_ + v.Y * c)
           for v in plate.vertices() if abs(v.Z) < 0.01]
    if len(pts) < 4:
        raise SystemExit("no vertices found on the bed plane")

    ylo, yhi = min(p[1] for p in pts), max(p[1] for p in pts)
    near = [p[0] for p in pts if p[1] < ylo + 1.0]
    far = [p[0] for p in pts if p[1] > yhi - 1.0]
    xlo_n, xhi_n = min(near), max(near)
    xlo_f, xhi_f = min(far), max(far)

    ymid = (ylo + yhi) / 2
    m = test.pad / 2 + 2.0                       # keep each pad on the plate

    # The plate is not symmetric about x = 0 in its own frame -- it was centred
    # on its bed-frame bounding box, which leaves the centreline off to one
    # side. Pull toward the measured centre of each end, not toward zero.
    def inward(x, y, centre):
        return (x + math.copysign(m, centre - x), y + math.copysign(m, ymid - y))

    spots = [inward(xlo_n, ylo, (xlo_n + xhi_n) / 2),
             inward(xhi_n, ylo, (xlo_n + xhi_n) / 2),
             inward(xhi_f, yhi, (xlo_f + xhi_f) / 2),
             inward(xlo_f, yhi, (xlo_f + xhi_f) / 2)]

    # Mid-edge, which is where the first plate actually tore.
    spots += [((xhi_n + xhi_f) / 2 - m, ymid),
              ((xlo_n + xlo_f) / 2 + m, ymid)]

    # One more up the length. It cannot sit at the centroid: the plate is only
    # about 52 mm across at mid-length and three pads will not fit there.
    axis = ((xlo_n + xhi_n) / 2 + (xlo_f + xhi_f) / 2) / 2
    spots += [(axis, ymid + 45.0)]
    return spots                                 # still in the plate's frame


def build(test: BedTest, spots):
    part = None
    for n, (x, y) in enumerate(spots, start=1):
        pad = Pos(x, y, test.thick / 2) * Box(test.pad, test.pad, test.thick)
        span = (n - 1) * test.rib_gap
        for k in range(n):
            rx = x - span / 2 + k * test.rib_gap
            pad += Pos(rx, y, test.thick + test.rib / 2) * Box(
                test.rib_wide, test.rib_len, test.rib)
        part = pad if part is None else part + pad
    return part


if __name__ == "__main__":
    scope, test = Scope(), BedTest()
    plate, angle = build_plate(scope, SidePlate(), SmallCap())
    spots = stations(plate, angle, test)

    # Pads are built square to the plate and the whole set is turned with it.
    # Building them square to the BED instead looks fine until you check the
    # spacing: two pads 20 mm apart along the plate are only 16 mm apart as
    # axis-aligned boxes, because Chebyshev distance is not rotation-invariant.
    part = Rot(0, 0, angle) * build(test, spots)
    stl, step, mesh, tess = emit(part, "bed_test")

    bb = sits_on_bed(part)
    area, _ = unsupported_area(mesh)
    require(area < 0.5, f"{area:.1f} mm2 over air — pads should have none")
    require(len(spots) == 7, f"expected 7 stations, got {len(spots)}")
    widest = (len(spots) - 1) * test.rib_gap + test.rib_wide
    require(widest <= test.pad - 2,
            f"the {len(spots)}-rib pad spans {widest:.1f} mm on a {test.pad:.0f} mm "
            "pad — the outer ribs would hang over the edge and print over air")
    for i in range(len(spots)):
        for j in range(i + 1, len(spots)):
            gap = max(abs(spots[i][0] - spots[j][0]), abs(spots[i][1] - spots[j][1]))
            require(gap > test.pad + 3,
                    f"pads {i + 1} and {j + 1} are {gap:.1f} mm apart and would "
                    f"merge into one — they stop being independent tests")

    pbb = plate.bounding_box()
    print(f"plate      {pbb.max.X - pbb.min.X:.0f} x {pbb.max.Y - pbb.min.Y:.0f} mm "
          f"footprint at {angle:.1f} deg")
    print(f"test       {bb.max.X - bb.min.X:.0f} x {bb.max.Y - bb.min.Y:.0f} mm, "
          f"{len(spots)} pads of {test.pad:.0f} mm, {test.thick + test.rib:.1f} mm tall, "
          f"{part.volume / 1000:.2f} cm3")
    print(f"mesh       {len(mesh.faces)} faces, watertight, {area:.1f} mm2 unsupported")
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    print("\npad  ribs   position from bed centre")
    for n, (px, py) in enumerate(spots, start=1):
        x, y = px * ca - py * sa, px * sa + py * ca
        side = ("front" if y < -20 else "back" if y > 20 else "middle")
        hand = ("left" if x < -20 else "right" if x > 20 else "centre")
        print(f"{n:3d}  {n:4d}   x {x:+7.1f}  y {y:+7.1f}   {hand} {side}")
    print(f"\nwrote      {stl}")
    print("print with no brim, then try to peel each pad — a sound one tears "
          "rather than lifting")
