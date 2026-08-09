FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

/* ─────────────────────────────────────────────────────────────────────────
   Tapered kaleidoscope — SMALL END CAP.  Print one.

   One part, floor on the XY plane, skirt and bump ramps pointing up — which
   is also how it is used: cap on the table, plates dropped in one at a time
   until the bumps engage, then the mirrors.

   Deliberately a loose fit over the tube, not a press fit.  Three inward
   bumps drop into pockets in the plates and do the holding.  Each bump has a
   ramped top so a plate cams over it going in, and a flat bottom — that flat
   is what stops the cap sliding back off.  Printed floor-down, the ramp needs
   no support and the flat retaining face is a short bridge.

   The floor's aperture is a little smaller than the optical face, so its lip
   overlaps the mirror ends and catches them.  Mirrors slide freely in a
   tube whose taper matches their own, so without this lip they would simply
   fall out the bottom during assembly.
   ───────────────────────────────────────────────────────────────────────── */

function skRoundedTri(sk is Sketch, tag is string, r is ValueWithUnits, cr is ValueWithUnits)
{
    const rc = 2 * (r - cr);
    for (var i = 0; i < 3; i += 1)
    {
        const a = (90 + 120 * i) * degree;
        const c = rc * vector(cos(a), sin(a));
        skArc(sk, tag ~ "a" ~ i, {
                "start" : c + cr * vector(cos(a - 60 * degree), sin(a - 60 * degree)),
                "mid" : c + cr * vector(cos(a), sin(a)),
                "end" : c + cr * vector(cos(a + 60 * degree), sin(a + 60 * degree))
        });
        const aN = (90 + 120 * ((i + 1) % 3)) * degree;
        const cN = rc * vector(cos(aN), sin(aN));
        skLineSegment(sk, tag ~ "l" ~ i, {
                "start" : c + cr * vector(cos(a + 60 * degree), sin(a + 60 * degree)),
                "end" : cN + cr * vector(cos(aN - 60 * degree), sin(aN - 60 * degree))
        });
    }
}

function triLoft(context is Context, base is Id, zA is ValueWithUnits, zB is ValueWithUnits,
                 rA is ValueWithUnits, rB is ValueWithUnits, cr is ValueWithUnits)
{
    const s0 = newSketchOnPlane(context, base + "s0", {
            "sketchPlane" : plane(vector(0, 0, 1) * zA, vector(0, 0, 1), vector(1, 0, 0)) });
    skRoundedTri(s0, "t", rA, cr);
    skSolve(s0);
    const s1 = newSketchOnPlane(context, base + "s1", {
            "sketchPlane" : plane(vector(0, 0, 1) * zB, vector(0, 0, 1), vector(1, 0, 0)) });
    skRoundedTri(s1, "t", rB, cr);
    skSolve(s1);
    opLoft(context, base + "L", {
            "profileSubqueries" : [qSketchRegion(base + "s0", true), qSketchRegion(base + "s1", true)]
    });
    opDeleteBodies(context, base + "d", {
            "entities" : qUnion([qCreatedBy(base + "s0", EntityType.BODY),
                                 qCreatedBy(base + "s1", EntityType.BODY)])
    });
}

annotation { "Feature Type Name" : "Kaleidoscope small end cap" }
export const kaleidoscopeSmallCap = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Optical face, narrow end" }
        isLength(definition.narrowSide, { (inch) : [0.2, 1.0, 12.0] } as LengthBoundSpec);

        annotation { "Name" : "Optical face, wide end" }
        isLength(definition.wideSide, { (inch) : [0.2, 2.0, 12.0] } as LengthBoundSpec);

        annotation { "Name" : "Length along axis" }
        isLength(definition.tubeLength, { (millimeter) : [10.0, 100.0, 800.0] } as LengthBoundSpec);

        annotation { "Name" : "Mirror thickness" }
        isLength(definition.mirrorThickness, { (millimeter) : [0.5, 1.5875, 10.0] } as LengthBoundSpec);

        annotation { "Name" : "Plate thickness" }
        isLength(definition.plateThickness, { (millimeter) : [1.5, 3.0, 10.0] } as LengthBoundSpec);

        annotation { "Name" : "Skirt length" }
        isLength(definition.capLength, { (millimeter) : [5.0, 16.0, 60.0] } as LengthBoundSpec);

        annotation { "Name" : "Clearance over the tube" }
        isLength(definition.capClearance, { (millimeter) : [0.0, 0.3, 2.0] } as LengthBoundSpec);

        annotation { "Name" : "Wall" }
        isLength(definition.capWall, { (millimeter) : [1.0, 2.5, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Floor thickness" }
        isLength(definition.capFloor, { (millimeter) : [1.0, 2.0, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Lip overlap onto the mirror" }
        isLength(definition.lipOverlap, { (millimeter) : [0.2, 0.8, 5.0] } as LengthBoundSpec);

        annotation { "Name" : "Detent position from narrow end" }
        isLength(definition.detentZ, { (millimeter) : [3.0, 8.0, 60.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump width" }
        isLength(definition.bumpWidth, { (millimeter) : [2.0, 6.0, 30.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump length along axis" }
        isLength(definition.bumpLength, { (millimeter) : [1.0, 3.0, 20.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump height" }
        isLength(definition.bumpHeight, { (millimeter) : [0.2, 0.8, 3.0] } as LengthBoundSpec);

        annotation { "Name" : "Corner relief radius" }
        isLength(definition.cornerRound, { (millimeter) : [0.5, 1.5, 6.0] } as LengthBoundSpec);
    }
    {
        const S3 = sqrt(3);
        const cr = definition.cornerRound;
        const cc = definition.capClearance;
        const cw = definition.capWall;
        const fl = definition.capFloor;
        const skirt = definition.capLength;

        const m = (definition.wideSide - definition.narrowSide) / (2 * S3 * definition.tubeLength);
        const roN = definition.narrowSide / (2 * S3)
                  + definition.mirrorThickness + definition.plateThickness;

        // Floor occupies z 0..fl; the skirt sits above it, so tube station
        // z_tube = z_model - fl.
        const boreBot = roN + cc;                    // at z = fl
        const boreTop = roN + m * skirt + cc;        // at z = fl + skirt
        const boreFloor = roN - m * fl + cc;         // extrapolated down to z = 0

        triLoft(context, id + "o", 0 * millimeter, fl + skirt,
                boreFloor + cw, boreTop + cw, cr + cw);
        triLoft(context, id + "b", fl, fl + skirt, boreBot, boreTop, cr);
        opBoolean(context, id + "bcut", {
                "tools" : qCreatedBy(id + "b", EntityType.BODY),
                "targets" : qCreatedBy(id + "o", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        const apR = definition.narrowSide / (2 * S3) - definition.lipOverlap;
        if (apR <= cr)
            throw regenError("Lip overlap is too big for this narrow end.");
        triLoft(context, id + "ap", -1 * millimeter, fl + 1 * millimeter, apR, apR, cr);
        opBoolean(context, id + "apcut", {
                "tools" : qCreatedBy(id + "ap", EntityType.BODY),
                "targets" : qCreatedBy(id + "o", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        // One bump on the bottom flat, then patterned.  Sketched at
        // x = -bumpWidth/2 with local x = axis and local y measured outward.
        const bw = definition.bumpWidth;
        const bh = definition.bumpHeight;
        const zc = fl + definition.detentZ;
        const h0 = zc - definition.bumpLength / 2;
        const h1 = zc + definition.bumpLength / 2;
        const ramp = 1.6 * bh;                       // ~32° lead-in
        const bMid = roN + m * definition.detentZ + cc;
        const bs = newSketchOnPlane(context, id + "bsk", {
                "sketchPlane" : plane(vector(-1, 0, 0) * (bw / 2), vector(1, 0, 0), vector(0, 0, 1)) });
        skPolyline(bs, "p", { "points" : [
                    vector(h0, bMid + 1 * millimeter),
                    vector(h0, bMid - bh),
                    vector(h1, bMid - bh),
                    vector(h1 + ramp, bMid + 1 * millimeter),
                    vector(h0, bMid + 1 * millimeter)] });
        skSolve(bs);
        opExtrude(context, id + "bump", {
                "entities" : qSketchRegion(id + "bsk"),
                "direction" : vector(1, 0, 0),
                "endBound" : BoundingType.BLIND,
                "endDepth" : bw
        });
        opDeleteBodies(context, id + "bskd", { "entities" : qCreatedBy(id + "bsk", EntityType.BODY) });

        const zAxis = line(vector(0, 0, 0) * millimeter, vector(0, 0, 1));
        opPattern(context, id + "bpat", {
                "entities" : qCreatedBy(id + "bump", EntityType.BODY),
                "transforms" : [rotationAround(zAxis, 120 * degree), rotationAround(zAxis, 240 * degree)],
                "instanceNames" : ["b", "c"]
        });
        opBoolean(context, id + "join", {
                "tools" : qUnion([qCreatedBy(id + "o", EntityType.BODY),
                                  qCreatedBy(id + "bump", EntityType.BODY),
                                  qCreatedBy(id + "bpat", EntityType.BODY)]),
                "operationType" : BooleanOperationType.UNION
        });
    });
