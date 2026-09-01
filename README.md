# inkpacking
Inkscape extension to create foldable boxes, with finger slots and different flaps, takes paper thickness into account

The extension was published by inkscapeforum.com member celso.junior in 2011 (see [this forum post](http://www.inkscapeforum.com/viewtopic.php?f=34&t=10880) for more details and a description by the original author). It was later updated to be compatible with Inkscape 0.91, and in 2026 was ported to the Python 3 / Inkscape 1.x extension API (the old `inkex.Effect` / `optparse` / `simplepath` API was removed in Inkscape 1.0).

This repository is intended to facilitate further development of the extension and to make it readily accessible. If you would like to contribute or take over maintenance, please contact github user Moini via this repository's [issue section](https://github.com/Moini/inkpacking/issues).

It is licenced as GPL version 2 or later.

## Requirements:

Inkscape 1.0 or later (uses the current Python 3 extension API). It will not work in Inkscape 0.92 or earlier.

## Installation:

Copy the files inkpacking.py and inkpacking.inx into the directory indicated in Edit -> Preferences -> System: User extensions, then restart Inkscape.

## Usage:

* Find the extension in Render -> InkPACKING...
* Enter values for the available options
* You can use the preview functionality (checkbox "Live Preview" at the bottom) to see how your changes affect the appearance of the folding box

The generated lines come in two styles, so the output can be sent straight to a laser cutter / plotter workflow that tells them apart: solid black lines are cuts, dashed blue lines are folds (creases). Both are also tagged with a `class` attribute (`inkpacking-cut` / `inkpacking-fold`) for tools that filter by class rather than by color.

## Development

`inkpacking.py` draws each panel/flap through a small set of shared helper methods on `BoxBuilder` (top and bottom ends are the same code mirrored by a sign, rather than duplicated), instead of one function per end/scheme combination.

`tests/run_variants.py` runs the extension against every top/bottom scheme, mirrored-flap and finger-slot combination and checks each produces valid SVG -- run it locally with `pip install inkex && python tests/run_variants.py`. It also runs in CI on every push/PR (`.github/workflows/smoke-test.yml`), which is the kind of check that would have caught this extension silently breaking under Inkscape 1.x in the first place.

## Screenshots:

![dialog_1](https://cloud.githubusercontent.com/assets/3240233/11562363/dce5b7be-99cd-11e5-92a9-1d16b1fce41f.png)

![dialog_2](https://cloud.githubusercontent.com/assets/3240233/11562361/dce2e14c-99cd-11e5-82c0-8acc4f65e899.png)

![dialog_3](https://cloud.githubusercontent.com/assets/3240233/11562362/dce4edde-99cd-11e5-8cdd-806a2dcd023a.png)

![dialog_4](https://cloud.githubusercontent.com/assets/3240233/11562359/dce083a2-99cd-11e5-908b-f5981203b923.png)

![dialog_5](https://cloud.githubusercontent.com/assets/3240233/11562358/dcc68150-99cd-11e5-8efb-aa75507702c7.png)

![examples](https://cloud.githubusercontent.com/assets/3240233/11562364/dce9b2d8-99cd-11e5-9e92-1f4305c8ff81.png)
