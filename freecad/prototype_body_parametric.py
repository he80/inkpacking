"""Milestone 2: same folded box body as prototype_body.py, but every
dimension is now driven live by a Spreadsheet ("Parameters") through
FreeCAD's expression engine, instead of being baked in as Python floats.
Editing a cell and recomputing updates the whole folded model -- this is
the pattern the eventual multi-style app builds on: one shared parameter
schema, expressions everywhere, nothing hand-typed into geometry.

Run with:
    "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" prototype_body_parametric.py
"""
import sys

SHEETMETAL_MOD = r"C:\Users\homej\AppData\Roaming\FreeCAD\v1-1\Mod\sheetmetal"
sys.path.insert(0, SHEETMETAL_MOD)

import FreeCAD as App
import Part
import Sketcher

import SheetMetalBaseCmd
import SheetMetalCmd

PARAMS = {
    "Width": 40.0,
    "Depth": 30.0,
    "Height": 80.0,
    "Thickness": 0.5,
    "CreaseRadius": 0.1,
}


def make_parameters_sheet(doc):
    sheet = doc.addObject("Spreadsheet::Sheet", "Parameters")
    for row, (name, value) in enumerate(PARAMS.items(), start=1):
        sheet.set(f"A{row}", name)
        sheet.set(f"B{row}", str(value))
        sheet.setAlias(f"B{row}", name)
    doc.recompute()
    return sheet


def far_end_face(shape, near_point, expected_area, expected_length, tol=0.35):
    """See prototype_body.py for why this looks the way it does (planar +
    expected-area filtering to dodge bend-fillet/relief slivers; X/Y-only,
    expected-length matching instead of "farthest" to dodge the mid-height
    centroid offset and other walls' untouched far ends)."""
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

    best_name, best_face, best_err = None, None, None
    for n, f in candidates:
        err = abs(xy_dist(f.CenterOfMass) - expected_length)
        if best_err is None or err < best_err:
            best_name, best_face, best_err = n, f, err
    return best_name, best_face.CenterOfMass


def build(doc, sheet):
    thk = PARAMS["Thickness"]
    boxH = PARAMS["Height"]
    end_cap_area = thk * boxH

    # --- seed sketch: a vertical line (length Height) whose own length is
    # bound to the spreadsheet via a Distance constraint's expression. ---
    sketch1 = doc.addObject("Sketcher::SketchObject", "Wall1Sketch")
    sketch1.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 1, 0), 90))
    sketch1.addGeometry(Part.LineSegment(App.Vector(0, 0, 0), App.Vector(boxH, 0, 0)), False)
    con_idx = sketch1.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, boxH))
    sketch1.setExpression(f"Constraints[{con_idx}]", "Parameters.Height")
    doc.recompute()

    wall1 = doc.addObject("Part::FeaturePython", "Wall1")
    SheetMetalBaseCmd.SMBaseBend(wall1, sketch1)
    wall1.Length = PARAMS["Width"]
    wall1.Thickness = thk
    wall1.Radius = PARAMS["CreaseRadius"]
    wall1.setExpression("Length", "Parameters.Width")
    wall1.setExpression("Thickness", "Parameters.Thickness")
    wall1.setExpression("Radius", "Parameters.CreaseRadius")
    doc.recompute()

    walls = [wall1]
    # (cell alias, numeric value) for each following panel, D/W/D
    steps = [("Depth", PARAMS["Depth"]), ("Width", PARAMS["Width"]), ("Depth", PARAMS["Depth"])]
    prev = wall1
    near_point = App.Vector(0, 0, 0)
    prev_length = PARAMS["Width"]

    for i, (alias, length) in enumerate(steps, start=2):
        face_name, far_point = far_end_face(prev.Shape, near_point, end_cap_area, prev_length)

        newwall = doc.addObject("Part::FeaturePython", f"Wall{i}")
        SheetMetalCmd.SMBendWall(newwall, prev, [face_name])
        newwall.length = length
        newwall.angle = 90.0
        newwall.radius = PARAMS["CreaseRadius"]
        newwall.LengthSpec = "Leg"
        newwall.setExpression("length", f"Parameters.{alias}")
        newwall.setExpression("radius", "Parameters.CreaseRadius")
        doc.recompute()
        walls.append(newwall)
        prev = newwall
        near_point = far_point
        prev_length = length

    return walls


def verify(walls, expected_w, expected_d, expected_h, thk, label):
    final = walls[-1]
    bb = final.Shape.BoundBox
    exp_env = (expected_w + 2 * thk, expected_d + 2 * thk, expected_h)
    exp_vol = 2 * (expected_w + expected_d) * expected_h * thk
    print(f"[{label}] envelope: {bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f}  "
          f"(expected ~{exp_env[0]:.1f} x {exp_env[1]:.1f} x {exp_env[2]:.1f})")
    print(f"[{label}] volume: {final.Shape.Volume:.1f}  (expected ~{exp_vol:.1f})")
    env_ok = (abs(bb.XLength - exp_env[0]) < 1.0
              and abs(bb.YLength - exp_env[1]) < 1.0
              and abs(bb.ZLength - exp_env[2]) < 0.01)
    vol_ok = abs(final.Shape.Volume - exp_vol) / exp_vol < 0.05
    print(f"[{label}] envelope OK: {env_ok}, volume OK: {vol_ok}")
    return env_ok and vol_ok


def main():
    doc = App.newDocument("InkpackingBodyParametric")
    sheet = make_parameters_sheet(doc)
    walls = build(doc, sheet)

    ok1 = verify(walls, PARAMS["Width"], PARAMS["Depth"], PARAMS["Height"], PARAMS["Thickness"],
                 "initial (40x30x80)")

    # --- Now prove it's actually LIVE: change the spreadsheet, recompute,
    # and check the folded solid follows without touching any geometry code. ---
    new_w, new_d, new_h = 60.0, 25.0, 100.0
    sheet.set("B1", str(new_w))
    sheet.set("B2", str(new_d))
    sheet.set("B3", str(new_h))
    doc.recompute()
    ok2 = verify(walls, new_w, new_d, new_h, PARAMS["Thickness"], "after spreadsheet edit (60x25x100)")

    print("\nMILESTONE 2 RESULT:", "PASS" if (ok1 and ok2) else "FAIL")
    doc.saveAs(r"c:\Users\homej\Documents\tools\inkpacking-master\freecad\prototype_body_parametric.FCStd")
    print("Saved.")


main()
