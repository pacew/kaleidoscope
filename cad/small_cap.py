#!/usr/bin/env python3
"""Small end cap for the tapered kaleidoscope.

Run:  python3 cad/small_cap.py

Prints floor-down, which is also how it is used: cap on the table, plates
dropped in one at a time until the bumps engage, then the mirrors.

A deliberately loose fit over the tube — three inward bumps drop into pockets
in the plates and do the holding. Each bump is ramped on top so a plate cams
over it going in, and flat on the bottom; that flat is what stops the cap
sliding back off.

Two changes from the 100 mm prototype's cap, both from things that build
taught us:

  * the bore's corner radius is small. Rounding a bore's corners removes
    clearance rather than adding it, and at 1.5 mm the corners were touching
    the plates' outer points with nothing to spare.
  * the aperture's lip is half a mirror thickness and its corners are as
    sharp as the nozzle allows. The lip only has to stop the mirrors falling
    through; what made it obtrusive was the corner radius, not the lip.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import (Plane, Polygon, RegularPolygon, Rot, extrude, fillet,
                       loft)

from scope import Scope, rounded_tri_area, rounded_tri_reach
from verify import emit, require, sits_on_bed, unsupported_area


@dataclass(frozen=True)
class SmallCap:
    skirt: float = 16.0        # how far up the plates it grips
    floor: float = 2.0         # end plate under the aperture
    wall: float = 2.5
    clearance: float = 0.3     # radial, on the flats
    corner: float = 0.4        # bore and aperture corners — keep this small
    lip: float = 0.0           # 0 means half a mirror thickness
    detent_z: float = 8.0      # from the plates' narrow end
    bump_w: float = 6.0
    bump_l: float = 3.0
    bump_h: float = 0.8
    ramp: float = 1.6          # lead-in length, in multiples of bump_h

    def lip_for(self, scope: Scope) -> float:
        return self.lip if self.lip else scope.mirror / 2


def _rtri(inradius: float, corner: float, z: float):
    """A rounded equilateral triangle on the plane z, clocked with vertices at
    90/210/330 to match the tube."""
    sk = RegularPolygon(radius=2 * inradius, side_count=3,
                        major_radius=True, rotation=90)
    return Plane.XY.offset(z) * fillet(sk.vertices(), corner)


def build(scope: Scope, cap: SmallCap):
    # Floor occupies z 0..floor; the skirt sits above it, so a point at cap
    # height h is over tube station h - floor.
    def bore(h: float) -> float:
        return scope.r_outer(h - cap.floor) + cap.clearance

    top = cap.floor + cap.skirt

    part = loft([_rtri(bore(0.0) + cap.wall, cap.corner + cap.wall, 0.0),
                 _rtri(bore(top) + cap.wall, cap.corner + cap.wall, top)])

    part -= loft([_rtri(bore(cap.floor), cap.corner, cap.floor),
                  _rtri(bore(top), cap.corner, top)])

    ap = scope.r_face(0.0) - cap.lip_for(scope)
    part -= extrude(_rtri(ap, cap.corner, -1.0), amount=cap.floor + 2.0)

    # One bump on the bottom flat, then rotated to the other two. Sketched in
    # the YZ plane, where local x is global Y (radially outward is -Y here)
    # and local y is the axis.
    zc = cap.floor + cap.detent_z
    h0, h1 = zc - cap.bump_l / 2, zc + cap.bump_l / 2
    r = bore(zc)
    pts = [(-r - 1.0, h0),                    # buried in the wall
           (-r + cap.bump_h, h0),             # flat bottom: the retaining face
           (-r + cap.bump_h, h1),
           (-r - 1.0, h1 + cap.ramp * cap.bump_h)]   # ramped top: the lead-in
    bump = extrude(Plane.YZ.offset(-cap.bump_w / 2) * Polygon(*pts, align=None),
                   amount=cap.bump_w)
    part = part + bump + Rot(0, 0, 120) * bump + Rot(0, 0, 240) * bump
    return part


def check(scope: Scope, cap: SmallCap, part, mesh) -> dict:
    facts = {}

    bb = sits_on_bed(part)
    facts["height"] = bb.max.Z
    facts["across"] = bb.max.X - bb.min.X

    # The bore's corners must clear the plates' outer points. Rounding pulls
    # the bore's corner in, so this goes negative if `corner` grows.
    for z, tag in ((0.0, "bottom"), (cap.skirt, "top")):
        gap = (rounded_tri_reach(scope.r_outer(z) + cap.clearance, cap.corner)
               - scope.corner_reach(z))
        require(gap > 0.3, f"bore corner clearance {gap:+.2f} mm at the skirt {tag} "
                           "— reduce SmallCap.corner")
        facts[f"corner_{tag}"] = gap

    require(cap.clearance > 0, "bore has no clearance on the flats")

    # The lip must catch the mirrors without eating the view.
    lip = cap.lip_for(scope)
    require(lip >= scope.mirror / 2 - 1e-9,
            f"lip {lip:.3f} mm is less than half a mirror thickness")
    require(lip < scope.mirror, f"lip {lip:.3f} mm covers the whole mirror edge")
    facts["lip"] = lip
    # a uniform inward offset pulls a triangle's vertices in by twice the offset
    facts["corner_bite"] = 2 * lip + cap.corner

    # The bump has to reach past the plates' outer face to engage at all.
    engage = cap.bump_h - cap.clearance
    require(engage > 0.2, f"bump only reaches {engage:+.2f} mm past the plate face")
    require(engage < scope.plate, "bump would punch through the plate")
    facts["engage"] = engage

    area, lowest = unsupported_area(mesh)
    require(area < 30.0, f"{area:.1f} mm2 of downward-facing area above the bed, "
                         f"lowest at z={lowest:.2f} — something is printing over air")
    facts["unsupported"] = area
    return facts


if __name__ == "__main__":
    scope, cap = Scope(), SmallCap()
    part = build(scope, cap)
    stl, step, mesh, tess = emit(part, "small_cap")
    facts = check(scope, cap, part, mesh)

    print(f"scope      {scope.summary()}")
    print(f"cap        {facts['across']:.1f} mm across, {facts['height']:.1f} mm tall, "
          f"{part.volume / 1000:.2f} cm3")
    print(f"bore       {scope.r_outer(0) + cap.clearance:.2f} -> "
          f"{scope.r_outer(cap.skirt) + cap.clearance:.2f} mm inradius, "
          f"{cap.clearance:.2f} mm on the flats")
    print(f"corners    clear by {facts['corner_bottom']:.2f} mm "
          f"(was 0.00 on the prototype's cap)")
    print(f"aperture   lip {facts['lip']:.3f} mm = half a mirror; "
          f"corners bite {facts['corner_bite']:.2f} mm")
    print(f"detent     bump engages {facts['engage']:.2f} mm past the plate face")
    print(f"mesh       {len(mesh.faces)} faces, watertight, "
          f"{facts['unsupported']:.1f} mm2 unsupported, "
          f"tessellation {tess:.1e}")
    print(f"wrote      {stl}, {step}")
