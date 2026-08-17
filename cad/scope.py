"""Geometry shared by every part of the tapered kaleidoscope.

One Scope instance is the single source of truth for the tube. Each part
module derives its own dimensions from it, so changing the length or the
apertures cannot leave two parts quietly disagreeing — which is how the large
end cap ended up with its ears on top of the collar's.

Current target: 255 mm. The longest that fits a 250x210 MK3 bed at all is
263.8 mm, but that lands exactly on 210.0 with nothing spare; 255 costs 5%
of the facets and buys real margin. Apertures unchanged at 1 in and 2 in,
so the image gets finer rather than bigger.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

S3 = math.sqrt(3)


def rounded_tri_area(inradius: float, corner: float) -> float:
    """Area of an equilateral triangle of this inradius with rounded corners —
    the Minkowski sum of a smaller triangle and a disc."""
    rho = inradius - corner
    return 3 * S3 * rho**2 + 6 * S3 * rho * corner + math.pi * corner**2


def rounded_tri_reach(inradius: float, corner: float) -> float:
    """How far the corner reaches from the axis.

    Rounding pulls it IN, which is the trap that cost a printed end cap:
    a rounded bore has *less* corner clearance than a sharp one, not more.
    """
    return 2 * inradius - corner


@dataclass(frozen=True)
class Scope:
    narrow_face: float = 25.4      # optical face at the narrow end
    wide_face: float = 50.8        # optical face at the wide end
    length: float = 255.0          # along the axis; 263 fits the bed with
    #                                literally zero margin, this leaves ~6 mm
    mirror: float = 1.5875         # 1/16 in stock
    plate: float = 3.0             # side plate thickness
    miter_land: float = 0.6        # truncation of the plates' outer mitre tips
    mirror_overlap: float = 1.0    # blanks cut oversize; the surplus buries
    #                                itself behind the neighbouring mirror

    # ---- the tube, station by station -------------------------------------

    @property
    def taper(self) -> float:
        """d(inradius)/dz. Every taper in the scope is this one number."""
        return (self.wide_face - self.narrow_face) / (2 * S3 * self.length)

    def r_face(self, z: float) -> float:
        """Optical inradius — the mirrors' front faces."""
        return self.narrow_face / (2 * S3) + self.taper * z

    def r_seat(self, z: float) -> float:
        """Plate inner face. The mirror rests straight on it, so this is one
        mirror thickness outboard of the optical plane."""
        return self.r_face(z) + self.mirror

    def r_outer(self, z: float) -> float:
        """Outside of the assembled tube, on the flats."""
        return self.r_seat(z) + self.plate

    def corner_reach(self, z: float) -> float:
        """How far the tube's material actually reaches at a corner.

        A plate's outer face stops sqrt(3)*miter_land short of the sharp
        vertex, which pulls the corner in by 1.5*miter_land. Anything sliding
        over the tube has to clear this, not the sharp vertex.
        """
        return 2 * self.r_outer(z) - 1.5 * self.miter_land

    # ---- the mirror blanks -------------------------------------------------

    def blank_width(self, z: float) -> float:
        """Cut width at station z: the optical face plus the overlap."""
        return 2 * S3 * self.r_face(z) + self.mirror_overlap

    @property
    def blank_height(self) -> float:
        """Between the parallel edges, measured in the mirror's own plane."""
        return self.length / math.cos(math.atan(self.taper))

    @property
    def blank_leg(self) -> float:
        """The slanted sides. One of these is cut on a factory edge."""
        return math.hypot(self.blank_height, (self.wide_face - self.narrow_face) / 2)

    @property
    def overlap_limit(self) -> float:
        """Past this the surplus fouls the neighbouring plate instead of
        burying itself in the void behind the mirror ahead of it."""
        return 1.155 * self.mirror

    # ---- what you see through it ------------------------------------------

    @property
    def dihedral_deg(self) -> float:
        k = self.taper
        return 180 - math.degrees(math.acos((k * k - 0.5) / (1 + k * k)))

    @property
    def facets(self) -> float:
        return 4 * math.pi / math.radians(3 * (self.dihedral_deg - 60))

    @property
    def apex_to_narrow(self) -> float:
        return self.r_face(0) / self.taper

    @property
    def sphere_deg(self) -> float:
        """Angular diameter of the image sphere, seen from the wide end."""
        d1 = self.apex_to_narrow
        return 2 * math.degrees(math.asin(d1 / (d1 + self.length)))

    def summary(self) -> str:
        return (f"{self.length:.0f} mm, {self.narrow_face:.2f} -> {self.wide_face:.2f} mm "
                f"faces, dihedral {self.dihedral_deg:.4f} deg, "
                f"{self.facets:.0f} facets, sphere {self.sphere_deg:.1f} deg wide")
