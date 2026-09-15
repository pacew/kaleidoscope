#!/usr/bin/env python3
"""Object cell for the scope: two windows with loose jewels tumbling between.

Run:  python3 cad/jewel_frame.py

Three parts. The body has an annular ledge and a coarse helical groove in its
bore. Window one drops onto the ledge, a plain spacer tube drops on top of it,
window two on top of that, and a threaded ring screws in and clamps the whole
stack. The chamber is the spacer's bore, sealed by a window at each end.

ONE THREAD, NOT TWO

The obvious way to hold two windows is to thread the retaining ring on its
outside as well and put a second cap over it. That works, but it needs two
mating threads to print correctly instead of one, and the chamber depth is then
locked into a threaded part. This way the depth lives in a plain tube: to try a
different chamber, reprint `spacer` and nothing else. Everything down to window
two also drops straight through the bore, because the groove is cut OUTWARD from
it and the bore's minimum diameter never changes.

WHY LOOSE, NOT GLUED

Glued jewels give one fixed picture. Loose ones tumble every time the cell is
moved, and PVA on smooth sheet is a poor bond anyway. The only cost is that the
cell has to actually seal — see the note about piece size below.

THE THREAD HAS TO REACH THE RIM

The rib's crest stands proud of the plain bore, so the ring cannot be pushed in
and then engaged; it has to be threaded from the mouth. An earlier version put
the groove in the middle of the bore, built cleanly, passed every check, and
could not have been assembled. There is now a check for it.

Prints ledge-down, all three. Thread flanks are 45 degrees, so the slicer sees
walls rather than ceilings and nothing needs support.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import (Align, Box, Cylinder, Helix, Plane, Polygon, Pos, Rot,
                       sweep)

from verify import emit, require, sits_on_bed, unsupported_area

MIN = (Align.CENTER, Align.CENTER, Align.MIN)


@dataclass(frozen=True)
class JewelCell:
    disk_dia: float = 75.0     # NOMINAL, to cut to. The first disk came off a
    #                            jar lid at 74.1 and was a good guess; the stock
    #                            will not give much more anyway
    disk_t: float = 0.3        # measured, and barely used — see the docstring

    pocket: float = 76.5       # bore everything drops into. Sized for a
    #                            hand-cut disk, not a measured one: 75 +1.5/-0,
    #                            so all four come out of the stock usable
    ledge: float = 4.0         # annular rest for a window. Widened from 3.0 to
    #                            thicken the ring's wall, so a pin can be driven
    #                            below the surface without bottoming out
    floor: float = 2.0
    body_od: float = 84.0      # leaves 2.05 mm of solid wall for the pin to grip
    #                            before it breaks into the groove

    # The jewels, measured. These drive the chamber depth and are checked
    # against it, because "will they tumble" is not a judgement call once you
    # have the numbers — see check().
    jewel_min: float = 11.0    # thinnest dimension of the thinnest piece
    jewel_pass: float = 15.0   # gap they drop through in almost any attitude
    jewel_max: float = 20.0    # longest dimension of the longest piece
    jewel_g: float = 1.6

    spacer_h: float = 15.0     # THE CHAMBER DEPTH. Set to jewel_pass: a chamber
    #                            IS a caliper gap the pieces must fall through
    #                            in whatever attitude they happen to be in.
    spacer_gap: float = 0.6     # diametral clearance in the bore. It does not
    #                            turn, so it can be closer than the ring
    chamber: float = 0.0        # 0 = full aperture. Set smaller to concentrate
    #                            the pieces into a denser field

    pitch: float = 5.0
    groove_depth: float = 1.7
    groove_half: float = 1.8

    ring_od: float = 75.5
    recess: float = 0.6        # how far the ring's top finishes BELOW the rim.
    #                            Parts measured 0.30 under model on the second
    #                            coupon, so expect about 0.9 in the hand
    rib_z: float = 2.0
    rib_turns: float = 1.0
    rib_depth: float = 1.5
    rib_half: float = 1.5      # 45 degree flanks, which is why it prints

    # 1.8 needed pliers on 1.75 mm filament, so these are the press fit to test.
    # The BODY's slot is the grip — it has twice the depth of the ring's hole —
    # so the coupon carries one slot per width and the ring's holes stay loose.
    # 1.8 as a round hole through 3.05 mm needed pliers; 1.90 as a slot through
    # 2.05 barely resisted. A slot grips on two flats instead of all round and
    # has less length, so it wants to be narrower. These three bracket it, and
    # they stay on the FINAL part: only one gets pinned, the other two read as
    # three-fold detailing. Flutes beside each one count out its rank, tightest
    # first — otherwise there is no way to tell them apart on a round body.
    pin_widths: tuple = (1.72, 1.79, 1.86)
    pin_ring_d: float = 2.4    # deliberately generous: never the tight part
    pin_deep: float = 2.4      # blind, in the ring's 3.5 mm wall. Deeper than
    #                            the pin needs, so it can be driven below the
    #                            outer surface without bottoming
    pin_n: int = 12            # so one is always within 15 degrees of tight
    slot_h: float = 5.0        # VERTICAL SLOT, not a hole. Measured seating ran
    #                            about 1 mm below nominal — accumulated print
    #                            error, not an arithmetic mistake — and a round
    #                            hole cannot absorb that. A slot also means a
    #                            different spacer no longer needs a new body.

    notch_n: int = 6           # spanner notches. Wider and deeper than before,
    notch_w: float = 4.0       # because a recessed ring cannot be gripped by
    notch_deep: float = 2.0    # its edge — these are now the only purchase
    rim_margin: float = 2.5    # material above the pin slot

    # ---- derived -----------------------------------------------------------

    @property
    def aperture(self) -> float:
        return self.pocket - 2 * self.ledge

    @property
    def bore_dia(self) -> float:
        """Chamber diameter — the spacer's bore."""
        return self.chamber or self.aperture

    @property
    def stack(self) -> float:
        """Window, spacer, window."""
        return 2 * self.disk_t + self.spacer_h

    @property
    def seated(self) -> float:
        """Where the ring's base ends up once it is down on the stack."""
        return self.floor + self.stack

    @property
    def ring_pin_z(self) -> float:
        """As LOW on the ring as it will go, just clear of the rib.

        Not mid-band. Low here means the body can be shorter, and — because
        ring_h then drops out of the body's height entirely — the ring can be
        made as tall as you like for free, so it stands proud of the rim
        instead of sinking below it.
        """
        return (self.rib_z + self.rib_turns * self.pitch + self.rib_half
                + self.pin_ring_d / 2 + 0.4)

    @property
    def pin_z(self) -> float:
        """The body's hole follows the ring's, so the two cannot disagree.

        Note what this makes the pin: height-specific. Change spacer_h and the
        BODY has to be reprinted too for the holes to meet. The spacer is still
        the cheap part for TRYING depths — just leave the pin out until the
        depth is settled.
        """
        return self.seated + self.ring_pin_z

    @property
    def body_h(self) -> float:
        return self.pin_z + self.slot_h / 2 + self.rim_margin

    @property
    def ring_h(self) -> float:
        """Set so the ring finishes `recess` below the rim, which is what the
        body's height works out to minus the recess. Nothing else wants a
        particular ring height — the pin sits low enough to be out of it."""
        return self.ring_pin_z + self.slot_h / 2 + self.rim_margin - self.recess

    @property
    def groove_z(self) -> float:
        return self.floor + self.groove_half + 0.5

    @property
    def groove_turns(self) -> float:
        """Long enough to cover the seated rib AND break out of the rim."""
        need = max(self.body_h + 0.5, self.rib_span()[1])
        return math.ceil((need - self.groove_z - self.groove_half)
                         / self.pitch * 10) / 10

    @property
    def chamber_cc(self) -> float:
        return math.pi * (self.bore_dia / 2) ** 2 * self.spacer_h / 1000.0

    def rib_span(self):
        """Where the rib reaches in BODY coordinates, once seated."""
        lo = self.seated + self.rib_z - self.rib_half
        hi = self.seated + self.rib_z + self.rib_turns * self.pitch + self.rib_half
        return lo, hi

    def groove_span(self):
        lo = self.groove_z - self.groove_half
        hi = self.groove_z + self.groove_turns * self.pitch + self.groove_half
        return lo, hi


def _thread(radius: float, z0: float, turns: float, pitch: float,
            depth: float, half: float, into: float = 0.3):
    """A helical triangular thread about the Z axis. The profile's x is radial
    and its normal tangential, so it stays square to the helix all the way."""
    helix = Helix(pitch, turns * pitch, radius, center=(0, 0, z0))
    profile = Plane(origin=(radius, 0, z0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * Polygon(
        (-into, -half), (depth, 0.0), (-into, half), align=None)
    return sweep(profile, path=helix, is_frenet=True)


def build_body(c: JewelCell):
    part = Cylinder(c.body_od / 2, c.body_h, align=MIN)
    part -= Pos(0, 0, c.floor) * Cylinder(c.pocket / 2, c.body_h - c.floor + 1.0,
                                          align=MIN)
    part -= Pos(0, 0, -1.0) * Cylinder(c.aperture / 2, c.floor + 2.0, align=MIN)
    part -= _thread(c.pocket / 2, c.groove_z, c.groove_turns, c.pitch,
                    c.groove_depth, c.groove_half)
    outer, inner = c.body_od / 2 + 1.0, c.pocket / 2 - 1.0
    for i, w in enumerate(c.pin_widths):
        ang = i * 360.0 / len(c.pin_widths)
        slot = Pos(0, -(outer + inner) / 2, c.pin_z) * Box(
            w, outer - inner, c.slot_h)
        part -= Rot(0, 0, ang) * slot
        # Rank flutes: full height, so they are plain vertical cuts with no
        # ceiling anywhere. i+1 of them, tightest slot marked with one.
        for k in range(i + 1):
            flute = Pos(4.0 + 3.0 * k, -(c.body_od / 2 + 0.1), c.body_h / 2) * Box(
                1.2, 1.8, c.body_h + 2.0)
            part -= Rot(0, 0, ang) * flute
    return part


def build_spacer(c: JewelCell):
    od = c.pocket - c.spacer_gap
    part = Cylinder(od / 2, c.spacer_h, align=MIN)
    part -= Pos(0, 0, -1.0) * Cylinder(c.bore_dia / 2, c.spacer_h + 2.0, align=MIN)
    return part


def build_ring(c: JewelCell):
    part = Cylinder(c.ring_od / 2, c.ring_h, align=MIN)
    part -= Pos(0, 0, -1.0) * Cylinder(c.aperture / 2, c.ring_h + 2.0, align=MIN)
    part += _thread(c.ring_od / 2, c.rib_z, c.rib_turns, c.pitch,
                    c.rib_depth, c.rib_half)

    outer, inner = c.ring_od / 2 + 1.0, c.ring_od / 2 - c.pin_deep
    for i in range(c.pin_n):
        hole = Pos(0, -(outer + inner) / 2, c.ring_pin_z) * Cylinder(
            c.pin_ring_d / 2, outer - inner, rotation=(90, 0, 0))
        part -= Rot(0, 0, i * 360.0 / c.pin_n) * hole

    # Notches run out past the rim rather than landing on it: a cut face
    # coincident with the top face is what OCC turns into a leak.
    reach = (c.ring_od - c.aperture) / 2 + 4.0
    for i in range(c.notch_n):
        slot = Pos(0, -(c.aperture / 2 - 1.0 + reach / 2),
                   c.ring_h - c.notch_deep + 1.0) * Box(
            c.notch_w, reach, c.notch_deep + 2.0)
        part -= Rot(0, 0, i * 360.0 / c.notch_n) * slot
    return part


def _depth_checks(c: JewelCell, d: dict):
    require(c.spacer_h >= c.jewel_pass,
            f"chamber {c.spacer_h:.1f} is under the {c.jewel_pass:.1f} mm gap the "
            "pieces fall through freely — they would only fit one way up and would "
            "sit where you put them instead of tumbling")
    require(c.spacer_h < c.jewel_max,
            f"chamber {c.spacer_h:.1f} clears the {c.jewel_max:.1f} mm long axis, so "
            "pieces can stand on end and leave the object plane")
    require(c.spacer_h < 2 * c.jewel_min,
            f"chamber {c.spacer_h:.1f} is over twice the {c.jewel_min:.1f} mm minimum "
            "thickness, so pieces can stack and shadow each other")
    d["tumble"] = c.spacer_h - c.jewel_pass
    d["no_stack"] = 2 * c.jewel_min - c.spacer_h
    d["no_stand"] = c.jewel_max - c.spacer_h


def check(c: JewelCell, parts, meshes) -> dict:
    d = {}
    for p in parts.values():
        sits_on_bed(p)

    require(c.pocket > c.disk_dia + 0.3,
            f"pocket {c.pocket:.2f} does not clear the {c.disk_dia:.2f} mm windows")
    d["slack"] = c.pocket - c.disk_dia
    require(c.aperture < c.disk_dia - 4.0, "less than 2 mm of window on the ledge")
    d["rest"] = (c.disk_dia - c.aperture) / 2

    # The spacer has to land on window one's rim and carry window two's, so it
    # needs a bearing annulus at both ends, and it has to drop through the bore.
    sp_od = c.pocket - c.spacer_gap
    require(sp_od < c.pocket - 0.3, "spacer will not drop into the bore")
    require(sp_od > c.bore_dia + 3.0,
            f"spacer bears on only {(sp_od - c.bore_dia) / 2:.2f} mm of window rim")
    # A chamber is a caliper gap. Three separate things it has to satisfy, and
    # they bracket the depth from both sides. Skipped when no jewels are given,
    # which is how the fit coupon gets away with a 5 mm chamber.
    if c.jewel_pass <= 0:
        d["tumble"] = d["no_stack"] = d["no_stand"] = float("nan")
    else:
        _depth_checks(c, d)
    require(c.bore_dia <= c.aperture,
            f"chamber {c.bore_dia:.1f} is wider than the {c.aperture:.1f} aperture, so "
            "the spacer's own wall would be in the picture")
    d["sp_od"], d["sp_bear"] = sp_od, (sp_od - c.bore_dia) / 2
    d["seal"] = (c.disk_dia - c.bore_dia) / 2

    require(c.ring_od < c.pocket - 0.5, "ring will not turn in the bore")
    d["turn_gap"] = (c.pocket - c.ring_od) / 2
    d["bear"] = (c.ring_od - c.aperture) / 2

    crest = (c.pocket / 2 + c.groove_depth) - (c.ring_od / 2 + c.rib_depth)
    require(crest > 0.3, f"rib crest fouls the groove bottom by {crest:+.2f} mm")
    require(c.groove_half - c.rib_half > 0.2, "no axial slack in the thread flanks")
    require(c.pitch > 2 * c.groove_half + 0.5, "pitch too fine for this groove")
    d["crest"], d["flank"] = crest, c.groove_half - c.rib_half
    d["engage"] = (c.ring_od / 2 + c.rib_depth) - c.pocket / 2
    require(d["engage"] > 0.6, f"only {d['engage']:.2f} mm of rib inside the bore")

    rlo, rhi = c.rib_span()
    glo, ghi = c.groove_span()
    require(glo <= rlo and rhi <= ghi,
            f"seated on a {c.stack:.2f} mm stack the rib spans {rlo:.2f}..{rhi:.2f}, "
            f"but the groove only covers {glo:.2f}..{ghi:.2f} — it would bottom out "
            "on thread instead of on the windows")
    d["rib"], d["groove"] = (rlo, rhi), (glo, ghi)
    d["thread_margin"] = min(rlo - glo, ghi - rhi)

    require(ghi >= c.body_h,
            f"groove stops at {ghi:.2f} inside a {c.body_h:.1f} mm bore — the rib's "
            f"crest is {d['engage']:.2f} mm wider than the bore, so it cannot be "
            "introduced anywhere but the mouth")
    d["groove_out"] = ghi - c.body_h

    require(c.pin_z + c.slot_h / 2 < c.body_h - 0.8, "body pin slot breaks the rim")
    d["slot_range"] = c.slot_h - max(c.pin_widths)
    solid = c.body_od / 2 - (c.pocket / 2 + c.groove_depth)
    require(solid > 1.5, f"only {solid:.2f} mm of wall outboard of the groove")
    d["pin_wall"] = solid
    require(min(c.pin_widths) < c.pin_ring_d - 0.2,
            "the ring's hole is not looser than the body's slot, so it — not the "
            "slot — would set the press fit, and it has half the grip length")
    require(c.pin_deep < (c.ring_od - c.aperture) / 2 - 0.6,
            "pin hole breaks into the ring's bore")
    top = c.ring_h - c.notch_deep
    require(c.ring_pin_z + c.pin_ring_d / 2 < top - 0.3, "ring pin hole hits the notches")
    require(c.ring_pin_z - c.pin_ring_d / 2 > c.rib_z + c.rib_turns * c.pitch + c.rib_half,
            f"ring pin hole at {c.ring_pin_z:.2f} lands in the rib")
    d["hole_deep"] = (c.body_od - c.pocket) / 2 + d["turn_gap"] + c.pin_deep
    d["pin_len"] = d["hole_deep"] - 1.0     # so it can be driven under
    d["proud"] = c.seated + c.ring_h - c.body_h
    require(-2.0 < d["proud"] < -0.2,
            f"ring finishes {d['proud']:+.2f} mm against the rim; it should sit "
            "slightly under, but not so deep the notches are out of reach")
    require(c.ring_h - c.notch_deep - c.pin_ring_d / 2 - 0.3 > c.ring_pin_z,
            f"ring is {c.ring_h:.2f} tall: the notches would break into the pin "
            "holes. Deepen the slot or shrink the notches.")

    # Budgets from the geometry rather than from taste: the slots bridge their
    # own width across the wall, and each ring hole roofs its own bore.
    slot_bridge = sum(c.pin_widths) * (c.body_od / 2 + 1.0 - (c.pocket / 2 - 1.0))
    for tag, budget in (("body", slot_bridge + 8.0),
                        ("spacer", 2.0),
                        ("ring", c.pin_n * c.pin_ring_d * c.pin_deep + 5.0)):
        area, lowest = unsupported_area(meshes[tag])
        require(area < budget,
                f"{tag}: {area:.1f} mm2 over air against a {budget:.0f} budget, "
                f"lowest at z={lowest:.2f}. 45 degree thread flanks should not "
                "count; something else is unsupported.")
        d[f"air_{tag}"] = area
    return d


CELL = JewelCell()

# Fit coupon. Every thread, wall and clearance dimension is IDENTICAL to CELL —
# those are absolute, not proportional, so shrinking them would test nothing.
# Only the diameter and the stack come down. The smaller diameter makes it a
# harder test, not an easier one: the lead angle triples, so the swept thread is
# more skewed than the real one.
TEST = JewelCell(disk_dia=30.0, pocket=31.5, body_od=39.0, ring_od=30.5,
                 spacer_h=5.0, jewel_min=0.0, jewel_pass=0.0, jewel_max=0.0)


if __name__ == "__main__":
    test = "test" in sys.argv[1:]
    c, prefix = (TEST, "jewel_test") if test else (CELL, "jewel")
    parts = {"body": build_body(c), "spacer": build_spacer(c), "ring": build_ring(c)}
    meshes, files = {}, {}
    for tag, part in parts.items():
        # Looser volume tolerance than the tube parts get. Those are almost all
        # planes; these are 75-84 mm cylinders, and faceting a circle that big
        # is worth about 1e-3 of the volume before anything is wrong.
        stl, step, mesh, tess = emit(part, f"{prefix}_{tag}", vol_tol=4e-3)
        meshes[tag], files[tag] = mesh, stl
    d = check(c, parts, meshes)

    print(f"{'FIT COUPON' if test else 'full cell'}")
    print(f"windows    cut them {c.disk_dia:.1f} mm; anything from "
          f"{c.disk_dia - 0.5:.1f} to {c.pocket - 0.3:.1f} will seat")
    if c.jewel_pass > 0:
        n = 0.5 * math.pi * (c.bore_dia / 2) ** 2 / 165.0
        print(f"jewels     ~{n:.0f} pieces at 15 mm covers half the chamber "
              f"({n * c.jewel_g:.0f} g); {12 * 1.36 / c.chamber_cc:.0%} of the volume at 12")
    print(f"body       {c.body_od:.1f} od x {c.body_h:.1f} tall, "
          f"{parts['body'].volume / 1000:.2f} cm3")
    print(f"           pocket {c.pocket:.1f} ({d['slack']:.2f} slack), ledge {c.ledge:.1f}, "
          f"aperture {c.aperture:.1f} clear")
    print(f"spacer     {d['sp_od']:.1f} od x {c.spacer_h:.1f} tall, bore {c.bore_dia:.1f}, "
          f"{parts['spacer'].volume / 1000:.2f} cm3")
    print(f"           bears on {d['sp_bear']:.1f} mm of window rim, seals "
          f"{d['seal']:.1f} mm wide")
    print(f"chamber    {c.bore_dia:.1f} dia x {c.spacer_h:.1f} deep = "
          f"{c.chamber_cc:.1f} cm3; aim to fill about a third")
    if c.jewel_pass > 0:
        print(f"           tumbles (+{d['tumble']:.1f} over the free-fall gap), cannot "
              f"stack (+{d['no_stack']:.1f}), cannot stand on end (+{d['no_stand']:.1f})")
    print(f"ring       {c.ring_od:.1f} od x {c.ring_h:.1f} tall, "
          f"{parts['ring'].volume / 1000:.2f} cm3, {d['turn_gap']:.2f} mm to turn")
    print(f"stack      floor {c.floor:.1f} + window + spacer + window = ring seats at "
          f"{c.seated:.2f}, top at {c.seated + c.ring_h:.2f}, standing "
          f"{d['proud']:+.2f} proud of the rim")
    print(f"thread     pitch {c.pitch:.1f}, {c.rib_turns:.1f} turns of rib in "
          f"{c.groove_turns:.1f} of groove, {d['engage']:.2f} mm deep")
    print(f"           breaks out {d['groove_out']:.2f} past the rim so the rib can start; "
          f"{(c.groove_turns - c.rib_turns) * c.pitch:.1f} mm of travel")
    print(f"           crest clear {d['crest']:.2f}, flank slack {d['flank']:.2f}, seated "
          f"rib {d['rib'][0]:.2f}..{d['rib'][1]:.2f} in {d['groove'][0]:.2f}.."
          f"{d['groove'][1]:.2f} ({d['thread_margin']:.2f} spare)")
    w = ", ".join(f"{x:.2f}" for x in c.pin_widths)
    print(f"pin        body slot(s) {w} mm wide x {c.slot_h:.1f} tall, at "
          + ", ".join(f"{i * 360 / len(c.pin_widths):.0f} deg" for i in range(len(c.pin_widths))))
    print(f"           slot absorbs +/-{d['slot_range'] / 2:.2f} mm; measured error on "
          f"coupon 2 was 0.30. Flutes count the rank: 1 = tightest.")
    print(f"           grips over {d['pin_wall']:.2f} mm of solid wall; ring holes "
          f"{c.pin_ring_d:.1f} x {c.pin_deep:.1f} deep, {c.pin_n} at "
          f"{360 / c.pin_n:.0f} deg, z {c.ring_pin_z:.2f}")
    print(f"           hole is {d['hole_deep']:.1f} mm deep — cut the pin "
          f"{d['pin_len']:.1f} mm, leaving 1.0 to drive it under the surface")
    print(f"mesh       " + ", ".join(
        f"{t} {len(meshes[t].faces)}f/{d['air_' + t]:.1f}mm2" for t in parts))
    print(f"wrote      " + ", ".join(files.values()))
