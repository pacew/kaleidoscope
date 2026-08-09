FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

/* ─────────────────────────────────────────────────────────────────────────
   Tapered kaleidoscope — open end caps.  Two per scope, press-fit.

   Each cap is a short triangular collar that slides over the outside of the
   tube.  Rounded exterior corners, open through the middle, no chamber.

   WHY THE TWO CAPS ARE NOT THE SAME SHAPE
   The tube tapers, so pushing a collar on means travelling toward one end or
   the other:

     narrow end — the collar travels toward the FAT part of the tube, the
       tube grows under it, and it tightens on its own.
     wide end — the collar travels toward the THIN part, the tube shrinks
       away beneath it, and a collar that merely copies the tube's taper gets
       LOOSER the harder you push.  No amount of interference fixes that; the
       bore has to converge on its own account.

   So the narrow cap's bore converges at (tube taper + grip angle), hugging
   the tube along its length, while the wide cap's bore converges at the grip
   angle alone.  Both then seat the same way: the tube's end rim wedges into
   the converging bore and stops.  Three line contacts at 120° on a
   converging cone — self-centring, and tilting drives one of them further
   into interference, so it does not rock.

   TOLERANCE
   Seating depth absorbs size error instead of the fit doing it.  At the
   default 3° grip, a 0.1 mm radial error moves the narrow cap 0.8 mm along
   and the wide cap 1.9 mm.  Keep capLength - engagement bigger than the
   travel you expect to need.

   PRINTING
   Modelled mouth-down on the XY plane, so each cap prints as it sits: flat
   on the bed, walls leaning inward by 3–7°, no supports.  Bore and outer
   profile share a corner radius offset by the wall thickness, which keeps
   the wall a constant thickness all the way round including the corners.
   ───────────────────────────────────────────────────────────────────────── */


// Equilateral triangle of inradius r with corners rounded to cr, drawn about
// the sketch origin with vertices at 90/210/330° — the same clocking as the
// rail cross-section, so a cap sits square on the tube.
function skRoundedTriangle(sk is Sketch, tag is string, r is ValueWithUnits, cr is ValueWithUnits)
{
    const rc = 2 * (r - cr);          // circumradius of the arc-centre triangle
    for (var i = 0; i < 3; i += 1)
    {
        const a = (90 + 120 * i) * degree;
        const c = rc * vector(cos(a), sin(a));
        const pStart = c + cr * vector(cos(a - 60 * degree), sin(a - 60 * degree));
        const pMid = c + cr * vector(cos(a), sin(a));
        const pEnd = c + cr * vector(cos(a + 60 * degree), sin(a + 60 * degree));
        skArc(sk, tag ~ "a" ~ i, { "start" : pStart, "mid" : pMid, "end" : pEnd });

        // straight side over to the next corner; both ends share this normal
        const aNext = (90 + 120 * ((i + 1) % 3)) * degree;
        const cNext = rc * vector(cos(aNext), sin(aNext));
        const qStart = cNext + cr * vector(cos(aNext - 60 * degree), sin(aNext - 60 * degree));
        skLineSegment(sk, tag ~ "l" ~ i, { "start" : pEnd, "end" : qStart });
    }
}

// One collar: bore goes from bore0 at the mouth (z = 0) to bore1 at the far
// end (z = Lc), outer profile offset from it by a constant wall.
function makeCap(context is Context, id is Id, tag is string, xOff is ValueWithUnits,
                 Lc is ValueWithUnits, bore0 is ValueWithUnits, bore1 is ValueWithUnits,
                 wall is ValueWithUnits, cr is ValueWithUnits)
{
    const b = id + tag;
    const pA = plane(vector(xOff, 0 * millimeter, 0 * millimeter), vector(0, 0, 1), vector(1, 0, 0));
    const pB = plane(vector(xOff, 0 * millimeter, Lc), vector(0, 0, 1), vector(1, 0, 0));

    const sO0 = newSketchOnPlane(context, b + "so0", { "sketchPlane" : pA });
    skRoundedTriangle(sO0, "o", bore0 + wall, cr + wall);
    skSolve(sO0);
    const sO1 = newSketchOnPlane(context, b + "so1", { "sketchPlane" : pB });
    skRoundedTriangle(sO1, "o", bore1 + wall, cr + wall);
    skSolve(sO1);
    opLoft(context, b + "outer", {
            "profileSubqueries" : [qSketchRegion(b + "so0", true), qSketchRegion(b + "so1", true)]
    });

    const sB0 = newSketchOnPlane(context, b + "sb0", { "sketchPlane" : pA });
    skRoundedTriangle(sB0, "i", bore0, cr);
    skSolve(sB0);
    const sB1 = newSketchOnPlane(context, b + "sb1", { "sketchPlane" : pB });
    skRoundedTriangle(sB1, "i", bore1, cr);
    skSolve(sB1);
    opLoft(context, b + "bore", {
            "profileSubqueries" : [qSketchRegion(b + "sb0", true), qSketchRegion(b + "sb1", true)]
    });

    opBoolean(context, b + "cut", {
            "tools" : qCreatedBy(b + "bore", EntityType.BODY),
            "targets" : qCreatedBy(b + "outer", EntityType.BODY),
            "operationType" : BooleanOperationType.SUBTRACTION
    });

    opDeleteBodies(context, b + "clean", {
            "entities" : qUnion([qCreatedBy(b + "so0", EntityType.BODY),
                                 qCreatedBy(b + "so1", EntityType.BODY),
                                 qCreatedBy(b + "sb0", EntityType.BODY),
                                 qCreatedBy(b + "sb1", EntityType.BODY)])
    });
}


annotation { "Feature Type Name" : "Kaleidoscope end caps" }
export const kaleidoscopeCaps = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Mirror side, narrow end" }
        isLength(definition.narrowSide, { (inch) : [0.2, 1.0, 12.0] } as LengthBoundSpec);

        annotation { "Name" : "Mirror side, wide end" }
        isLength(definition.wideSide, { (inch) : [0.2, 2.0, 12.0] } as LengthBoundSpec);

        annotation { "Name" : "Length along axis" }
        isLength(definition.tubeLength, { (millimeter) : [10.0, 100.0, 800.0] } as LengthBoundSpec);

        annotation { "Name" : "Mirror thickness" }
        isLength(definition.mirrorThickness, { (millimeter) : [0.5, 1.5875, 10.0] } as LengthBoundSpec);

        annotation { "Name" : "Bond layer" }
        isLength(definition.bondGap, { (millimeter) : [0.0, 0.2, 2.0] } as LengthBoundSpec);

        annotation { "Name" : "Rail wall thickness" }
        isLength(definition.wallThickness, { (millimeter) : [1.0, 3.0, 10.0] } as LengthBoundSpec);

        annotation { "Name" : "Cap length" }
        isLength(definition.capLength, { (millimeter) : [4.0, 14.0, 60.0] } as LengthBoundSpec);

        annotation { "Name" : "Engagement at nominal seating" }
        isLength(definition.engagement, { (millimeter) : [2.0, 8.0, 40.0] } as LengthBoundSpec);

        annotation { "Name" : "Grip angle" }
        isAngle(definition.gripAngle, { (degree) : [0.5, 3.0, 12.0] } as AngleBoundSpec);

        annotation { "Name" : "Cap wall thickness" }
        isLength(definition.capWall, { (millimeter) : [1.0, 2.5, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Bore corner radius" }
        isLength(definition.boreRound, { (millimeter) : [0.2, 1.5, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Space between the two caps" }
        isLength(definition.capGap, { (millimeter) : [0.0, 10.0, 80.0] } as LengthBoundSpec);
    }
    {
        const S3 = sqrt(3);
        const pocket = definition.mirrorThickness + definition.bondGap;
        const wall = definition.capWall;
        const cr = definition.boreRound;
        const Lc = definition.capLength;
        const E = definition.engagement;

        if (E >= Lc)
            throw regenError("Engagement must be shorter than the cap, or the tube pushes "
                    ~ "straight through it.");

        // tube outer inradius at each end, and its taper rate along the axis
        const roN = definition.narrowSide / (2 * S3) + pocket + definition.wallThickness;
        const roW = definition.wideSide / (2 * S3) + pocket + definition.wallThickness;
        const m = (definition.wideSide - definition.narrowSide) / (2 * S3 * definition.tubeLength);
        const k = tan(definition.gripAngle);

        // Both bores are sized so they touch the tube's end rim at depth E.
        // Narrow cap adds the tube's own taper, since the tube converges into
        // the cap; the wide cap does not, since the tube diverges into it.
        const nBore0 = roN + (m + k) * E;
        const nBore1 = roN + (m + k) * (E - Lc);
        const wBore0 = roW + k * E;
        const wBore1 = roW + k * (E - Lc);

        if (nBore1 - cr <= 0 * millimeter || wBore1 - cr <= 0 * millimeter)
            throw regenError("Cap is too long for this grip angle — the bore closes up. "
                    ~ "Shorten it or reduce the grip angle.");

        makeCap(context, id, "narrow", 0 * millimeter, Lc, nBore0, nBore1, wall, cr);

        // clear of one another: outermost point of a rounded triangle is 2r - cr
        const xOff = (2 * (nBore0 + wall) - (cr + wall))
                   + (2 * (wBore0 + wall) - (cr + wall)) + definition.capGap;
        makeCap(context, id, "wide", xOff, Lc, wBore0, wBore1, wall, cr);
    });
