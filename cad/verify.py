"""Checks a part must pass before it is allowed near the printer.

These encode the defects that actually reached the printer during the
FeatureScript phase, when nothing could be executed before Pace ran it:

  * the small cap sat at z = -2 while the plate sat at z = 0, so the slicer
    bedded the cap and left the plate floating in mid-air;
  * the collar's ear spanned z 1..11 against a body starting at 0, so 11 mm
    of it printed over nothing;
  * the large cap's ear landed exactly on top of the collar's.

The first two are bounding-box and downward-face checks. The third is a
clearance check, which lives in the part module because only it knows what
it has to clear.
"""

from __future__ import annotations

import math
import os

import trimesh
from build123d import export_step, export_stl


class CheckFailed(Exception):
    pass


def _fail(msg: str):
    raise CheckFailed(msg)


def sits_on_bed(part, tol: float = 1e-3):
    """Lowest geometry must be exactly on z = 0.

    A part whose minimum is below zero drags everything else up off the bed
    when several are in one file; one whose minimum is above zero prints its
    first layer in the air.
    """
    bb = part.bounding_box()
    if abs(bb.min.Z) > tol:
        _fail(f"lowest geometry at z={bb.min.Z:+.4f}, not 0 — "
              "the slicer will bed that and float anything modelled above it")
    return bb


def unsupported_area(mesh, above: float = 0.15, angle_deg: float = 55.0):
    """Total downward-facing area that is not sitting on the build plate.

    A face's overhang angle is measured from vertical: a wall is 0 deg, a
    ceiling is 90. Anything past `angle_deg` and clear of the bed is being
    printed over air. Small amounts are fine — a short bridge is normal — so
    this reports rather than judges, and the caller sets the limit.
    """
    nz = mesh.face_normals[:, 2]
    zc = mesh.triangles_center[:, 2]
    steep = (nz < 0) & (np_arcsin_deg(-nz) > angle_deg) & (zc > above)
    area = float(mesh.area_faces[steep].sum())
    lowest = float(zc[steep].min()) if steep.any() else float("nan")
    return area, lowest


def np_arcsin_deg(x):
    import numpy as np

    return np.degrees(np.arcsin(np.clip(x, -1.0, 1.0)))


def emit(part, name: str, outdir: str = "out", vol_tol: float = 1e-3):
    """Write STL and STEP, then read the mesh back and prove it is printable."""
    os.makedirs(outdir, exist_ok=True)
    stl = os.path.join(outdir, f"{name}.stl")
    step = os.path.join(outdir, f"{name}.step")
    export_stl(part, stl)
    export_step(part, step)

    mesh = trimesh.load_mesh(stl)
    if not mesh.is_watertight:
        _fail(f"{stl} is not watertight — the slicer will guess at the holes")
    if not mesh.is_winding_consistent:
        _fail(f"{stl} has inconsistent winding")
    if mesh.volume <= 0:
        _fail(f"{stl} encloses non-positive volume — normals are inverted")

    # Two floors on how close this can get: binary STL is float32 (~1e-7
    # relative), and any curved face is chorded, which for a part with rounded
    # corners dominates at ~1e-5. So this is a backstop against gross errors —
    # a dropped face, inverted normals — not a precision check. Pass a tighter
    # vol_tol for an all-planar part, where it can be held to 1e-5.
    err = abs(mesh.volume - part.volume) / part.volume
    if err > vol_tol:
        _fail(f"{stl} volume {mesh.volume:.4f} disagrees with the solid "
              f"{part.volume:.4f} by {err:.1e}")
    return stl, step, mesh, err


def require(condition: bool, msg: str):
    if not condition:
        _fail(msg)
