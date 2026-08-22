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

from build123d import Plane, Polygon, RegularPolygon, extrude, fillet


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
