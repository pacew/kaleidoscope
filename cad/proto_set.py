#!/usr/bin/env python3
"""A second, short scope sized around the mirrors already cut for the prototype.

Run:  python3 cad/proto_set.py

Three mirrors exist and are cut: parallel edges 26.40 and 51.80 mm, height
100.268 mm between them, legs 101.069 mm. They came off the prototype-era
template (git b477f4b) and they are the fixed input here — the plastic is sized
to them, not the other way round.

WHY THIS IS NOT JUST THE OLD PROTOTYPE REPRINTED

The prototype's plate seats were cut for 1.5875 mm stock. The stock actually
measures 1.68. On the 255 mm scope that error is stuck in printed parts and has
to be absorbed, but nothing here is printed yet, so this set is built around the
real number: `mirror` and `mirror_stock` are both 1.68 and the optical faces
come out at exactly 25.40 and 50.80, which is what the blanks were drawn for.
The 1.00 mm overlap they carry is then the intended 1.00, not the 1.32 it would
be if the old seats were reused.

Everything else — the lopsided detent pocket, the opened aperture, the split
bore/aperture corner radii — carries over from the 255 mm work unchanged,
because those are all fixes to the parts rather than to the tube.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scope import Scope, S3
from small_cap import SmallCap, build as build_cap, check as check_cap
from side_plate import (BED, SidePlate, build as build_plate,
                        check as check_plate, pocket_dims)
from collar import Collar, build as build_collar, check as check_collar
from verify import emit, require

# Mirrors already in hand. Measured off the template they were cut from, so
# these are the numbers the plastic has to match, to within saw accuracy.
BLANK_NARROW = 26.40
BLANK_WIDE = 51.80
BLANK_HEIGHT = 100.268
BLANK_LEG = 101.069

PROTO = Scope(length=100.0,
              mirror=1.68,        # the seats are cut for the REAL thickness
              mirror_stock=1.68,  # so there is no as-built offset to absorb
              mirror_overlap=1.0)

COLLAR_SEAT = 74.0               # spans 74-90, ten clear of the wide opening


def check_blanks(scope: Scope) -> dict:
    """The whole point of this set: the mirrors on the bench have to fit it."""
    got = {"narrow": scope.blank_width(0),
           "wide": scope.blank_width(scope.length),
           "height": scope.blank_height,
           "leg": scope.blank_leg}
    want = {"narrow": BLANK_NARROW, "wide": BLANK_WIDE,
            "height": BLANK_HEIGHT, "leg": BLANK_LEG}
    for k in want:
        require(abs(got[k] - want[k]) < 0.01,
                f"blank {k} wants {want[k]:.3f} mm but this scope needs "
                f"{got[k]:.3f} — the cut mirrors will not fit")

    require(scope.optical_shift == 0.0,
            "seats are cut for a different thickness than the stock, so the "
            "faces will not land where the blanks were drawn for")
    require(scope.mirror_overlap < scope.overlap_limit,
            f"overlap {scope.mirror_overlap:.2f} exceeds the {scope.overlap_limit:.2f} mm "
            "the void behind the neighbouring mirror can swallow")
    return got


if __name__ == "__main__":
    scope = PROTO
    print(f"scope      {scope.summary()}")
    got = check_blanks(scope)
    print(f"blanks     needs {got['narrow']:.2f} / {got['wide']:.2f} mm parallel, "
          f"height {got['height']:.3f}, legs {got['leg']:.3f}")
    print(f"           have  {BLANK_NARROW:.2f} / {BLANK_WIDE:.2f} mm parallel, "
          f"height {BLANK_HEIGHT:.3f}, legs {BLANK_LEG:.3f}  -> match")
    print(f"           overlap {scope.mirror_overlap:.2f} of "
          f"{scope.overlap_limit:.2f} mm allowed")

    # Band notches on: this scope's only collar sits at 74, which leaves 2.67 mm
    # on the flats, and the large cap is held on by rubber bands rather than by
    # snap arms.
    cap = SmallCap(tab_out=2.0)
    part = build_cap(scope, cap)
    stl, step, mesh, tess = emit(part, "proto_small_cap")
    f = check_cap(scope, cap, part, mesh)
    print(f"\ncap        {f['across']:.1f} mm across, {f['height']:.1f} mm tall, "
          f"{part.volume / 1000:.2f} cm3")
    print(f"           bore {scope.r_outer(0) + cap.clearance:.2f} -> "
          f"{scope.r_outer(cap.skirt) + cap.clearance:.2f} mm inradius, corners "
          f"clear by {f['corner_bottom']:.2f}")
    print(f"           lip {f['lip']:.3f} mm on the flats, {f['corner_bite']:.2f} at "
          f"the corners, mirror bears on {f['bearing']:.2f} mm of floor")
    print(f"           6 band notches {f['tab_depth']:.1f} mm deep x {cap.tab_z:.1f} tall, "
          f"standing {f['tab_reach']:.2f} mm from the axis")
    print(f"           {len(mesh.faces)} faces, watertight -> {stl}")

    plate = SidePlate()
    part, angle = build_plate(scope, plate, cap)
    stl, step, mesh, tess = emit(part, "proto_side_plate")
    f = check_plate(scope, plate, cap, part, mesh)
    fx, fy = f["footprint"]
    require(fx <= BED[0] and fy <= BED[1],
            f"{fx:.1f} x {fy:.1f} mm will not fit a {BED[0]:.0f}x{BED[1]:.0f} bed")
    print(f"\nplate      {fx:.1f} x {fy:.1f} mm footprint at {angle:.1f} deg, "
          f"{f['height']:.2f} mm tall, {part.volume / 1000:.2f} cm3")
    print(f"           inner face {2 * S3 * scope.r_seat(0):.2f} -> "
          f"{2 * S3 * scope.r_seat(scope.length):.2f} mm")
    print(f"           mirror margin {f['margin_lead']:.2f} leading, "
          f"{f['margin_over']:.2f} overlap")
    pw, plo, phi, _ = pocket_dims(plate, cap)
    print(f"           pocket {pw:.1f} x {phi - plo:.2f} x {f['pocket_depth']:.1f} deep, "
          f"z {plo:.2f}-{phi:.2f}, {f['play']:.2f} mm play")
    print(f"           {len(mesh.faces)} faces, watertight -> {stl}   (print 3)")

    collar = Collar(seat=COLLAR_SEAT)
    part = build_collar(scope, collar)
    stl, step, mesh, tess = emit(part, f"proto_collar_{COLLAR_SEAT:.0f}")
    f = check_collar(scope, collar, part, mesh, cap)
    print(f"\ncollar     seat {COLLAR_SEAT:.0f}-{COLLAR_SEAT + collar.length:.0f} mm, "
          f"{f['across']:.1f} mm across, {part.volume / 1000:.2f} cm3")
    print(f"           corners clear by {f['corner_mouth']:.2f} mm, clears the cap "
          f"by {f['over_cap']:.1f} mm, its band notches by {f['over_tabs']:.2f} mm")
    print(f"           far edge {scope.length - COLLAR_SEAT - collar.length:.1f} mm "
          f"from the wide opening, seat drifts {f['drift']:.0f} mm per mm")
    print(f"           {len(mesh.faces)} faces, watertight -> {stl}")
