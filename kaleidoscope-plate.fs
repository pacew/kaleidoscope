FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

/* ─────────────────────────────────────────────────────────────────────────
   Tapered kaleidoscope — side plate and small end cap.

   Three flat mitred plates form the tube.  Nothing interlocks them: the small
   end cap holds the narrow end, a collar (separate file) wedges near the wide
   end, and the mirrors drop in loose.  No adhesive anywhere.

   THE MIRROR SITS ON THE PLATE, NOT IN A POCKET
   So the plate's inner face is one mirror thickness outboard of the optical
   plane, and the plate is a good deal wider than its mirror: 30.90 mm inner
   face at the narrow end against a 25.40 mm optical face.

   MITRE
   30° off the plate's plane at both long edges, which is what closes three
   plates into a 60° corner.  The outer face runs sqrt(3)*w past the inner
   one, so the feather edge is on the OUTSIDE corner of the tube, not the
   inside — truncating it costs nothing optically and leaves a small V-notch
   down each outer corner that the collar bridges.  Without the truncation the
   tip goes to zero thickness and simply will not print.

   CORNER ROOM
   The mirror may still overlap past the optical vertex, just less than it
   could with a pocket: 1.155 * mirrorThickness = 1.83 mm here, against the
   1.00 mm the blanks carry.  Past that it fouls the neighbouring plate.

   DETENT
   A pocket in the plate's outer face near the narrow end takes an inward bump
   on the cap.  The bump's top is ramped so the plate cams over it going in;
   its bottom is flat, and that flat is what stops the cap sliding back off.
   Insert the plates one at a time — three plates cannot all flex past their
   bumps at once, since the closed mitres resist it.

   PRINTING
   Plate: outer face down on the XY plane, cross-section narrowing upward, so
   the mitres lean inward rather than overhang.  No supports, bed finish on
   the visible outside, mirror seat is a top surface — turn ironing on.
   Cap: prints as modelled, aperture end down, bump ramps facing up.
   ───────────────────────────────────────────────────────────────────────── */


// Equilateral triangle of inradius r, corners rounded to cr, vertices at
// 90/210/330° — same clocking as the tube.
function skRoundedTri(sk is Sketch, tag is string, r is ValueWithUnits, cr is ValueWithUnits)
{
    const rc = 2 * (r - cr);
    for (var i = 0; i < 3; i += 1)
    {
        const a = (90 + 120 * i) * degree;
        const c = rc * vector(cos(a), sin(a));
        const pS = c + cr * vector(cos(a - 60 * degree), sin(a - 60 * degree));
        const pM = c + cr * vector(cos(a), sin(a));
        const pE = c + cr * vector(cos(a + 60 * degree), sin(a + 60 * degree));
        skArc(sk, tag ~ "a" ~ i, { "start" : pS, "mid" : pM, "end" : pE });
        const aN = (90 + 120 * ((i + 1) % 3)) * degree;
        const cN = rc * vector(cos(aN), sin(aN));
        skLineSegment(sk, tag ~ "l" ~ i, {
                "start" : pE,
                "end" : cN + cr * vector(cos(aN - 60 * degree), sin(aN - 60 * degree))
        });
    }
}

function polySketch(context is Context, skId is Id, pl is Plane, pts is array)
{
    const s = newSketchOnPlane(context, skId, { "sketchPlane" : pl });
    for (var k = 0; k < size(pts); k += 1)
        skLineSegment(s, "e" ~ k, { "start" : pts[k], "end" : pts[(k + 1) % size(pts)] });
    skSolve(s);
}

// One plate's cross-section.  Face at the bottom, outward -Y.
function plateProfile(side, t, w, land) returns array
{
    const S3 = sqrt(3);
    const rp = side / (2 * S3) + t;      // inner face: the mirror seat
    const ro = rp + w;                   // outer face
    const xi = S3 * rp;                  // inner half-width
    const xo = S3 * (ro - land);         // outer half-width, mitre tip truncated
    return [vector(-xi, -rp), vector(xi, -rp),
            vector(xo, -ro + land), vector(xo, -ro),
            vector(-xo, -ro), vector(-xo, -ro + land)];
}

function triLoft(context is Context, base is Id, pA is Plane, pB is Plane,
                 rA is ValueWithUnits, rB is ValueWithUnits, cr is ValueWithUnits)
{
    const s0 = newSketchOnPlane(context, base + "s0", { "sketchPlane" : pA });
    skRoundedTri(s0, "t", rA, cr);
    skSolve(s0);
    const s1 = newSketchOnPlane(context, base + "s1", { "sketchPlane" : pB });
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


annotation { "Feature Type Name" : "Kaleidoscope plate and small cap" }
export const kaleidoscopePlate = defineFeature(function(context is Context, id is Id, definition is map)
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

        annotation { "Name" : "Mitre tip truncation" }
        isLength(definition.miterLand, { (millimeter) : [0.2, 0.6, 3.0] } as LengthBoundSpec);

        annotation { "Name" : "Detent position from narrow end" }
        isLength(definition.detentZ, { (millimeter) : [3.0, 8.0, 60.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump size (width x along axis)" }
        isLength(definition.bumpWidth, { (millimeter) : [2.0, 6.0, 30.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump length along axis" }
        isLength(definition.bumpLength, { (millimeter) : [1.0, 3.0, 20.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump height" }
        isLength(definition.bumpHeight, { (millimeter) : [0.2, 0.8, 3.0] } as LengthBoundSpec);

        annotation { "Name" : "Detent clearance (generous for v1)" }
        isLength(definition.detentClear, { (millimeter) : [0.1, 1.0, 4.0] } as LengthBoundSpec);

        annotation { "Name" : "Cap skirt length" }
        isLength(definition.capLength, { (millimeter) : [5.0, 16.0, 60.0] } as LengthBoundSpec);

        annotation { "Name" : "Cap clearance over the tube" }
        isLength(definition.capClearance, { (millimeter) : [0.0, 0.3, 2.0] } as LengthBoundSpec);

        annotation { "Name" : "Cap wall" }
        isLength(definition.capWall, { (millimeter) : [1.0, 2.5, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Cap floor thickness" }
        isLength(definition.capFloor, { (millimeter) : [1.0, 2.0, 8.0] } as LengthBoundSpec);

        annotation { "Name" : "Lip overlap onto the mirror" }
        isLength(definition.lipOverlap, { (millimeter) : [0.2, 0.8, 5.0] } as LengthBoundSpec);

        annotation { "Name" : "Corner relief radius" }
        isLength(definition.cornerRound, { (millimeter) : [0.5, 1.5, 6.0] } as LengthBoundSpec);

        annotation { "Name" : "Gap between the laid-out parts" }
        isLength(definition.layoutGap, { (millimeter) : [0.0, 12.0, 80.0] } as LengthBoundSpec);
    }
    {
        const S3 = sqrt(3);
        const t = definition.mirrorThickness;
        const w = definition.plateThickness;
        const land = definition.miterLand;
        const L = definition.tubeLength;
        const cr = definition.cornerRound;
        const cc = definition.capClearance;

        const m = (definition.wideSide - definition.narrowSide) / (2 * S3 * L);
        const roN = definition.narrowSide / (2 * S3) + t + w;   // tube outer, narrow end

        if (land >= w)
            throw regenError("Mitre truncation must be less than the plate thickness.");

        // ── plate ────────────────────────────────────────────────────────
        const pl0 = plane(vector(0, 0, 0) * millimeter, vector(0, 0, 1), vector(1, 0, 0));
        const plL = plane(vector(0, 0, 1) * L, vector(0, 0, 1), vector(1, 0, 0));
        polySketch(context, id + "pk0", pl0, plateProfile(definition.narrowSide, t, w, land));
        polySketch(context, id + "pk1", plL, plateProfile(definition.wideSide, t, w, land));
        opLoft(context, id + "plate", {
                "profileSubqueries" : [qSketchRegion(id + "pk0", true), qSketchRegion(id + "pk1", true)]
        });
        opDeleteBodies(context, id + "pkd", {
                "entities" : qUnion([qCreatedBy(id + "pk0", EntityType.BODY),
                                     qCreatedBy(id + "pk1", EntityType.BODY)])
        });

        // detent pocket, cut on a plane parallel to the plate's outer face
        const nOut = normalize(vector(0, -1, -m));
        const pOut = plane(vector(0 * millimeter, -roN, 0 * millimeter) + 1 * millimeter * nOut,
                           nOut, vector(1, 0, 0));
        const vW = definition.bumpWidth + 2 * definition.detentClear;
        const vL = definition.bumpLength + 2 * definition.detentClear;
        const vD = definition.bumpHeight + definition.detentClear;
        const alongPlate = definition.detentZ * sqrt(1 + m * m);
        const vs = newSketchOnPlane(context, id + "vsk", { "sketchPlane" : pOut });
        skRectangle(vs, "r", {
                "firstCorner" : vector(-vW / 2, alongPlate - vL / 2),
                "secondCorner" : vector(vW / 2, alongPlate + vL / 2)
        });
        skSolve(vs);
        opExtrude(context, id + "vtool", {
                "entities" : qSketchRegion(id + "vsk"),
                "direction" : -nOut,
                "endBound" : BoundingType.BLIND,
                "endDepth" : 1 * millimeter + vD
        });
        opBoolean(context, id + "vcut", {
                "tools" : qCreatedBy(id + "vtool", EntityType.BODY),
                "targets" : qCreatedBy(id + "plate", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });
        opDeleteBodies(context, id + "vskd", {
                "entities" : qCreatedBy(id + "vsk", EntityType.BODY)
        });

        // lay the outer face on XY, material above
        const plateQ = qCreatedBy(id + "plate", EntityType.BODY);
        opTransform(context, id + "prot", {
                "bodies" : plateQ,
                "transform" : rotationAround(line(vector(0, 0, 0) * millimeter, vector(1, 0, 0)),
                                             atan(1 / m))
        });
        const bb = evBox3d(context, { "topology" : plateQ, "tight" : true });
        const mid = (bb.minCorner + bb.maxCorner) / 2;
        opTransform(context, id + "pctr", {
                "bodies" : plateQ,
                "transform" : transform(vector(-mid[0], -mid[1], -bb.minCorner[2]))
        });

        // ── small end cap ────────────────────────────────────────────────
        const capL = definition.capLength;
        const floor = definition.capFloor;
        const bore0 = roN + cc;                     // at the cap's floor, h = 0
        const bore1 = roN + m * capL + cc;          // at the skirt's top
        const boreF = roN - m * floor + cc;         // extrapolated below the floor

        // put it clear of the plate
        const xCap = (bb.maxCorner[0] - bb.minCorner[0]) / 2
                   + (2 * (bore1 + definition.capWall) - (cr + definition.capWall))
                   + definition.layoutGap;
        const capO = vector(xCap, 0 * millimeter, 0 * millimeter);

        const cA = plane(capO - vector(0, 0, 1) * floor, vector(0, 0, 1), vector(1, 0, 0));
        const cB = plane(capO, vector(0, 0, 1), vector(1, 0, 0));
        const cC = plane(capO + vector(0, 0, 1) * capL, vector(0, 0, 1), vector(1, 0, 0));

        triLoft(context, id + "co", cA, cC, boreF + definition.capWall,
                bore1 + definition.capWall, cr + definition.capWall);
        triLoft(context, id + "cb", cB, cC, bore0, bore1, cr);
        opBoolean(context, id + "cbcut", {
                "tools" : qCreatedBy(id + "cb", EntityType.BODY),
                "targets" : qCreatedBy(id + "co", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        // aperture through the floor, lipOverlap in from the optical face
        const apR = definition.narrowSide / (2 * S3) - definition.lipOverlap;
        if (apR <= cr)
            throw regenError("Lip overlap is too big for this narrow end.");
        triLoft(context, id + "cap",
                plane(capO - vector(0, 0, 1) * (floor + 1 * millimeter), vector(0, 0, 1), vector(1, 0, 0)),
                plane(capO + vector(0, 0, 1) * (1 * millimeter), vector(0, 0, 1), vector(1, 0, 0)),
                apR, apR, cr);
        opBoolean(context, id + "apcut", {
                "tools" : qCreatedBy(id + "cap", EntityType.BODY),
                "targets" : qCreatedBy(id + "co", EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
        });

        // one bump on the bottom flat, then patterned to the other two.
        // Sketched in the plane x = -bumpWidth/2 with local x = axis, local y
        // pointing outward, so the profile is written in +bore terms.
        const bw = definition.bumpWidth;
        const h0 = definition.detentZ - definition.bumpLength / 2;
        const h1 = definition.detentZ + definition.bumpLength / 2;
        const ramp = 1.6 * definition.bumpHeight;   // ~32° lead-in
        const bMid = roN + m * definition.detentZ + cc;
        const bp = plane(capO - vector(1, 0, 0) * (bw / 2), vector(1, 0, 0), vector(0, 0, 1));
        const bs = newSketchOnPlane(context, id + "bsk", { "sketchPlane" : bp });
        skPolyline(bs, "p", { "points" : [
                    vector(h0, bMid + 1 * millimeter),
                    vector(h0, bMid - definition.bumpHeight),
                    vector(h1, bMid - definition.bumpHeight),
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

        const axis = line(capO, vector(0, 0, 1));
        opPattern(context, id + "bpat", {
                "entities" : qCreatedBy(id + "bump", EntityType.BODY),
                "transforms" : [rotationAround(axis, 120 * degree), rotationAround(axis, 240 * degree)],
                "instanceNames" : ["b", "c"]
        });
        opBoolean(context, id + "bjoin", {
                "tools" : qUnion([qCreatedBy(id + "co", EntityType.BODY),
                                  qCreatedBy(id + "bump", EntityType.BODY),
                                  qCreatedBy(id + "bpat", EntityType.BODY)]),
                "operationType" : BooleanOperationType.UNION
        });
    });
