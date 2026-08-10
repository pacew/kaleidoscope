FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

/* ─────────────────────────────────────────────────────────────────────────
   Tapered kaleidoscope — CLAMPING COLLAR.  Print one.

   One part, mouth on the XY plane, as it prints and as it slides on.

   The collar goes on over the narrow end and is pushed toward the wide end.
   Because the tube grows that way, a bore cut to the tube's own taper closes
   on it uniformly and wedges with full-face contact — a straight bore would
   only touch on its leading rim and could rock.  Bore corners are relieved so
   it bears on the flats and squeezes the mitres shut rather than prising the
   corners apart.

   That wedge is tolerant of size error but pays for it in seating depth:
   13.6 mm of travel per 1 mm of radial error, so the collar lands a couple of
   millimetres either side of nominal.  The large cap's blades carry the slot
   that absorbs it.

   Blade sits in x = [-bladeThick, 0] so the large cap's blade lies against it
   on the plane x = 0, bolt running tangentially through both — head and nut
   both end up in free air.  The hole prints with its axis horizontal, so its
   top will droop a little; it is cut oversize to absorb that.
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

annotation { "Feature Type Name" : "Kaleidoscope collar" }
export const kaleidoscopeCollar = defineFeature(function(context is Context, id is Id, definition is map)
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

        annotation { "Name" : "Seat, from the narrow end" }
        isLength(definition.collarSeatZ, { (millimeter) : [5.0, 76.0, 700.0] } as LengthBoundSpec);

        annotation { "Name" : "Collar length" }
        isLength(definition.collarLength, { (millimeter) : [5.0, 12.0, 60.0] } as LengthBoundSpec);

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

        annotation { "Name" : "Corner relief radius" }
        isLength(definition.cornerRound, { (millimeter) : [0.5, 1.5, 6.0] } as LengthBoundSpec);
    }
    {
        const S3 = sqrt(3);
        const L = definition.tubeLength;
        const cr = definition.cornerRound;
        const cw = definition.collarWall;
        const bt = definition.bladeThick;
        const Lc = definition.collarLength;
        const zSeat = definition.collarSeatZ;

        if (zSeat + Lc > L)
            throw regenError("Collar runs off the wide end. Move the seat down or shorten it.");

        const m = (definition.wideSide - definition.narrowSide) / (2 * S3 * L);
        const roN = definition.narrowSide / (2 * S3)
                  + definition.mirrorThickness + definition.plateThickness;

        const bore0 = roN + m * zSeat;
        const bore1 = roN + m * (zSeat + Lc);

        triLoft(context, id + "o", 0 * millimeter, Lc, bore0 + cw, bore1 + cw, cr + cw);
        triLoft(context, id + "b", 0 * millimeter, Lc, bore0, bore1, cr);
        opBoolean(context, id + "cut", {
                "tools" : qCreatedBy(id + "b", EntityType.BODY),
                "targets" : qCreatedBy(id + "o", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        // Blade on the bottom flat, occupying x in [-bladeThick, 0].  It runs
        // the full height of the collar so its underside lands on the build
        // plate — anything shorter leaves the part of the blade that overhangs
        // the collar wall printing in mid-air.
        const zMid = Lc / 2;
        const outMid = roN + m * (zSeat + zMid) + cw;
        const bs = newSketchOnPlane(context, id + "bsk", {
                "sketchPlane" : plane(vector(-1, 0, 0) * bt, vector(1, 0, 0), vector(0, 0, 1)) });
        skRectangle(bs, "r", {
                "firstCorner" : vector(0 * millimeter, outMid - cw + 1 * millimeter),
                "secondCorner" : vector(Lc, outMid + definition.bladeReach)
        });
        skCircle(bs, "h", { "center" : vector(zMid, outMid + definition.holeOut),
                            "radius" : definition.holeDia / 2 });
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
