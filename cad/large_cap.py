#!/usr/bin/env python3
"""Wide-end cap for the short scope, with one snap ear onto the collar.

Run:  python3 cad/large_cap.py

Two jobs. It closes the wide end with a lip that overhangs the mirrors' end
faces, so they cannot slide out — the taper means the wide end is the only
direction they can go. And it carries three sprung ears, one down each flat, over
the collar, hooking onto the collar's narrow end face to hold the cap on. Three
rather than one: the pull is balanced instead of cocking the cap to one side,
and the scope still holds together if an ear snaps off.

IT IS BUILT AROUND THE MEASURED COLLAR POSITION, NOT THE DESIGNED ONE.

A wedging collar stops where it stops. This one was designed to seat with its
far edge 10.0 mm from the wide opening and measured 10.70, so it is 0.70 mm
short of nominal and every feature of the ear is referenced to the measurement.
The prototype's large cap missed its slot by 1.0 mm for exactly this reason.
Re-measure and re-run if the collar is ever reseated.

ASSEMBLY ORDER MATTERS, AND IT IS THE OPPOSITE OF WHAT YOU WOULD GUESS

Put this cap on BEFORE driving the collar home. The collar's outside is tapered,
so an ear sliding down over it from the wide end has to climb the whole taper —
2.17 mm of deflection. Coming the other way, the collar's narrow rim meets the
hook's ramp at the very end of its travel and only opens it by the engagement
depth, 1.00 mm. Same joint, less than half the strain. Both are within PLA, and
the script prints both numbers, but there is no reason to use the hard one.

THE BORE IS STRAIGHT, AND IT HAS TO BE

The first version cut the skirt's bore to the tube's taper, the way the small
cap and the collar are cut, and it would not go on — 0.55 mm of interference on
the flats, 0.89 at the corners. Those two parts enter from the NARROW end, so
their mouth is sized for the widest station they cover and everything they slide
over is smaller. This one enters from the WIDE end, which inverts the argument:
its mouth is sized for the narrowest station it covers, and the first thing that
mouth meets is the tube at its very widest. No skirt length rescues it.

So the bore is a constant r_outer(length) + clearance. The cost is that it can
only be tight at the tube's end face, and opens up by taper * skirt by the time
it reaches the mouth. That gap is the price of entering from this end; the only
lever on it is skirt length, and `skirt` is the one number to change.

WIND THE PROFILES THE SAME WAY

build123d extrudes along the FACE normal, and the face normal follows the
polygon's winding, not the plane's. The gusset was wound clockwise and the arm
counterclockwise, so `amount=+arm_w` sent them opposite ways: arm at X -5..+5,
gusset at X -15..-5, touching on a coincident face and nothing else. Both go
through _fin(), which normalises the winding, and build() asserts that the two
end up on the same span of X.

PRINTS APERTURE-DOWN, and the hook geometry follows from that: the catch face
looks back at the bed and is a short overhang, the ramp faces up and prints as
a plain slope. The ear is deliberately NOT fused to the skirt above its root
gusset — fusing it would cut the free length from 29 mm to 17 and triple the
bending strain.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build123d import Plane, Polygon, RegularPolygon, Rot, extrude, fillet, loft

from scope import Scope, rounded_tri_reach
from shapes import fin as _fin, rtri as _rtri
from collar import Collar
from proto_set import PROTO, COLLAR_SEAT
from verify import emit, require, sits_on_bed, unsupported_area

# Measured on the assembled tube: wide edge of a side plate to the near edge of
# the collar. Design was 10.0, so the collar wedged 0.70 mm short.
COLLAR_GAP = 10.70

E_PLA = 3500.0        # MPa, for turning bending strain into a stress to judge
ARMS = 3              # one per flat


@dataclass(frozen=True)
class LargeCap:
    rim: float = 3.0           # flange thickness standing past the tube end
    skirt: float = 8.0         # sets the gap at the mouth: taper * skirt. Also
    #                            must stay clear of the collar, see COLLAR_GAP
    wall: float = 2.5
    clearance: float = 0.15
    bore_corner: float = 0.7
    ap_corner: float = 0.3
    lip: float = 0.6           # over the mirrors' end faces. Generous compared
    #                            with the small cap's 0.294 because this end is
    #                            the frame of the picture rather than a triangle
    #                            drawn in the middle of it
    arm_w: float = 10.0
    arm_t: float = 1.8         # bending dimension; see the strain check
    arm_gap: float = 0.8       # air gap to the skirt, so the ear stays free
    root_h: float = 4.0        # gusset height; this much of the ear is stiff
    root_bury: float = 2.0     # how far the gusset reaches INTO the cap body
    engage: float = 1.0        # radial bite on the collar's end face
    hook_slack: float = 0.4    # catch sits this far PAST the collar's face, so
    #                            the cap always seats even if the collar creeps
    hook_flat: float = 1.0
    ramp: float = 2.5


class Layout:
    """Every station the cap cares about, in cap coordinates.

    z_cap runs from 0 at the outermost face (which is the bed) inward toward the
    narrow end. The tube's wide end face sits at z_cap = rim.
    """

    def __init__(self, scope: Scope, cap: LargeCap, collar: Collar, gap: float):
        self.scope, self.cap, self.collar = scope, cap, collar
        self.far = scope.length - gap                  # collar's wide edge
        self.near = self.far - collar.length           # collar's narrow face
        self.slip = collar.seat - self.near            # how short it wedged
        self.top = cap.rim + cap.skirt

        self.catch = self.to_cap(self.near) + cap.hook_slack
        self.arm_top = self.catch + cap.hook_flat + cap.ramp
        self.hook_r = self.collar_outer(self.near) - cap.engage

    # ---- frames -----------------------------------------------------------

    def to_cap(self, z_tube: float) -> float:
        return self.scope.length + self.cap.rim - z_tube

    def to_tube(self, z_cap: float) -> float:
        return self.scope.length + self.cap.rim - z_cap

    # ---- surfaces ---------------------------------------------------------

    def shell(self, z_cap: float) -> float:
        """Outside of the cap."""
        return (self.scope.r_outer(self.to_tube(z_cap))
                + self.cap.clearance + self.cap.wall)

    def bore(self, z_cap: float) -> float:
        """Straight, not tapered. Sized to pass the tube's widest station,
        because that is the first thing it meets. See the module docstring."""
        return self.scope.r_outer(self.scope.length) + self.cap.clearance

    def collar_outer(self, z_tube: float) -> float:
        """The collar's outside where it ACTUALLY sits, slip included."""
        return (self.scope.r_outer(z_tube + self.slip) + self.collar.wall)

    def arm_inner(self, z_cap: float) -> float:
        """Inner face of the ear. Parallel to the collar's outside, standing off
        far enough to clear the cap's own skirt, which is the fatter of the
        two."""
        return self.collar_outer(self.to_tube(z_cap)) + self.cap.arm_gap


def build(scope: Scope, cap: LargeCap, lay: Layout):
    part = loft([_rtri(lay.shell(0.0), cap.bore_corner + cap.wall, 0.0),
                 _rtri(lay.shell(lay.top), cap.bore_corner + cap.wall, lay.top)])

    # Bore, from the tube's end face up. Overshoot the top so the cut is clean.
    part -= loft([_rtri(lay.bore(cap.rim), cap.bore_corner, cap.rim),
                  _rtri(lay.bore(lay.top + 1.0), cap.bore_corner, lay.top + 1.0)])

    # Aperture through the flange.
    ap = scope.r_face(scope.length) - cap.lip
    part -= extrude(_rtri(ap, cap.ap_corner, -1.0), amount=cap.rim + 2.0)

    ear = _ear(cap, lay)
    return part + ear + Rot(0, 0, 120) * ear + Rot(0, 0, 240) * ear


def _ear(cap: LargeCap, lay: Layout):
    """One sprung arm with its root gusset, on the -Y flat.

    Sketched in the YZ plane like the small cap's bumps: local x is global Y,
    and radially outward is -Y on this face.
    """
    a0, a1 = lay.arm_inner(0.0), lay.arm_inner(lay.arm_top)
    pts = [(-a0, 0.0),
           (-lay.arm_inner(lay.catch), lay.catch),
           (-lay.hook_r, lay.catch),                       # the catch face
           (-lay.hook_r, lay.catch + cap.hook_flat),
           (-a1, lay.arm_top),                             # ramp back out
           (-a1 - cap.arm_t, lay.arm_top),
           (-a0 - cap.arm_t, 0.0)]
    arm = _fin(pts, cap.arm_w)

    # Root gusset: a plain wedge filling the air gap from the bed up to root_h,
    # buried root_bury into the cap body and running the arm's full thickness.
    # The old one reached 0.5 mm into the cap and 0.3 mm into the arm.
    gus = [(-(lay.shell(0.0) - cap.root_bury), 0.0),
           (-a0 - cap.arm_t, 0.0),
           (-lay.arm_inner(cap.root_h) - cap.arm_t, cap.root_h),
           (-lay.shell(cap.root_h), cap.root_h)]
    gusset = _fin(gus, cap.arm_w)

    ab, gb = arm.bounding_box(), gusset.bounding_box()
    require(abs(ab.min.X - gb.min.X) < 1e-6 and abs(ab.max.X - gb.max.X) < 1e-6,
            f"gusset spans X {gb.min.X:.2f}..{gb.max.X:.2f} but the arm spans "
            f"{ab.min.X:.2f}..{ab.max.X:.2f} — one of them extruded the wrong way")

    return arm + gusset


def strain(delta: float, t: float, L: float) -> float:
    """Peak surface strain at the root of a tip-loaded cantilever."""
    return 3 * delta * t / (2 * L * L)


def check(scope: Scope, cap: LargeCap, lay: Layout, part, mesh) -> dict:
    f = {}
    bb = sits_on_bed(part)
    f["height"], f["across"] = bb.max.Z, bb.max.X - bb.min.X
    f["deep"] = bb.max.Y - bb.min.Y

    require(cap.skirt < COLLAR_GAP - 0.5,
            f"skirt {cap.skirt:.1f} mm runs into the collar, which is only "
            f"{COLLAR_GAP:.2f} mm away — the cap would stop before its lip "
            "reached the mirrors")
    f["skirt_gap"] = COLLAR_GAP - cap.skirt

    # The lip has to overhang the mirror's end face without eating the view.
    lip_lands = scope.mirror - cap.lip
    require(0.0 < cap.lip < scope.mirror,
            f"lip {cap.lip:.2f} mm does not land on the {scope.mirror:.2f} mm "
            "mirror edge")
    f["lip_lands"] = lip_lands
    f["corner_bite"] = 2 * cap.lip + cap.ap_corner
    f["ap_across"] = 2 * math.sqrt(3) * (scope.r_face(scope.length) - cap.lip)

    # THE CHECK THAT WAS MISSING. Sliding on from the wide end, every part of
    # the bore passes over the tube's widest station, so the whole bore — not
    # just the part that ends up there — has to clear it.
    widest = scope.r_outer(scope.length)
    for z_cap, tag in ((cap.rim, "face"), (lay.top, "mouth")):
        flat = lay.bore(z_cap) - widest
        require(flat > 0.05,
                f"bore is {flat:+.3f} mm on the flats against the tube's widest "
                f"station at the {tag} — the cap will not go on. A tapered bore "
                "cannot be entered from the wide end.")
        corner = (rounded_tri_reach(lay.bore(z_cap), cap.bore_corner)
                  - scope.corner_reach(scope.length))
        require(corner > 0.3, f"bore corner clearance {corner:+.2f} mm against the "
                              f"widest station at the {tag}")
        f[f"entry_{tag}"], f[f"corner_{tag}"] = flat, corner

    # What the straight bore costs: it can only be tight at the end face.
    f["mouth_gap"] = lay.bore(lay.top) - scope.r_outer(lay.to_tube(lay.top))
    f["min_wall"] = min(lay.shell(z) - lay.bore(z)
                        for z in (cap.rim, lay.top))
    require(f["min_wall"] > 1.2, f"skirt wall down to {f['min_wall']:.2f} mm")

    # Hook: it must bite the collar's end face and nothing else.
    band = lay.collar_outer(lay.near) - scope.r_outer(lay.near + lay.slip)
    require(cap.engage < band - 0.5,
            f"hook bites {cap.engage:.2f} mm of a {band:.2f} mm end face")
    require(lay.hook_r > scope.r_outer(lay.to_tube(lay.arm_top)) + 0.5,
            "the hook would foul the tube itself past the collar")
    f["band"], f["hook_depth"] = band, lay.arm_inner(lay.catch) - lay.hook_r
    f["tube_clear"] = lay.hook_r - scope.r_outer(lay.to_tube(lay.arm_top))

    # Ear stiffness. Free length starts at the top of the gusset.
    L = lay.arm_top - cap.root_h
    d_collar_last = cap.engage
    d_cap_last = lay.collar_outer(lay.far) - lay.hook_r
    f["free_len"] = L
    for tag, d in (("collar_last", d_collar_last), ("cap_last", d_cap_last)):
        e = strain(d, cap.arm_t, L)
        require(e < 0.010, f"{tag}: {e * 100:.2f}% bending strain would crack PLA")
        f[f"defl_{tag}"], f[f"strain_{tag}"] = d, e
    f["stress_worst"] = E_PLA * strain(d_cap_last, cap.arm_t, L)

    # What it takes to drive the collar in under all three hooks. Tip-loaded
    # cantilever, then the ramp turning radial force into axial. Friction is not
    # in here, so read it as a floor rather than a prediction.
    I = cap.arm_w * cap.arm_t ** 3 / 12.0
    radial = 3 * E_PLA * I * cap.engage / L ** 3
    rise = lay.arm_inner(lay.arm_top) - lay.hook_r
    ramp_deg = math.degrees(math.atan2(rise, cap.ramp))
    f["ramp_deg"] = ramp_deg
    f["push_n"] = ARMS * radial / math.tan(math.radians(ramp_deg))
    f["push_kgf"] = f["push_n"] / 9.81

    # The ear must not touch the skirt, or it stops being a spring.
    clear = min(lay.arm_inner(z) - lay.shell(z)
                for z in (cap.root_h, lay.top / 2, lay.top))
    require(clear > 0.3, f"only {clear:.2f} mm between the ear and the skirt")
    f["ear_clear"] = clear

    area, lowest = unsupported_area(mesh)
    ledge = ARMS * f["hook_depth"] * cap.arm_w
    require(area < ledge + 6.0,
            f"{area:.1f} mm2 over air against {ARMS} hook catches totalling "
            f"{ledge:.1f} mm2, "
            f"lowest at z={lowest:.2f} — something else is unsupported")
    f["unsupported"], f["ledge"] = area, ledge
    return f


if __name__ == "__main__":
    scope, cap = PROTO, LargeCap()
    collar = Collar(seat=COLLAR_SEAT)
    lay = Layout(scope, cap, collar, COLLAR_GAP)

    part = build(scope, cap, lay)
    stl, step, mesh, tess = emit(part, "proto_large_cap")
    f = check(scope, cap, lay, part, mesh)

    print(f"scope      {scope.summary()}")
    print(f"collar     measured {COLLAR_GAP:.2f} mm from the wide edge -> sits at "
          f"tube z {lay.near:.2f}-{lay.far:.2f}, {lay.slip:+.2f} mm off design")
    print(f"cap        {f['across']:.1f} x {f['deep']:.1f} mm, {f['height']:.1f} mm tall, "
          f"{part.volume / 1000:.2f} cm3")
    print(f"           skirt {cap.skirt:.1f} mm, stopping {f['skirt_gap']:.2f} mm "
          f"short of the collar")
    print(f"aperture   {f['ap_across']:.2f} mm across vs a {2 * math.sqrt(3) * scope.r_face(scope.length):.2f} mm "
          f"optical face")
    print(f"           lip {cap.lip:.2f} mm over the mirror, {f['lip_lands']:.2f} mm "
          f"of edge left uncovered, {f['corner_bite']:.2f} mm bite at the corners")
    print(f"bore       straight at {lay.bore(0.0):.2f} mm inradius, clearing the tube's "
          f"widest station by {f['entry_face']:.2f} mm on the flats")
    print(f"           corners clear by {f['corner_face']:.2f} mm; gap opens to "
          f"{f['mouth_gap']:.2f} mm at the mouth, wall down to {f['min_wall']:.2f} mm")
    print(f"ear        {ARMS} of them, one per flat, {cap.arm_w:.0f} x {cap.arm_t:.1f} mm, free length "
          f"{f['free_len']:.1f} mm, {f['ear_clear']:.2f} mm off the skirt")
    print(f"           hook {f['hook_depth']:.2f} mm deep, biting {cap.engage:.2f} of the "
          f"collar's {f['band']:.2f} mm end face, {f['tube_clear']:.2f} mm off the tube")
    print(f"           catch at cap z {lay.catch:.2f}, {cap.hook_slack:.2f} mm of slack")
    print(f"           {ARMS} ramps at {f['ramp_deg']:.0f} deg -> {f['push_n']:.1f} N "
          f"({f['push_kgf']:.2f} kgf) to drive the collar under them, friction aside")
    print(f"flex       collar last: {f['defl_collar_last']:.2f} mm, "
          f"{f['strain_collar_last'] * 100:.2f}% strain   <-- do it this way")
    print(f"           cap last:    {f['defl_cap_last']:.2f} mm, "
          f"{f['strain_cap_last'] * 100:.2f}% strain, ~{f['stress_worst']:.0f} MPa")
    print(f"mesh       {len(mesh.faces)} faces, watertight, {f['unsupported']:.1f} mm2 "
          f"over air vs {f['ledge']:.1f} mm2 of hook catch, tessellation {tess:.1e}")
    print(f"wrote      {stl}, {step}")
