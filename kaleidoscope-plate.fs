FeatureScript 3044;
import(path : "onshape/std/common.fs", version : "3044.0");

/* ─────────────────────────────────────────────────────────────────────────
   Tapered kaleidoscope — SIDE PLATE.  Print three.

   One part, sitting on the XY plane, outer face down.

   The mirror rests straight on the plate's inner face, so that face is one
   mirror thickness outboard of the optical plane and the plate is a good deal
   wider than its mirror — 30.90 mm inner face at the narrow end against a
   25.40 mm optical face.

   MITRE: 30° off the plate's plane at both long edges, which is what closes
   three plates into a 60° corner.  The outer face runs sqrt(3)*w past the
   inner one, so the feather edge is the tube's OUTSIDE corner — truncating it
   costs nothing optically and leaves a small V-notch down each outer corner
   that the collar bridges.  Untruncated it goes to zero thickness and will
   not print.

   The mirror may overlap past the optical vertex by 1.155 * mirrorThickness
   = 1.83 mm before it fouls the neighbouring plate.  The blanks carry 1.00.

   DETENT: pocket in the outer face near the narrow end, taking the inward
   bump on the small cap.  Insert the plates one at a time — three cannot all
   flex past their bumps at once, since the closed mitres resist it.

   PRINTING: cross-section narrows upward, so the mitres lean inward rather
   than overhang.  No supports.  The mirror seat is a top surface with nothing
   between it and the mirror, so turn ironing on.
   ───────────────────────────────────────────────────────────────────────── */

function polySketch(context is Context, skId is Id, pl is Plane, pts is array)
{
    const s = newSketchOnPlane(context, skId, { "sketchPlane" : pl });
    for (var k = 0; k < size(pts); k += 1)
        skLineSegment(s, "e" ~ k, { "start" : pts[k], "end" : pts[(k + 1) % size(pts)] });
    skSolve(s);
}

// Cross-section, face at the bottom, outward -Y.
function plateProfile(side, t, w, land) returns array
{
    const S3 = sqrt(3);
    const rp = side / (2 * S3) + t;      // inner face: the mirror seat
    const ro = rp + w;                   // outer face
    const xi = S3 * rp;
    const xo = S3 * (ro - land);         // mitre tip truncated
    return [vector(-xi, -rp), vector(xi, -rp),
            vector(xo, -ro + land), vector(xo, -ro),
            vector(-xo, -ro), vector(-xo, -ro + land)];
}

annotation { "Feature Type Name" : "Kaleidoscope side plate" }
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

        annotation { "Name" : "Bump width" }
        isLength(definition.bumpWidth, { (millimeter) : [2.0, 6.0, 30.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump length along axis" }
        isLength(definition.bumpLength, { (millimeter) : [1.0, 3.0, 20.0] } as LengthBoundSpec);

        annotation { "Name" : "Bump height" }
        isLength(definition.bumpHeight, { (millimeter) : [0.2, 0.8, 3.0] } as LengthBoundSpec);

        annotation { "Name" : "Detent clearance (generous for v1)" }
        isLength(definition.detentClear, { (millimeter) : [0.1, 1.0, 4.0] } as LengthBoundSpec);
    }
    {
        const S3 = sqrt(3);
        const t = definition.mirrorThickness;
        const w = definition.plateThickness;
        const land = definition.miterLand;
        const L = definition.tubeLength;

        if (land >= w)
            throw regenError("Mitre truncation must be less than the plate thickness.");

        const m = (definition.wideSide - definition.narrowSide) / (2 * S3 * L);
        const roN = definition.narrowSide / (2 * S3) + t + w;

        polySketch(context, id + "pk0",
                plane(vector(0, 0, 0) * millimeter, vector(0, 0, 1), vector(1, 0, 0)),
                plateProfile(definition.narrowSide, t, w, land));
        polySketch(context, id + "pk1",
                plane(vector(0, 0, 1) * L, vector(0, 0, 1), vector(1, 0, 0)),
                plateProfile(definition.wideSide, t, w, land));
        opLoft(context, id + "plate", {
                "profileSubqueries" : [qSketchRegion(id + "pk0", true), qSketchRegion(id + "pk1", true)]
        });
        opDeleteBodies(context, id + "pkd", {
                "entities" : qUnion([qCreatedBy(id + "pk0", EntityType.BODY),
                                     qCreatedBy(id + "pk1", EntityType.BODY)])
        });

        // detent pocket, cut on a plane parallel to the outer face
        const nOut = normalize(vector(0, -1, -m));
        const pOut = plane(vector(0 * millimeter, -roN, 0 * millimeter) + 1 * millimeter * nOut,
                           nOut, vector(1, 0, 0));
        const vW = definition.bumpWidth + 2 * definition.detentClear;
        const vL = definition.bumpLength + 2 * definition.detentClear;
        const vD = definition.bumpHeight + definition.detentClear;
        const along = definition.detentZ * sqrt(1 + m * m);
        const vs = newSketchOnPlane(context, id + "vsk", { "sketchPlane" : pOut });
        skRectangle(vs, "r", {
                "firstCorner" : vector(-vW / 2, along - vL / 2),
                "secondCorner" : vector(vW / 2, along + vL / 2)
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
        opDeleteBodies(context, id + "vskd", { "entities" : qCreatedBy(id + "vsk", EntityType.BODY) });

        // lay the outer face on XY, material above, centred
        const q = qCreatedBy(id + "plate", EntityType.BODY);
        opTransform(context, id + "rot", {
                "bodies" : q,
                "transform" : rotationAround(line(vector(0, 0, 0) * millimeter, vector(1, 0, 0)),
                                             atan(1 / m))
        });
        const bb = evBox3d(context, { "topology" : q, "tight" : true });
        const mid = (bb.minCorner + bb.maxCorner) / 2;
        opTransform(context, id + "seat", {
                "bodies" : q,
                "transform" : transform(vector(-mid[0], -mid[1], -bb.minCorner[2]))
        });
    });
