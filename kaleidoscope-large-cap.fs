FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

/* ─────────────────────────────────────────────────────────────────────────
   Tapered kaleidoscope — LARGE END CAP.  Print one.

   One part, floor on the XY plane, skirt and blades pointing up.  Note that
   this is upside-down from how it is used: in service the floor is uppermost,
   sitting on the tube's wide end face, with the blades reaching back down the
   outside to meet the collar.

   It retains the mirrors at the wide end and carries the slotted half of the
   bolted joint.  The slot runs along the tube axis, because the collar wedges
   at a position that moves 13.6 mm per 1 mm of radial size error and round
   holes in both parts could never line up.

   Blade sits in x = [0, bladeThick] so it lies against the collar's blade on
   the plane x = 0, bolt tangential through both.

   Tightening the bolts drives the collar further up the taper while pulling
   this cap down onto the end face, so the joint self-tightens.
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

// obround centred on c, running along the sketch's local x
function skSlot(sk is Sketch, tag is string, c is Vector, halfLen is ValueWithUnits,
                r is ValueWithUnits)
{
    const z = 0 * millimeter;
    const a = c + vector(-halfLen, z);
    const b = c + vector(halfLen, z);
    skLineSegment(sk, tag ~ "u", { "start" : a + vector(z, r), "end" : b + vector(z, r) });
    skArc(sk, tag ~ "e", { "start" : b + vector(z, r), "mid" : b + vector(r, z),
                           "end" : b + vector(z, -r) });
    skLineSegment(sk, tag ~ "d", { "start" : b + vector(z, -r), "end" : a + vector(z, -r) });
    skArc(sk, tag ~ "w", { "start" : a + vector(z, -r), "mid" : a + vector(-r, z),
                           "end" : a + vector(z, r) });
}

annotation { "Feature Type Name" : "Kaleidoscope large end cap" }
export const kaleidoscopeLargeCap = defineFeature(function(context is Context, id is Id, definition is map)
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

        annotation { "Name" : "Floor thickness" }
        isLength(definition.endFloor, { (millimeter) : [1.0, 2.5, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Skirt length" }
        isLength(definition.endSkirt, { (millimeter) : [2.0, 6.0, 40.0] } as LengthBoundSpec);

        annotation { "Name" : "Clearance over the tube" }
        isLength(definition.endClear, { (millimeter) : [0.0, 0.3, 2.0] } as LengthBoundSpec);

        annotation { "Name" : "Wall" }
        isLength(definition.endWall, { (millimeter) : [1.5, 2.5, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Lip overlap onto the mirror" }
        isLength(definition.lipOverlap, { (millimeter) : [0.2, 0.8, 5.0] } as LengthBoundSpec);

        annotation { "Name" : "Collar seat AS PRINTED (sets bolt radius)" }
        isLength(definition.collarSeatZ, { (millimeter) : [5.0, 76.0, 700.0] } as LengthBoundSpec);

        annotation { "Name" : "MEASURED collar top to plate wide edge" }
        isLength(definition.collarTopToEnd, { (millimeter) : [0.0, 17.8, 200.0] } as LengthBoundSpec);

        annotation { "Name" : "Collar length" }
        isLength(definition.collarLength, { (millimeter) : [5.0, 12.0, 60.0] } as LengthBoundSpec);

        annotation { "Name" : "Ear offset (clears the collar's ear)" }
        isLength(definition.earOffset, { (millimeter) : [0.0, 3.5, 20.0] } as LengthBoundSpec);

        annotation { "Name" : "Collar wall" }
        isLength(definition.collarWall, { (millimeter) : [1.5, 2.5, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Blade thickness" }
        isLength(definition.bladeThick, { (millimeter) : [1.5, 3.0, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Bolt centre, out from the collar face" }
        isLength(definition.holeOut, { (millimeter) : [3.0, 6.0, 30.0] } as LengthBoundSpec);

        annotation { "Name" : "Blade reach, out from the collar face" }
        isLength(definition.bladeReach, { (millimeter) : [5.0, 11.0, 40.0] } as LengthBoundSpec);

        annotation { "Name" : "Bolt hole diameter" }
        isLength(definition.holeDia, { (millimeter) : [2.0, 3.6, 10.0] } as LengthBoundSpec);

        annotation { "Name" : "Slot travel (total, about nominal)" }
        isLength(definition.slotTravel, { (millimeter) : [0.0, 6.0, 30.0] } as LengthBoundSpec);

        annotation { "Name" : "Corner relief radius" }
        isLength(definition.cornerRound, { (millimeter) : [0.5, 1.5, 6.0] } as LengthBoundSpec);
    }
    {
        const S3 = sqrt(3);
        const L = definition.tubeLength;
        const cr = definition.cornerRound;
        const ew = definition.endWall;
        const ec = definition.endClear;
        const fl = definition.endFloor;
        const sk = definition.endSkirt;
        const bt = definition.bladeThick;
        const hr = definition.holeDia / 2;

        const m = (definition.wideSide - definition.narrowSide) / (2 * S3 * L);
        const roN = definition.narrowSide / (2 * S3)
                  + definition.mirrorThickness + definition.plateThickness;

        // Built upside-down: model z measures down from the outside of the
        // floor, so tube station z_tube = L - (z_model - fl).
        const boreTop = roN + m * (L + fl) + ec;     // extrapolated, at z = 0
        const boreMid = roN + m * L + ec;            // at z = fl, the end face
        const boreLow = roN + m * (L - sk) + ec;     // at z = fl + sk

        triLoft(context, id + "o", 0 * millimeter, fl + sk, boreTop + ew, boreLow + ew, cr + ew);
        triLoft(context, id + "b", fl, fl + sk, boreMid, boreLow, cr);
        opBoolean(context, id + "cut", {
                "tools" : qCreatedBy(id + "b", EntityType.BODY),
                "targets" : qCreatedBy(id + "o", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        const apR = definition.wideSide / (2 * S3) - definition.lipOverlap;
        if (apR <= cr)
            throw regenError("Lip overlap is too big for this wide end.");
        triLoft(context, id + "ap", -1 * millimeter, fl + 1 * millimeter, apR, apR, cr);
        opBoolean(context, id + "apcut", {
                "tools" : qCreatedBy(id + "ap", EntityType.BODY),
                "targets" : qCreatedBy(id + "o", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        // Blade in x = [earOffset, earOffset + bladeThick].  The offset is what
        // keeps it clear of the collar's ear: this cap prints upside-down and
        // has to be turned over to use, and any 180° flip that keeps the flats
        // aligned reverses x — so a blade modelled at x = [0, bt] lands exactly
        // on top of the collar's at x = [-bt, 0].  Separating them costs a full
        // blade thickness plus clearance, not half of one.
        //
        // Bolt RADIUS comes from the collar's own model, since the blade's
        // radius is baked into that printed part and does not change with where
        // the collar ends up sitting.
        const outMid = roN + m * (definition.collarSeatZ + definition.collarLength / 2)
                     + definition.collarWall;
        // Bolt AXIAL position comes from the built scope instead: the wedge
        // lands where it lands, and on the first build it stopped 5.8 mm short
        // of the design seat.  Measure along the axis from the collar's wide
        // edge to the plates' wide edge.
        const collarMidZ = L - definition.collarTopToEnd - definition.collarLength / 2;
        const slotZ = fl + (L - collarMidZ);
        const halfSlot = definition.slotTravel / 2;
        const bladeTop = slotZ + halfSlot + hr + 4 * millimeter;
        const bs = newSketchOnPlane(context, id + "bsk", {
                "sketchPlane" : plane(vector(1, 0, 0) * definition.earOffset,
                                      vector(1, 0, 0), vector(0, 0, 1)) });
        skRectangle(bs, "r", {
                "firstCorner" : vector(0 * millimeter, boreMid + 0.5 * millimeter),
                "secondCorner" : vector(bladeTop, outMid + definition.bladeReach)
        });
        skSlot(bs, "s", vector(slotZ, outMid + definition.holeOut), halfSlot, hr);
        skSolve(bs);
        opExtrude(context, id + "blade", {
                "entities" : qSketchRegion(id + "bsk", true),
                "direction" : vector(1, 0, 0),
                "endBound" : BoundingType.BLIND,
                "endDepth" : bt
        });
        opDeleteBodies(context, id + "bskd", { "entities" : qCreatedBy(id + "bsk", EntityType.BODY) });

        const zAxis = line(vector(0, 0, 0) * millimeter, vector(0, 0, 1));
        opPattern(context, id + "bpat", {
                "entities" : qCreatedBy(id + "blade", EntityType.BODY),
                "transforms" : [rotationAround(zAxis, 120 * degree), rotationAround(zAxis, 240 * degree)],
                "instanceNames" : ["b", "c"]
        });
        opBoolean(context, id + "join", {
                "tools" : qUnion([qCreatedBy(id + "o", EntityType.BODY),
                                  qCreatedBy(id + "blade", EntityType.BODY),
                                  qCreatedBy(id + "bpat", EntityType.BODY)]),
                "operationType" : BooleanOperationType.UNION
        });
    });
