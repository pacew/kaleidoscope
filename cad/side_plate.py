#!/usr/bin/env python3
"""Side plate for the tapered kaleidoscope. Print three.

Run:  python3 cad/side_plate.py

Flat, mitred 30 degrees on both long edges, which is what closes three of them
into a 60 degree corner. The mirror rests straight on the inner face, so that
face sits one mirror thickness outboard of the optical plane and the plate is
noticeably wider than its mirror.

The outer face runs sqrt(3)*plate past the inner one, so the zero-thickness
feather edge is the tube's OUTSIDE corner. Truncating it costs nothing
optically and leaves a small V-notch down each outer corner that the collar
bridges; untruncated it will not print at all.

Prints outer face down, cross-section narrowing upward, so the mitres lean
inward rather than overhang. The mirror seat is a top surface with nothing
between it and the mirror, so turn ironing on.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import Plane, Polygon, Pos, Rectangle, Rot, Vector, extrude, loft

from scope import S3, Scope
from small_cap import SmallCap
from verify import emit, require, sits_on_bed, unsupported_area


BED = (250.0, 210.0)             # MK3, nominal


def bed_angle(part, bed=BED):
    """Rotation about Z that leaves the most room on the bed.

    Optimised on the part's own vertices rather than its bounding rectangle:
    the footprint is a trapezoid, and packing the real outline rather than the
    box it fits in is worth about 9 mm on each axis here.
    """
    pts = [(v.X, v.Y) for v in part.vertices()]
    best = None
    for tenths in range(0, 1800):
        t = math.radians(tenths / 10)
        c, s_ = math.cos(t), math.sin(t)
        xs = [x * c - y * s_ for x, y in pts]
        ys = [x * s_ + y * c for x, y in pts]
        bx, by = max(xs) - min(xs), max(ys) - min(ys)
        r = max(bx / bed[0], by / bed[1])
        if best is None or r < best[0]:
            best = (r, tenths / 10, bx, by)
    return best[1], best[2], best[3]


@dataclass(frozen=True)
class SidePlate:
    side_clear: float = 1.0      # lateral; nothing bears here, so stay generous
    clear_low: float = 0.35      # THE wall that bears, and so the axial play
    clear_high: float = 1.0      # never bears; generous, for an easy snap in
    depth_clear: float = 1.0     # radial, into the plate


def pocket_dims(plate: SidePlate, cap: SmallCap):
    """Width, axial span and depth of the detent pocket, taken from the cap's
    bump — including its position, so the two parts cannot drift apart.

    The span is deliberately lopsided. The plate bottoms out on the cap's floor,
    so the only direction it can move is back out, and that brings the pocket's
    LOW wall up against the bump's flat underside. That wall alone sets the play.
    The HIGH wall never bears, so it keeps a generous clearance to make the bump
    easy to snap over on the way in.
    """
    w = cap.bump_w + 2 * plate.side_clear
    lo = cap.detent_z - cap.bump_l / 2 - plate.clear_low
    hi = cap.detent_z + cap.bump_l / 2 + plate.clear_high
    return w, lo, hi, cap.bump_h + plate.depth_clear


def profile(scope: Scope, z: float) -> list[tuple[float, float]]:
    """Cross-section at station z. Face at the bottom, outward -Y."""
    rp, ro, land = scope.r_seat(z), scope.r_outer(z), scope.miter_land
    xi, xo = S3 * rp, S3 * (ro - land)
    return [(-xi, -rp), (xi, -rp),
            (xo, -ro + land), (xo, -ro),
            (-xo, -ro), (-xo, -ro + land)]


def build(scope: Scope, plate: SidePlate, cap: SmallCap):
    part = loft([Plane.XY * Polygon(*profile(scope, 0.0), align=None),
                 Plane.XY.offset(scope.length)
                 * Polygon(*profile(scope, scope.length), align=None)])

    # Detent pocket, cut on a plane parallel to the outer face. Doing it here
    # rather than after the lay-flat keeps the position expressed in tube
    # stations, where it is the same number the cap uses.
    w, lo, hi, d = pocket_dims(plate, cap)
    face = Plane(origin=(0, -scope.r_outer(0.0), 0),
                 x_dir=(1, 0, 0),
                 z_dir=Vector(0, -1, -scope.taper)).offset(1.0)
    along = (lo + hi) / 2 * math.sqrt(1 + scope.taper**2)
    part -= extrude(face * (Pos(0, along) * Rectangle(w, hi - lo)), amount=-(1.0 + d))

    # Lay the outer face on the bed. It is tilted from the axis by the taper,
    # so this is a rotation of (90 - taper) about X, not a flat 90.
    part = Rot(math.degrees(math.atan(1 / scope.taper)), 0, 0) * part
    bb = part.bounding_box()
    part = Pos(-(bb.min.X + bb.max.X) / 2,
               -(bb.min.Y + bb.max.Y) / 2,
               -bb.min.Z) * part

    # Turn it to the diagonal it has to sit on anyway, so the STL imports
    # ready to place instead of needing to be rotated by hand.
    angle, _, _ = bed_angle(part)
    part = Rot(0, 0, angle) * part
    bb = part.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2,
               -(bb.min.Y + bb.max.Y) / 2,
               -bb.min.Z) * part, angle


def check(scope: Scope, plate: SidePlate, cap: SmallCap, part, mesh) -> dict:
    facts = {}
    bb = sits_on_bed(part)
    facts["footprint"] = (bb.max.X - bb.min.X, bb.max.Y - bb.min.Y)
    facts["height"] = bb.max.Z

    require(scope.miter_land < scope.plate,
            "mitre truncation is thicker than the plate")

    # The mirror has to land on this plate, both its leading edge and the
    # surplus at the other end.
    lead = S3 * scope.r_seat(0.0) - S3 * scope.r_face(0.0)
    over = lead - scope.mirror_overlap
    require(lead > 0.5, f"only {lead:.2f} mm of plate beyond the mirror's leading edge")
    require(over > 0.5, f"only {over:.2f} mm of plate beyond the mirror's overlap edge")
    facts["margin_lead"], facts["margin_over"] = lead, over

    require(scope.mirror_overlap < scope.overlap_limit,
            f"overlap {scope.mirror_overlap} exceeds {scope.overlap_limit:.2f} mm "
            "and would foul the neighbouring plate")
    facts["overlap_limit"] = scope.overlap_limit

    w, lo, hi, d = pocket_dims(plate, cap)
    require(plate.clear_low > 0.1,
            "the pocket's bearing wall has no clearance — the bump will not drop in")
    facts["play"] = plate.clear_low
    require(d < scope.plate - 0.6, f"detent pocket {d:.2f} mm leaves too little "
                                   f"under it in a {scope.plate} mm plate")
    facts["pocket_depth"] = d

    # The only thing that should be printing over air is the roof of the
    # detent pocket, which is a bridge across its short span -- routine. Any
    # more than that and something is genuinely floating, so expect the exact
    # figure rather than picking a threshold.
    area, lowest = unsupported_area(mesh)
    roof = w * (hi - lo)
    require(area <= roof + 1.0,
            f"{area:.1f} mm2 unsupported, more than the {roof:.1f} mm2 detent "
            f"pocket roof -- something else is over air, lowest at z={lowest:.2f}")
    facts["unsupported"], facts["roof"] = area, roof
    facts["bridge"] = min(w, hi - lo)
    return facts


if __name__ == "__main__":
    scope, plate, cap = Scope(), SidePlate(), SmallCap()
    part, angle = build(scope, plate, cap)
    stl, step, mesh, tess = emit(part, "side_plate")
    f = check(scope, plate, cap, part, mesh)

    fx, fy = f["footprint"]
    print(f"scope      {scope.summary()}")
    print(f"plate      {fx:.1f} x {fy:.1f} mm footprint, {f['height']:.2f} mm tall")
    print(f"           inner face {2 * S3 * scope.r_seat(0):.2f} -> "
          f"{2 * S3 * scope.r_seat(scope.length):.2f} mm")
    print(f"mirror     margin {f['margin_lead']:.2f} mm at the leading edge, "
          f"{f['margin_over']:.2f} mm at the overlap edge")
    print(f"           overlap {scope.mirror_overlap:.2f} of {f['overlap_limit']:.2f} mm allowed")
    pw, plo, phi, _ = pocket_dims(plate, cap)
    print(f"detent     pocket {pw:.1f} x {phi - plo:.2f} x {f['pocket_depth']:.1f} mm deep, "
          f"spanning z {plo:.2f} to {phi:.2f}")
    print(f"           {f['play']:.2f} mm of axial play, all of it at the low wall "
          f"(was 1.00 nominal, 0.50 measured)")
    print(f"mesh       {len(mesh.faces)} faces, watertight, tessellation {tess:.1e}")
    print(f"           {f['unsupported']:.1f} mm2 over air = the pocket roof, "
          f"a {f['bridge']:.0f} mm bridge")

    ok = fx <= BED[0] and fy <= BED[1]
    require(ok, f"{fx:.1f} x {fy:.1f} mm will not fit a {BED[0]:.0f}x{BED[1]:.0f} bed")
    print(f"bed        pre-rotated {angle:.1f} deg -> {fx:.1f} x {fy:.1f} mm, "
          f"{BED[0] - fx:.1f} / {BED[1] - fy:.1f} mm clear on a "
          f"{BED[0]:.0f}x{BED[1]:.0f} MK3")
    print(f"wrote      {stl}, {step}")
