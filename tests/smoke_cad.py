#!/usr/bin/env python3
"""Smoke test for the CAD toolchain in the aisand sandbox.

Run inside the sandbox:  aisand sh -c 'python3 tests/smoke_cad.py'

Checks, in order of how confusing the failure is otherwise:

1. Every shared library OpenCascade links against actually resolves. OCP links
   X11/GL unconditionally even though nothing here renders, so a missing
   libGL surfaces as an opaque ImportError rather than a linker message.
2. build123d can build a solid, fillet it, and report its volume -- checked
   against the closed-form answer, not just printed.
3. Loft between two polygons is a straight ruled loft between corresponding
   vertices. Every kaleidoscope part is that one operation, and the whole
   design assumes its faces come out planar, so this is the load-bearing
   check rather than a nicety.
4. Exported STL is watertight, consistently wound, and encloses the same
   volume as the solid it came from. This is the class of defect that a
   slicer catches after you have wasted a print. Note that binary STL is
   single precision, so even an all-planar solid only round-trips to about
   1e-7 relative -- do not tighten STL_TOL past that.
5. STEP and STL export both write files.
"""

import glob
import math
import os
import subprocess
import sys
import tempfile

TOL = 1e-9          # volumes, which come from exact integration
BBOX_TOL = 1e-3     # OCC inflates bounding boxes by the shape tolerance
STL_TOL = 1e-5      # binary STL is float32, so ~1e-7 relative is the floor
MESH_TOL = 5e-3     # tessellation of curved faces, so looser


def check_libraries():
    import OCP

    so = sorted(glob.glob(os.path.join(os.path.dirname(OCP.__file__), "*.so")))
    if not so:
        sys.exit("no OCP .so files found -- is cadquery-ocp installed?")
    missing = set()
    for lib in so:
        out = subprocess.run(["ldd", lib], capture_output=True, text=True).stdout
        missing.update(
            line.split("=>")[0].strip()
            for line in out.splitlines()
            if "not found" in line
        )
    if missing:
        sys.exit("unresolved libraries: " + " ".join(sorted(missing)))
    print(f"libraries: all resolved across {len(so)} OCP .so files")


def check_modelling(tmp):
    from build123d import Axis, Box, Cylinder, export_step, export_stl, fillet

    part = Box(20, 20, 10) - Cylinder(radius=4, height=20)
    part = fillet(part.edges().filter_by(Axis.Z), 2)

    # box, less the bore, less four 90-degree corner fillets over the height
    want = 20 * 20 * 10 - math.pi * 4**2 * 10 - 4 * 10 * (4 - math.pi)
    if abs(part.volume - want) / want > TOL:
        sys.exit(f"volume {part.volume:.6f} != closed form {want:.6f}")

    step, stl = os.path.join(tmp, "t.step"), os.path.join(tmp, "t.stl")
    export_step(part, step)
    export_stl(part, stl)
    for path in (step, stl):
        if not os.path.getsize(path):
            sys.exit(f"{path} is empty")

    size = part.bounding_box().size
    print(f"modelling: volume {part.volume:.4f} matches closed form")
    print(f"           bbox {size.X:g} x {size.Y:g} x {size.Z:g}")
    print(f"           export {os.path.getsize(step)} B step, {os.path.getsize(stl)} B stl")
    return stl


def _plate_profile(side, t=1.5875, w=3.0, land=0.6):
    """One kaleidoscope side plate's cross-section: mitred both long edges,
    outer tips truncated so they are printable."""
    s3 = math.sqrt(3)
    rp = side / (2 * s3) + t
    ro = rp + w
    xi, xo = s3 * rp, s3 * (ro - land)
    return [(-xi, -rp), (xi, -rp), (xo, -ro + land),
            (xo, -ro), (-xo, -ro), (-xo, -ro + land)]


def _shoelace(pts):
    n = len(pts)
    return abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                   for i in range(n))) / 2


def check_loft(tmp):
    from build123d import Plane, Polygon, export_stl, loft

    length = 100.0
    a, b = _plate_profile(25.4), _plate_profile(50.8)

    # A ruled loft interpolates corresponding vertices linearly, so the section
    # area is quadratic in z and Simpson integrates it exactly. If build123d
    # disagreed, its faces would not be the planes the design relies on.
    def area_at(f):
        return _shoelace([(a[i][0] + (b[i][0] - a[i][0]) * f,
                           a[i][1] + (b[i][1] - a[i][1]) * f) for i in range(len(a))])

    want = length / 6 * (area_at(0) + 4 * area_at(0.5) + area_at(1))

    part = loft([Plane.XY * Polygon(*a, align=None),
                 Plane.XY.offset(length) * Polygon(*b, align=None)])
    if abs(part.volume - want) / want > TOL:
        sys.exit(f"loft volume {part.volume:.6f} != ruled-loft {want:.6f} "
                 "-- loft is not interpolating vertices linearly")

    bb = part.bounding_box()
    if abs(bb.size.Z - length) > BBOX_TOL:
        sys.exit(f"loft length {bb.size.Z} != {length}")

    stl = os.path.join(tmp, "plate.stl")
    export_stl(part, stl)
    print(f"loft:      volume {part.volume:.4f} matches the ruled-loft integral")
    print(f"           bbox {bb.size.X:.3f} x {bb.size.Y:.3f} x {bb.size.Z:.3f}")
    return part.volume, stl


def check_mesh(curved_stl, planar_stl, planar_volume):
    try:
        import trimesh
    except ImportError:
        sys.exit("trimesh missing -- needed to verify exported meshes")

    for path, want, tol, what in ((planar_stl, planar_volume, STL_TOL, "planar"),
                                  (curved_stl, None, MESH_TOL, "curved")):
        m = trimesh.load_mesh(path)
        if not m.is_watertight:
            sys.exit(f"{what} mesh {path} is not watertight")
        if not m.is_winding_consistent:
            sys.exit(f"{what} mesh {path} has inconsistent winding")
        if m.volume <= 0:
            sys.exit(f"{what} mesh {path} has non-positive volume -- normals inverted")
        if want is not None and abs(m.volume - want) / want > tol:
            sys.exit(f"{what} mesh volume {m.volume:.6f} != solid {want:.6f}")
        print(f"mesh:      {what} {len(m.faces)} faces, watertight, "
              f"volume {m.volume:.4f}")


if __name__ == "__main__":
    tmp = tempfile.mkdtemp()
    check_libraries()
    curved_stl = check_modelling(tmp)
    planar_volume, planar_stl = check_loft(tmp)
    check_mesh(curved_stl, planar_stl, planar_volume)
    print("OK")
