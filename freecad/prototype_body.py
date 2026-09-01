"""Milestone-1 prototype: fold the 4 main body panels of an InkPACKING box
(width/depth/height, no flaps yet) into a real 3D shape using the SheetMetal
workbench's own Base/Bend building blocks, run headlessly via freecadcmd.

Run with:
    "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" prototype_body.py

Orientation: boxH is the constant dimension (the seed sketch line, drawn
vertically) and each wall grows along a fresh direction as it's added, by
boxW/boxD/boxW/boxD in turn -- this matches a real box net, where the fold
lines between the four side panels run along the box's height and Only the
W/D widths alternate as you unroll around it.
"""
import sys

SHEETMETAL_MOD = r"C:\Users\homej\AppData\Roaming\FreeCAD\v1-1\Mod\sheetmetal"
sys.path.insert(0, SHEETMETAL_MOD)

import FreeCAD as App
import Part

import SheetMetalBaseCmd
import SheetMetalCmd

# Same default dimensions as the Inkscape extension's QA "default" variant.
boxW, boxD, boxH = 40.0, 30.0, 80.0
thk = 0.5
crease_radius = 0.1  # cardboard creases sharply -- a near-zero radius, not a metal bend radius


def far_end_face(shape, near_point, expected_area, expected_length, tol=0.35):
    """Pick the face at the free (far) end of a wall solid: the planar face
    whose area is close to `expected_area` (thickness x boxH -- constant
    across every wall in this box, so it uniquely identifies the true end
    caps and excludes bend-radius fillets / corner-relief slivers), among
    those picking the one whose *height-projected* (X/Y only -- Z/height
    never changes across this whole tube, and comparing raw 3D distance to
    a face's centroid, which sits at mid-height, drowns out the X/Y signal
    with an always-present ~boxH/2 offset) distance from `near_point` is
    closest to `expected_length` -- not just "farthest", since the fused
    shape keeps every previous wall's untouched far end around too, and
    those can be farther away than the genuinely new one once walls vary
    in length."""
    faces = [(f"Face{i+1}", shape.getElement(f"Face{i+1}")) for i in range(len(shape.Faces))]
    candidates = [
        (n, f) for n, f in faces
        if f.Surface.TypeId == "Part::GeomPlane"
        and abs(f.Area - expected_area) <= expected_area * tol
    ]
    if not candidates:
        raise RuntimeError(f"no end-cap face found near area {expected_area}; "
                            f"areas were {[(n, round(f.Area, 3)) for n, f in faces]}")

    def xy_dist(pt):
        return ((pt.x - near_point.x) ** 2 + (pt.y - near_point.y) ** 2) ** 0.5

    print("    candidates:", [(n, f.CenterOfMass, round(xy_dist(f.CenterOfMass), 2))
                               for n, f in candidates])
    best_name, best_face, best_err = None, None, None
    for n, f in candidates:
        err = abs(xy_dist(f.CenterOfMass) - expected_length)
        if best_err is None or err < best_err:
            best_name, best_face, best_err = n, f, err
    return best_name, best_face.CenterOfMass


def main():
    doc = App.newDocument("InkpackingBody")
    end_cap_area = thk * boxH  # constant across all 4 walls

    # --- Wall 1: seed sketch is a vertical line (length boxH) in a plane
    # rotated so its normal points along world X -- so smBase's extrusion
    # (along that normal) grows the first wall along X by boxW. ---
    sketch1 = doc.addObject("Sketcher::SketchObject", "Wall1Sketch")
    sketch1.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 1, 0), 90))
    sketch1.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(boxH, 0, 0)), False)
    doc.recompute()

    wall1 = doc.addObject("Part::FeaturePython", "Wall1")
    SheetMetalBaseCmd.SMBaseBend(wall1, sketch1)
    wall1.Length = boxW
    wall1.Thickness = thk
    wall1.Radius = crease_radius
    doc.recompute()
    print("Wall1 faces:", len(wall1.Shape.Faces), "valid:", wall1.Shape.isValid(),
          "bbox:", wall1.Shape.BoundBox)

    walls = [wall1]
    lengths = [boxD, boxW, boxD]  # D, W, D panels following the first W panel
    prev = wall1
    near_point = App.Vector(0, 0, 0)  # Wall1's sketch started here
    prev_length = boxW  # Wall1's own length, needed to find *its* far end below

    for i, length in enumerate(lengths, start=2):
        face_name, far_point = far_end_face(prev.Shape, near_point, end_cap_area, prev_length)
        print(f"  step {i}: bending from {face_name} on {prev.Name}, far point {far_point}")

        newwall = doc.addObject("Part::FeaturePython", f"Wall{i}")
        SheetMetalCmd.SMBendWall(newwall, prev, [face_name])
        newwall.length = length
        newwall.angle = 90.0
        newwall.radius = crease_radius
        newwall.LengthSpec = "Leg"
        doc.recompute()
        print(f"Wall{i} faces:", len(newwall.Shape.Faces), "valid:", newwall.Shape.isValid(),
              "bbox:", newwall.Shape.BoundBox)
        walls.append(newwall)
        prev = newwall
        near_point = far_point
        prev_length = length

    final = walls[-1]
    bb = final.Shape.BoundBox
    print("\nFinal wall shape bounding box:", bb)
    print("Final wall shape volume:", final.Shape.Volume)
    expected_volume = 2 * (boxW + boxD) * boxH * thk
    print(f"Expected thin-wall volume roughly: {expected_volume:.1f} "
          f"(perimeter x height x thickness)")
    print(f"Expected outer envelope roughly: {boxW + 2*thk:.1f} x {boxD + 2*thk:.1f} x {boxH:.1f}")
    print(f"Actual envelope: {bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f}")

    # near_point right now is Wall4's own *start* (where it hinges off Wall3);
    # find Wall4's *far* end the same way, which is what should close the loop.
    _, wall4_far = far_end_face(final.Shape, near_point, end_cap_area, prev_length)
    closure_gap = ((wall4_far.x - 0) ** 2 + (wall4_far.y - 0) ** 2) ** 0.5
    print(f"Loop closure gap (Wall4 far end vs Wall1 start, XY only): {closure_gap:.3f} "
          f"-- should be ~0 for a properly closed box")
    doc.saveAs(r"c:\Users\homej\Documents\tools\inkpacking-master\freecad\prototype_body.FCStd")
    print("Saved.")


main()
