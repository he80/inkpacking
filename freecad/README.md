# InkPACKING FreeCAD tooling (early prototype)

Goal: pick a FEFCO code, get a real 3D fold preview, and export a DXF +
dimensioned technical drawing suitable for sending to a manufacturer --
something Inkscape (a flat 2D vector editor) can't do. Builds on top of
FreeCAD's own [SheetMetal workbench](https://github.com/shaise/FreeCAD_SheetMetal)
rather than writing a 3D-fold engine from scratch: SheetMetal WB already
provides panel-to-panel bending, an unfolder, and DXF export with cut/bend
lines on separate layers.

## Status: milestone 1 done

`prototype_body.py` folds the box body's 4 main panels (no flaps/tabs yet)
into a real 3D solid, driven by SheetMetal WB's `smBase`/`smBend` building
blocks, using our own pre-computed panel lengths rather than SheetMetal's
metal-specific K-factor bend-allowance math (cardboard creases sharply; it
doesn't stretch around a bend radius the way metal does -- see the
`LengthSpec="Leg"` + near-zero `crease_radius` in the script).

Verified (not just "ran without crashing"):
- Final envelope: 41.20 x 31.20 x 80.00 mm vs. expected 41.0 x 31.0 x 80.0
  mm (width+2*thickness x depth+2*thickness x height) -- the ~0.2mm
  overshoot is the crease radius rounding, as expected.
- Loop closure gap (does the 4th panel's far edge land back on the 1st
  panel's start edge): 0.695mm -- same order as the crease-radius/
  thickness effects above, confirming the four panels genuinely close into
  a box rather than spiraling or leaving a gap.
- Thin-wall volume: 5666 mm^3 vs. an expected ~5600 mm^3 (perimeter x
  height x thickness) -- consistent with a real thin-walled tube, not a
  degenerate/self-intersecting shape.

`prototype_body.FCStd` is the saved result -- open it directly in FreeCAD
to look at it.

## Running it

Requires FreeCAD 1.1+ with the SheetMetal workbench addon installed
(Tools > Addon Manager in the FreeCAD GUI, or it may already be present at
`<FreeCAD user data dir>/Mod/sheetmetal` -- the script's `SHEETMETAL_MOD`
constant points there and may need updating for your machine).

```
"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" prototype_body.py
```

(`freecadcmd` is FreeCAD's headless CLI -- no GUI needed to run or verify
this script.)

## Notes for whoever picks this up next

- Building the wall chain requires picking, after each bend, which face of
  the growing (fused) solid is the new free end to bend the *next* panel
  from. This turned out to be the hard part -- see the comments in
  `far_end_face()` for two real bugs hit and fixed along the way: (1) area-
  based face selection gets fooled by small bend-radius fillet / corner-
  relief sliver faces unless you also require the face to be planar and
  match the *expected* area (thickness x the box's constant height
  dimension); (2) comparing a raw corner point against a face's centroid
  (which sits at panel mid-height) via full 3D distance drowns out the
  X/Y signal you actually care about in an always-present ~height/2
  offset -- compare X/Y only, and match against the *expected* bend
  length rather than just picking "the farthest" candidate (the fused
  shape keeps every earlier wall's untouched far end around too, and
  those can be farther away than the genuinely new one once panel lengths
  differ).

## Next milestones (not started)

1. Extract the panel/fold-line data out of the Inkscape extension's
   `BoxBuilder` (`../inkpacking-master/inkpacking.py`) into a plain-Python
   module with no `inkex` dependency, so this script and the Inkscape
   extension share one source of truth instead of hand-copied dimensions.
2. Add the flaps/tabs (lock tab, dust flaps, tuck lid, etc.) on top of the
   4-panel body proven here.
3. Use SheetMetal WB's own Unfold command on the resulting solid to
   regenerate the flat pattern -- both as a correctness cross-check
   against the Inkscape extension's 2D output, and to get DXF/SVG export
   (with cut vs. bend lines already separated) for free.
4. A TechDraw page: dimensioned view, title block, labeling/print
   instructions.
5. Only once 1-4 are solid: wrap this as an installable FreeCAD workbench
   (toolbar, task panel, FEFCO code picker) instead of a script.
