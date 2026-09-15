"""Sketch primitives shared by the printed parts.

Both of these were copy-pasted between modules before, which is how the large
cap's gusset came to be extruded a whole arm-width away from its own arm.

WINDING CONTROLS EXTRUSION DIRECTION

build123d extrudes along the FACE normal, and the face normal follows the
polygon's winding — not the plane's orientation. Two profiles sketched on the
same plane, given the same positive `amount`, come out on opposite sides if
they are wound opposite ways. Nothing about the code looks wrong when this
happens; the parts simply end up somewhere else. `fin()` normalises the winding
so a caller cannot trip over it.
"""

from __future__ import annotations

import math

from build123d import Box, Plane, Polygon, Pos, RegularPolygon, extrude, fillet


def rtri(inradius: float, corner: float, z: float):
    """A rounded equilateral triangle on the plane z, clocked with vertices at
    90/210/330 to match the tube.

    Remember that rounding pulls the corners IN — see scope.rounded_tri_reach.
    """
    sk = RegularPolygon(radius=2 * inradius, side_count=3,
                        major_radius=True, rotation=90)
    return Plane.XY.offset(z) * fillet(sk.vertices(), corner)


def signed_area(pts) -> float:
    n = len(pts)
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                     for i in range(n))


def fin(pts, width: float):
    """Extrude a profile sketched in the YZ plane into a fin centred on X.

    Local x is global Y and local y is the tube axis, so on the -Y face
    radially outward is -x. The winding is normalised first; see the module
    docstring for why that is not optional.
    """
    if signed_area(pts) < 0:
        pts = list(reversed(pts))
    return extrude(Plane.YZ.offset(-width / 2) * Polygon(*pts, align=None),
                   amount=width)


def tab_offsets(shell_r: float, from_vertex: float):
    """Where a pair of band notches sits along one flat, from its centre."""
    half = math.sqrt(3) * shell_r          # half a side of the triangle
    return (-(half - from_vertex), half - from_vertex)


def straight_run(shell_r: float, corner_r: float) -> float:
    """How far along a flat, from its centre, the wall is still straight.

    A fillet of radius rho at a 60 degree corner eats sqrt(3)*rho of each side.
    """
    return math.sqrt(3) * (shell_r - corner_r)


def band_tab(shell_r: float, xoff: float, w: float, out: float, col: float,
             notch_z: float, thick: float, bury: float):
    """A shelf held off the wall by an outer column, leaving a notch a rubber
    band drops into. On the -Y flat, like the other fins.

    Both caps use it the same way round without mirroring, because each cap's
    local z runs from 0 at its OUTERMOST face inward. The shelf therefore always
    ends up on the inboard side of its notch, and a band pulling toward the far
    cap bears on the shelf's underside and drags this cap onto the tube.

    `bury` buys notch depth for free: it eats into the wall rather than standing
    further out, which matters on the small cap, where the collar has to slide
    over the whole thing on its way to its seat.
    """
    inner, outer = -(shell_r - bury), -(shell_r + out)
    col_in = -(shell_r + out - col)
    shelf = Pos(xoff, (inner + outer) / 2, notch_z + thick / 2) * Box(
        w, abs(outer - inner), thick)
    column = Pos(xoff, (col_in + outer) / 2, notch_z / 2) * Box(
        w, abs(outer - col_in), notch_z)
    return shelf + column
