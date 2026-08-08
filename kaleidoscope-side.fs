FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

/* ─────────────────────────────────────────────────────────────────────────
   Tapered three-mirror kaleidoscope — one side rail.  PROTOTYPE SIZE.

   Three identical copies of this part form a truncated triangular pyramid,
   equilateral in cross-section, each carrying one flat trapezoidal mirror
   bonded to its inner face.  They lap together at the corners with a
   full-length tongue and groove.

   Prototype geometry (the defaults below):
       mirror-face triangle   25.40 mm  ->  50.80 mm  (1" -> 2")
       length along axis      100 mm
       taper half-angle       4.1936°
       corner dihedral        60.529286°   (excess over 60° = 0.5293°)
       apex                   100 mm behind the narrow end, ratio d2/d1 = 2
       image                  a sphere subtending 60°, ~453 facets

   Mirror flat pattern, per side:
       trapezoid, parallel edges 25.40 and 50.80 mm,
       height 100.27 mm, legs 101.07 mm.  About 17.8 sq in for a set of three.

   WHY THE CORNERS ARE LOFTED AND NOT EXTRUDED
   The dihedral is 60.53°, not 60°.  That excess is the entire optical effect:
   at exactly 60° the images tile a flat plane and there is no sphere at all.
   Lofting between the two end triangles puts every mirror plane through the
   common apex automatically, so the excess falls out of the geometry.  Do not
   "simplify" this into an extrude of a 60° profile.

   WHY THE SPLIT PLANE IS DERIVED AND NOT SET DIRECTLY
   At each corner the pocket floor overruns its own mirror's edge by
   sqrt(3) * pocketDepth, and that band is exactly where the NEIGHBOURING
   mirror's body and bond layer land.  The corner split has to fall inside
   that band; outside it, a mirror is cantilevered off the end of its own
   floor.  `lap` is therefore computed from the mirror thickness, and
   `edgeMargin` is how far inside the band to stay.

   WHERE THE MIRROR SITS ON THE FLOOR
   The pocket floor is wider than the mirror, and asymmetrically so.  On the
   split-plane side the floor runs past the mirror edge by exactly
   `edgeMargin`; on the corner-block side it runs past by sqrt(3) * pocket.
   So the assembly rule is: set the mirror edge `edgeMargin` (1 mm by default)
   in from the flat split face.  Set edgeMargin near zero and the mirror edge
   becomes flush with that face, which is self-registering but leaves no
   support margin for error.

   PRINT ORIENTATION
   The part is transformed at the end so the outside face lies on the XY plane.
   That gives a smooth exterior off the bed and needs no support, but it makes
   the mirror pocket floor a top surface.  With thin floppy mirror stock the
   mirror conforms to that floor, so turn ironing on for top surfaces.  With
   rigid mirror it does not matter.

   MIRROR EDGES NEED NO BEVEL
   At a 60° corner each mirror's body offsets away from its neighbour, so two
   square-cut edges can both reach the vertex without either one shadowing the
   other's reflective face.  Both mirrors are full width.  This only works in
   one handedness — all three mirrors must go in with the same rotational
   sense.
   ───────────────────────────────────────────────────────────────────────── */


// Cross-section of one side piece, at the station whose mirror-face triangle
// has side length `side`.  Face A is the bottom face (outward -Y); the piece
// owns face A plus the corner block at the A/B (right) corner.  Every bounding
// surface is a plane, so a ruled loft between two of these profiles is exact.
function sideProfile(side, pocket, w, lap, g, h, cl) returns array
{
    const S3 = sqrt(3);
    const rIdeal = side / (2 * S3);   // inradius of the mirror-face triangle
    const rp = rIdeal + pocket;       // inradius of the pocket floor
    const ro = rp + w;                // inradius of the outside
    const yIn = -rp;
    const yOut = -ro;
    const xL = -S3 * rp + lap;        // split plane at the C/A corner

    const uB = vector(-0.5, S3 / 2);  // along face B, away from the A/B corner
    const nB = vector(S3 / 2, 0.5);   // outward normal of face B
    const P = vector(S3 * rp, -rp) + lap * uB;

    const gc = g + 2 * cl;            // groove is the tongue plus clearance
    const hc = h + cl;

    return [
        vector(xL, yIn),                          //  1  floor, split end
        vector(S3 * rp, yIn),                     //  2  inner A/B corner
        P,                                        //  3  up face B by `lap`
        P + ((w - g) / 2) * nB,                   //  4  tongue
        P + ((w - g) / 2) * nB + h * uB,          //  5
        P + ((w + g) / 2) * nB + h * uB,          //  6
        P + ((w + g) / 2) * nB,                   //  7
        P + w * nB,                               //  8  outside of face B
        vector(S3 * ro, yOut),                    //  9  outer A/B corner
        vector(xL, yOut),                         // 10  back along the outside
        vector(xL, yOut + (w - gc) / 2),          // 11  groove
        vector(xL + hc, yOut + (w - gc) / 2),     // 12
        vector(xL + hc, yOut + (w + gc) / 2),     // 13
        vector(xL, yOut + (w + gc) / 2)           // 14
    ];
}

// Rectangle behind the mirror face: front on the ideal triangle, back `t` out.
function mirrorProfile(side, t) returns array
{
    const r = side / (2 * sqrt(3));
    return [
        vector(-side / 2, -r),
        vector(side / 2, -r),
        vector(side / 2, -(r + t)),
        vector(-side / 2, -(r + t))
    ];
}

function polySketch(context is Context, sk is Id, pl is Plane, pts is array)
{
    const s = newSketchOnPlane(context, sk, { "sketchPlane" : pl });
    for (var k = 0; k < size(pts); k += 1)
        skLineSegment(s, "e" ~ k, {
                "start" : pts[k],
                "end" : pts[(k + 1) % size(pts)]
        });
    skSolve(s);
}


annotation { "Feature Type Name" : "Kaleidoscope side" }
export const kaleidoscopeSide = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Mirror side, narrow end" }
        isLength(definition.narrowSide, { (inch) : [0.2, 1.0, 12.0] } as LengthBoundSpec);

        annotation { "Name" : "Mirror side, wide end" }
        isLength(definition.wideSide, { (inch) : [0.2, 2.0, 12.0] } as LengthBoundSpec);

        annotation { "Name" : "Length along axis" }
        isLength(definition.tubeLength, { (millimeter) : [10.0, 100.0, 800.0] } as LengthBoundSpec);

        annotation { "Name" : "Mirror thickness" }
        isLength(definition.mirrorThickness, { (millimeter) : [0.5, 1.6, 10.0] } as LengthBoundSpec);

        annotation { "Name" : "Bond layer (tape or silicone)" }
        isLength(definition.bondGap, { (millimeter) : [0.0, 0.2, 2.0] } as LengthBoundSpec);

        annotation { "Name" : "Wall thickness" }
        isLength(definition.wallThickness, { (millimeter) : [1.0, 3.0, 10.0] } as LengthBoundSpec);

        annotation { "Name" : "Mirror edge margin on floor" }
        isLength(definition.edgeMargin, { (millimeter) : [0.1, 1.0, 5.0] } as LengthBoundSpec);

        annotation { "Name" : "Tongue width" }
        isLength(definition.tongueWidth, { (millimeter) : [0.4, 1.2, 5.0] } as LengthBoundSpec);

        annotation { "Name" : "Tongue height" }
        isLength(definition.tongueHeight, { (millimeter) : [0.2, 0.8, 5.0] } as LengthBoundSpec);

        annotation { "Name" : "Tongue/groove clearance" }
        isLength(definition.tongueClearance, { (millimeter) : [0.0, 0.15, 1.0] } as LengthBoundSpec);

        annotation { "Name" : "Show all three (assembly check)", "Default" : false }
        definition.showAll is boolean;

        annotation { "Name" : "Include mirrors (reference)", "Default" : false }
        definition.showMirrors is boolean;
    }
    {
        const S3 = sqrt(3);
        const pocket = definition.mirrorThickness + definition.bondGap;
        const w = definition.wallThickness;
        const L = definition.tubeLength;

        const lap = S3 * pocket - definition.edgeMargin;
        if (lap < 0.4 * millimeter)
            throw regenError("Mirror edge margin is too large for this mirror thickness. "
                    ~ "Keep it below " ~ toString(S3 * pocket / millimeter) ~ " mm.");

        const planeN = plane(vector(0, 0, 0) * millimeter, vector(0, 0, 1), vector(1, 0, 0));
        const planeW = plane(vector(0, 0, 1) * L, vector(0, 0, 1), vector(1, 0, 0));

        const g = definition.tongueWidth;
        const h = definition.tongueHeight;
        const cl = definition.tongueClearance;

        polySketch(context, id + "skN", planeN,
                sideProfile(definition.narrowSide, pocket, w, lap, g, h, cl));
        polySketch(context, id + "skW", planeW,
                sideProfile(definition.wideSide, pocket, w, lap, g, h, cl));

        opLoft(context, id + "rail", {
                "profileSubqueries" : [
                    qSketchRegion(id + "skN", true),
                    qSketchRegion(id + "skW", true)
                ]
        });

        var junk = [qCreatedBy(id + "skN", EntityType.BODY),
                    qCreatedBy(id + "skW", EntityType.BODY)];

        if (definition.showMirrors)
        {
            polySketch(context, id + "mkN", planeN,
                    mirrorProfile(definition.narrowSide, definition.mirrorThickness));
            polySketch(context, id + "mkW", planeW,
                    mirrorProfile(definition.wideSide, definition.mirrorThickness));
            opLoft(context, id + "mirror", {
                    "profileSubqueries" : [
                        qSketchRegion(id + "mkN", true),
                        qSketchRegion(id + "mkW", true)
                    ]
            });
            junk = append(junk, qCreatedBy(id + "mkN", EntityType.BODY));
            junk = append(junk, qCreatedBy(id + "mkW", EntityType.BODY));
        }

        opDeleteBodies(context, id + "cleanup", { "entities" : qUnion(junk) });

        if (definition.showAll)
        {
            const axis = line(vector(0, 0, 0) * millimeter, vector(0, 0, 1));
            opPattern(context, id + "pat", {
                    "entities" : qCreatedBy(id, EntityType.BODY),
                    "transforms" : [rotationAround(axis, 120 * degree),
                                    rotationAround(axis, 240 * degree)],
                    "instanceNames" : ["b", "c"]
            });
        }

        // Lay the outside face on the XY plane with the material above it.
        // That face is tilted away from the tube axis by the taper half-angle,
        // so this is a rotation of (90° - taper) about X, not a flat 90°. After
        // it, the outside face is the lowest geometry in the part, so dropping
        // the bounding box to z = 0 seats it exactly on the plane.
        const m = (definition.wideSide - definition.narrowSide) / (2 * S3 * L);
        const theta = (abs(m) < 1e-9) ? 90 * degree : atan(1 / m);
        opTransform(context, id + "layFlat", {
                "bodies" : qCreatedBy(id, EntityType.BODY),
                "transform" : rotationAround(line(vector(0, 0, 0) * millimeter,
                                                  vector(1, 0, 0)), theta)
        });

        const bb = evBox3d(context, {
                "topology" : qCreatedBy(id, EntityType.BODY),
                "tight" : true
        });
        const mid = (bb.minCorner + bb.maxCorner) / 2;
        opTransform(context, id + "centre", {
                "bodies" : qCreatedBy(id, EntityType.BODY),
                "transform" : transform(vector(-mid[0], -mid[1], -bb.minCorner[2]))
        });
    });
