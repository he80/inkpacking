#!/usr/bin/env python3
"""
Copyleft ( ) 2009 Celso Junior celsojr2008 at gmail dot com>,
             2015 Maren Hachmann <marenhachmann@yahoo.com> (updated for Inkscape 0.91)
             2026 updated for Inkscape 1.x / Python 3, refactored, cut/fold styling,
                  input validation (see README for details)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

__version__ = "0.13"

import inkex
from math import *
from lxml import etree


def format_path(path):
    """Turns a list of [command, [params...]] pairs into an SVG path 'd'
    string (a small re-implementation of the old simplepath.formatPath()
    helper, which was removed from inkex)."""
    parts = []
    for cmd, params in path:
        parts.append(cmd)
        for p in params:
            if isinstance(p, float):
                p = round(p, 6)
                if p == int(p):
                    p = int(p)
            parts.append(str(p))
    return " ".join(parts)


# Two visually distinct line styles so the output can be used directly by a
# laser cutter / plotter workflow that tells cut lines from fold (score)
# lines apart: solid black for cuts, dashed blue for folds. Both are also
# tagged with a CSS class of the same name for tools that filter by class
# rather than by color.
CUT_STYLE = str(inkex.Style({'stroke': '#000000', 'fill': 'none'}))
FOLD_STYLE = str(inkex.Style({'stroke': '#0066ff', 'fill': 'none', 'stroke-dasharray': '2,1.5'}))


class BoxBuilder:
    """Draws one InkPACKING box net into an SVG group. Holds the geometry
    shared by every panel/flap, and the top/bottom drawing is written once
    and mirrored (sign=+1 for the bottom, sign=-1 for the top) rather than
    duplicated, since the two are exact mirror images of each other."""

    def __init__(self, g, box_id, boxW, boxD, boxH, boxL, thck, lockrr, lockroff, roto):
        self.g = g
        self.box_id = box_id
        self.boxW = boxW
        self.boxD = boxD
        self.boxH = boxH
        self.boxL = boxL
        self.thck = thck
        self.thck2 = thck / 2
        self.lockrr = lockrr
        self.lockroff = lockroff
        self.roto = roto
        # panel x-coordinates, left to right: W | D | W | D(-thck)
        self.x0 = 0
        self.xW = boxW
        self.xWD = boxW + boxD
        self.xWDW = boxW + boxD + boxW
        self.xEnd = boxW + boxD + boxW + boxD - thck

    def add(self, suffix, path, cut=True):
        if not path:
            return
        style = CUT_STYLE if cut else FOLD_STYLE
        css_class = 'inkpacking-cut' if cut else 'inkpacking-fold'
        atts = {
            'style': style,
            'class': css_class,
            'id': f'{self.box_id}-{suffix}',
            'd': format_path(path),
        }
        etree.SubElement(self.g, inkex.addNS('path', 'svg'), atts)

    # ------------------------------------------------------------------
    # Body + side glue flap
    # ------------------------------------------------------------------

    def draw_body(self, gfmirror):
        """The four vertical panel-division lines. Three of them are always
        fold lines (creases between adjacent panels); the fourth (whichever
        edge the side glue flap is NOT attached to) is the true cut edge of
        the blank."""
        xs = [self.x0, self.xW, self.xWD, self.xWDW, self.xEnd]
        outer_cut_x = xs[0] if gfmirror else xs[-1]
        fold_xs = [x for x in xs if x != outer_cut_x]

        self.add('body', [['M', [outer_cut_x, 0]], ['L', [outer_cut_x, self.boxH]]], cut=True)

        fold_path = []
        for x in fold_xs:
            fold_path += [['M', [x, 0]], ['L', [x, self.boxH]]]
        self.add('body-fold', fold_path, cut=False)

    def draw_side_glueflap(self, gfmirror, gflapsize, gflapoffy):
        """The manufacturer's side joint flap. It only needs to draw its 3
        free (cut) sides -- the 4th side, where it hinges onto the body, is
        already covered by the body's fold line at that same edge."""
        boxH = self.boxH
        if not gfmirror:
            path = [
                ['M', [0, 0]],
                ['L', [gflapsize * -1, gflapoffy]],
                ['L', [gflapsize * -1, boxH - gflapoffy]],
                ['L', [0, boxH]],
            ]
        else:
            x = self.xEnd
            path = [
                ['M', [x, 0]],
                ['L', [x + gflapsize, gflapoffy]],
                ['L', [x + gflapsize, boxH - gflapoffy]],
                ['L', [x, boxH]],
            ]
        self.add('sideglueflap', path, cut=True)

    # ------------------------------------------------------------------
    # Top / bottom ends -- shared, mirrored by `sign` (+1 bottom, -1 top)
    # ------------------------------------------------------------------

    def draw_open_edge(self, suffix, ybase, sign, fingergrepa, fingergrepb, fingergrepr):
        """'No top' / 'no bottom': just the flat (optionally finger-holed)
        outer edge of the blank. Entirely a cut edge."""
        boxW, boxD, thck = self.boxW, self.boxD, self.thck
        sweep = 1 if sign > 0 else 0

        def hole(x_center, half_width):
            return [
                ['L', [x_center - half_width, ybase]],
                ['A', [fingergrepr, fingergrepr, 0, 1, sweep, x_center + half_width, ybase]],
            ]

        path = [['M', [0, ybase]]]
        if fingergrepa:
            path += hole(boxW / 2, fingergrepr)
            path += [['L', [boxW, ybase]]]
        else:
            path += [['L', [boxW, ybase]]]

        path += [['L', [boxW + boxD, ybase]]] if not fingergrepb else []
        if fingergrepb:
            path += hole(boxW + boxD / 2, fingergrepr)
        path += [['L', [boxW + boxD + boxW, ybase]]]

        if fingergrepb:
            path += hole(boxW + boxD + boxW + boxD / 2 - thck / 2, fingergrepr)
            path += [['L', [boxW + boxD + boxW + boxD - thck, ybase]]]
        else:
            path += [['L', [boxW + boxD + boxW + boxD - thck, ybase]]]

        self.add(suffix, path, cut=True)

    def draw_cut_edge(self, suffix, ybase, sign, inicut, fingergrepa, fingergrepr):
        """The plain (non-flap) panel edge opposite a lock-flap head, used
        with the flat/rounded lock-flap and hotmelt end schemes. Entirely a
        cut edge."""
        boxW = self.boxW
        sweep = 1 if sign > 0 else 0
        if fingergrepa:
            path = [
                ['M', [inicut, ybase]],
                ['l', [boxW / 2 - fingergrepr, 0]],
                ['a', [fingergrepr, fingergrepr, 0, 0, sweep, fingergrepr * 2, 0]],
                ['l', [boxW / 2 - fingergrepr, 0]],
            ]
        else:
            path = [['M', [inicut, ybase]], ['l', [boxW, 0]]]
        self.add(suffix, path, cut=True)

    def draw_lockflap_end(self, suffix, ybase, sign, scheme, fal, rounded):
        """Flat/rounded lock-flap end (schemes 'fwlf' / 'rwlf'). Draws the
        flap's cut silhouette (with its locking tab) plus the single
        thickness-compensated fold line that hinges it to the body."""
        boxW, boxD, boxL, thck = self.boxW, self.boxD, self.boxL, self.thck
        lockrr, lockroff, roto = self.lockrr, self.lockroff, self.roto
        sweep = 0 if sign > 0 else 1

        desloc = 0 if fal else boxW + boxD

        cut = [
            ['M', [desloc, ybase]],
            ['l', [0, boxD * sign]],
            ['l', [6, 0]],
            ['l', [0, thck * -2 * sign]],
            ['m', [0, thck * sign]],
            ['l', [boxW - 12, 0]],
            ['m', [0, thck * -1 * sign]],
            ['l', [0, thck * 2 * sign]],
            ['l', [6, 0]],
            ['l', [0, boxD * -1 * sign]],
            ['M', [desloc, ybase]],
            ['m', [0, boxD * sign]],
            ['m', [thck, 0]],
        ]
        if rounded:
            cut += [
                ['a', [lockrr, lockrr, 0, 0, sweep, lockroff, (boxL - thck) * sign]],
                ['l', [boxW - lockroff - lockroff - thck - thck, 0]],
                ['a', [lockrr, lockrr, roto, 0, sweep, lockroff, (boxL - thck) * -1 * sign]],
            ]
        else:
            cut += [
                ['l', [lockroff, (boxL - thck) * sign]],
                ['l', [boxW - lockroff - lockroff - thck - thck, 0]],
                ['l', [lockroff, (boxL - thck) * -1 * sign]],
            ]
        self.add(suffix, cut, cut=True)

        fold = [
            ['M', [desloc, ybase + thck * sign]],
            ['l', [boxW, 0]],
        ]
        self.add(suffix + '-fold', fold, cut=False)

    def draw_hotmelt_end(self, suffix, ybase, sign, fal, hotmeltp):
        """HotMelt end (scheme 'fwnf'): a full-height flap on one side, a
        partial-height (hotmeltp) flap on the other, each hinging on the
        body edge, plus one thickness-compensated fold line per flap."""
        boxW, boxD, thck = self.boxW, self.boxD, self.thck
        full = boxD * sign
        partial = boxD * sign * hotmeltp
        # fal picks which side gets the full-height flap and which gets the
        # partial (hotmeltp) one -- mirrors the original tfal/bfal branches.
        left_h, right_h = (full, partial) if fal else (partial, full)

        cut = [
            ['M', [0, ybase]],
            ['L', [0, ybase + left_h]],
            ['L', [boxW, ybase + left_h]],
            ['L', [boxW, ybase]],
            ['M', [boxW + boxD, ybase]],
            ['L', [boxW + boxD, ybase + right_h]],
            ['L', [boxW + boxD + boxW, ybase + right_h]],
            ['L', [boxW + boxD + boxW, ybase]],
        ]
        self.add(suffix, cut, cut=True)

        fold = [
            ['M', [0, ybase + thck * sign]],
            ['L', [boxW, ybase + thck * sign]],
            ['M', [boxW + boxD, ybase + thck * sign]],
            ['L', [boxW + boxD + boxW, ybase + thck * sign]],
        ]
        self.add(suffix + '-fold', fold, cut=False)

    def draw_dust_flaps(self, suffix, ybase, sign, scheme, fal, gp):
        """The small corner dust flaps that fold up/down from the depth (D)
        panels at the top and bottom of the box, regardless of end scheme
        (as long as that end isn't 'open'). `gp` is a dict with the glue
        flap shape parameters (inner/outer offset, 45deg offset, computed
        diagonal length)."""
        boxW, boxD, boxL, thck, thck2 = self.boxW, self.boxD, self.boxL, self.thck, self.thck2
        desclock = 0 if scheme == 'fwnf' else thck

        inoff, in45, indesl = gp['inoff'], gp['in45'], gp['indesl']
        ouoff, ou45, oudesl = gp['ouoff'], gp['ou45'], gp['oudesl']

        def dy(base):
            return sign * (base - thck2)

        raw = (boxD + boxL) / 2

        # `fal` doesn't just flip a sign here (unlike top/bottom): it swaps
        # which whole corner gets the inner-vs-outer flap shape, so (unlike
        # the rest of this class) the two branches are transcribed directly
        # rather than derived from one shared shape.
        if fal:
            cut = [
                ['M', [boxW, ybase]],
                ['l', [0, inoff * sign]],
                ['l', [in45, in45 * sign]],
                ['l', [indesl, dy(raw - inoff - in45)]],
                ['M', [boxW + boxD, ybase]],
                ['l', [desclock * -1, 0]],
                ['l', [0, ouoff * sign]],
                ['l', [ou45 * -1, ou45 * sign]],
                ['l', [oudesl * -1, dy(raw - ouoff - ou45)]],
                ['l', [(boxD - indesl - oudesl - in45 - ou45 - desclock) * -1, 0]],
            ]
            fold1 = [['M', [boxW, ybase]], ['l', [boxD - desclock, 0]]]

            cut2 = [
                ['M', [boxW + boxW + boxD + boxD - thck, ybase]],
                ['l', [0, inoff * sign]],
                ['l', [in45 * -1, in45 * sign]],
                ['l', [indesl * -1, dy(raw - inoff - in45)]],
                ['M', [boxW + boxD + boxW, ybase]],
                ['l', [desclock, 0]],
                ['l', [0, ouoff * sign]],
                ['l', [ou45, ou45 * sign]],
                ['l', [oudesl, dy(raw - ouoff - ou45)]],
                ['l', [(boxD - indesl - oudesl - in45 - ou45 - desclock - thck), 0]],
            ]
            fold2 = [['M', [boxW + boxD + boxW + desclock, ybase]], ['l', [boxD - thck - desclock, 0]]]
        else:
            cut = [
                ['M', [boxW + boxD, ybase]],
                ['l', [0, inoff * sign]],
                ['l', [in45 * -1, in45 * sign]],
                ['l', [indesl * -1, dy(raw - inoff - in45)]],
                ['M', [boxW, ybase]],
                ['l', [desclock, 0]],
                ['l', [0, ouoff * sign]],
                ['l', [ou45, ou45 * sign]],
                ['l', [oudesl, dy(raw - ouoff - ou45)]],
                ['l', [(boxD - indesl - oudesl - in45 - ou45 - desclock), 0]],
            ]
            fold1 = [['M', [boxW + desclock, ybase]], ['l', [boxD - desclock, 0]]]

            cut2 = [
                ['M', [boxW + boxD + boxW, ybase]],
                ['l', [0, inoff * sign]],
                ['l', [in45, in45 * sign]],
                ['l', [indesl, dy(raw - inoff - in45)]],
                ['M', [boxW + boxD + boxW + boxD - thck, ybase]],
                ['l', [desclock * -1, 0]],
                ['l', [0, ouoff * sign]],
                ['l', [ou45 * -1, ou45 * sign]],
                ['l', [oudesl * -1, dy(raw - ouoff - ou45)]],
                ['l', [(boxD - indesl - oudesl - in45 - ou45 - desclock - thck) * -1, 0]],
            ]
            fold2 = [['M', [boxW + boxD + boxW, ybase]], ['l', [boxD - thck - desclock, 0]]]

        self.add(suffix, cut + cut2, cut=True)
        self.add(suffix + '-fold', fold1 + fold2, cut=False)


class InkPacking(inkex.EffectExtension):

    def add_arguments(self, pars):
        pars.add_argument("--width", type=float, dest="width", default=10.0)
        pars.add_argument("--height", type=float, dest="height", default=15.0)
        pars.add_argument("--depth", type=float, dest="depth", default=3.0)
        pars.add_argument("--unit", type=str, dest="unit", default="mm")
        pars.add_argument("--topscheme", type=str, dest="topscheme", default="rwlf")
        pars.add_argument("--botscheme", type=str, dest="botscheme", default="rwlf")
        pars.add_argument("--paper-thickness", type=float, dest="thickness", default=0.5)
        pars.add_argument("-t", "--tab-proportion", type=float, dest="tabProportion", default=14, help="Inner tab propotion for upper tab")
        pars.add_argument("-r", "--lockroundradius", type=float, dest="lockroundradius", default=18, help="Lock Radius")
        pars.add_argument("-c", "--clueflapsize", type=float, dest="clueflapsize", default=13, help="Clue Flap Size")
        pars.add_argument("-a", "--clueflapangle", type=float, dest="clueflapangle", default=12, help="Clue Flap Angle")
        pars.add_argument("--clueflapside", type=inkex.Boolean, dest="clueflapside", default=False)
        pars.add_argument("--pages", type=str, dest="page", default="page1")
        pars.add_argument("--dustpages", type=str, dest="dustpage", default="page1")
        pars.add_argument("--about", type=str, dest="about", default="")
        pars.add_argument("--tfal", type=inkex.Boolean, dest="tfal", default=False)
        pars.add_argument("--bfal", type=inkex.Boolean, dest="bfal", default=False)
        pars.add_argument("--hotmeltprop", type=float, dest="hotmeltprop", default=0.6)
        pars.add_argument("--fingergrepa", type=inkex.Boolean, dest="fingergrepa", default=False)
        pars.add_argument("--fingergrepb", type=inkex.Boolean, dest="fingergrepb", default=False)
        pars.add_argument("--fingergrepr", type=float, dest="fingergrepr", default=5)
        pars.add_argument("--usetop", type=inkex.Boolean, dest="usetop", default=False)
        pars.add_argument("--glueflapinoff", type=float, dest="glueflapinoff", default=0)
        pars.add_argument("--glueflapin45", type=float, dest="glueflapin45", default=2)
        pars.add_argument("--glueflapinang", type=float, dest="glueflapinang", default=7)
        pars.add_argument("--glueflapouoff", type=float, dest="glueflapouoff", default=0)
        pars.add_argument("--glueflapou45", type=float, dest="glueflapou45", default=3)
        pars.add_argument("--glueflapouang", type=float, dest="glueflapouang", default=12)
        pars.add_argument("--bglueflapinoff", type=float, dest="bglueflapinoff", default=0)
        pars.add_argument("--bglueflapin45", type=float, dest="bglueflapin45", default=2)
        pars.add_argument("--bglueflapinang", type=float, dest="bglueflapinang", default=7)
        pars.add_argument("--bglueflapouoff", type=float, dest="bglueflapouoff", default=0)
        pars.add_argument("--bglueflapou45", type=float, dest="bglueflapou45", default=3)
        pars.add_argument("--bglueflapouang", type=float, dest="bglueflapouang", default=12)
        pars.add_argument("--roto", type=float, dest="roto", default=0)

    def validate(self, boxW, boxD, boxH, boxL, thck, lockrr, fingergrepr,
                 fingergrepa, fingergrepb, clueflapangle):
        """Collect every geometrically-invalid parameter combination and
        report them all at once, instead of letting the math blow up deep
        inside path generation (asin() domain errors, negative segment
        lengths, etc.) with a confusing traceback."""
        problems = []
        if thck <= 0:
            problems.append("Paper Thick Discount must be greater than 0.")
        if boxL <= thck:
            problems.append("Lock Flap Size must be greater than the Paper Thick Discount.")
        elif lockrr <= 0 or (boxL - thck) > lockrr:
            problems.append(
                "Lock Flap Radius is too small for the current Lock Flap Size / "
                "Paper Thick Discount -- increase the radius or reduce the flap size."
            )
        if boxW <= 12 + 2 * thck:
            problems.append("Width (A) is too small for the lock/dust flap cutouts -- increase it.")
        if fingergrepa and fingergrepr * 2 >= boxW:
            problems.append("Finger Slot Radius is too large for Width (A).")
        if fingergrepb and fingergrepr * 2 >= boxD:
            problems.append("Finger Slot Radius is too large for Depth (B).")
        if not (0 < clueflapangle < 90):
            problems.append("Side Flap Angle must be between 0 and 90 degrees.")
        if boxW <= 0 or boxD <= 0 or boxH <= 0:
            problems.append("Width, Depth and Height must all be greater than 0.")
        if problems:
            raise inkex.AbortExtension("Cannot generate this box:\n- " + "\n- ".join(problems))

    def effect(self):
        opt = self.options
        unit = opt.unit

        def uu(value):
            return self.svg.unittouu(str(value) + unit)

        boxW = uu(opt.width)
        boxH = uu(opt.height)
        boxD = uu(opt.depth)
        boxL = uu(opt.tabProportion)
        thck = uu(opt.thickness)
        fingergrepr = uu(opt.fingergrepr)
        roto = opt.roto

        gflapsize = uu(opt.clueflapsize)
        gflapangle = 90 - opt.clueflapangle
        gfmirror = opt.clueflapside
        fingergrepa = opt.fingergrepa
        fingergrepb = opt.fingergrepb
        usetop = opt.usetop

        lockrr = uu(opt.lockroundradius)

        def glueflap_params(off, f45, ang):
            off_uu = uu(off)
            f45_uu = uu(f45)
            desl = (((boxD + boxL) / 2 - off_uu - f45_uu)
                    / sin(radians(90 - ang)) * sin(radians(ang)))
            return off_uu, f45_uu, desl

        gin_off, gin45, gindesl = glueflap_params(opt.glueflapinoff, opt.glueflapin45, opt.glueflapinang)
        gou_off, gou45, goudesl = glueflap_params(opt.glueflapouoff, opt.glueflapou45, opt.glueflapouang)
        top_gp = {'inoff': gin_off, 'in45': gin45, 'indesl': gindesl,
                  'ouoff': gou_off, 'ou45': gou45, 'oudesl': goudesl}

        if usetop:
            bot_gp = top_gp
        else:
            bgin_off, bgin45, bgindesl = glueflap_params(opt.bglueflapinoff, opt.bglueflapin45, opt.bglueflapinang)
            bgou_off, bgou45, bgoudesl = glueflap_params(opt.bglueflapouoff, opt.bglueflapou45, opt.bglueflapouang)
            bot_gp = {'inoff': bgin_off, 'in45': bgin45, 'indesl': bgindesl,
                      'ouoff': bgou_off, 'ou45': bgou45, 'oudesl': bgoudesl}

        tpsc = opt.topscheme
        btsc = opt.botscheme
        tfal = opt.tfal
        bfal = opt.bfal
        hotmeltp = opt.hotmeltprop

        self.validate(boxW, boxD, boxH, boxL, thck, lockrr, fingergrepr,
                       fingergrepa, fingergrepb, opt.clueflapangle)

        angx = asin((boxL - thck) / lockrr)
        angy = (3.141615 / 2) - angx
        lockroff = lockrr - (lockrr * sin(angy))

        box_id = self.svg.get_unique_id('box')
        g = etree.SubElement(self.svg.get_current_layer(), 'g', {
            'id': box_id,
            inkex.addNS('label', 'inkscape'): f'InkPACKING box ({box_id})',
        })

        b = BoxBuilder(g, box_id, boxW, boxD, boxH, boxL, thck, lockrr, lockroff, roto)

        gflapoffy = (gflapsize / sin((gflapangle / 360) * 6.28)) * sin(((90 - gflapangle) / 360) * 6.28)
        b.draw_side_glueflap(gfmirror, gflapsize, gflapoffy)
        b.draw_body(gfmirror)

        # --- top ---
        if tpsc == "notp":
            b.draw_open_edge('topdraw', 0, -1, fingergrepa, fingergrepb, fingergrepr)
        elif tpsc in ("fwlf", "rwlf"):
            inicut = (boxW + boxD) if tfal else 0
            b.draw_lockflap_end('tophead', 0, -1, tpsc, tfal, rounded=(tpsc == "rwlf"))
            b.draw_cut_edge('topcut', 0, -1, inicut, fingergrepa, fingergrepr)
        elif tpsc == "fwnf":
            b.draw_hotmelt_end('topdraw', 0, -1, tfal, hotmeltp)

        # --- bottom ---
        if btsc == "nobt":
            b.draw_open_edge('botdraw', boxH, 1, fingergrepa, fingergrepb, fingergrepr)
        elif btsc in ("fwlf", "rwlf"):
            inicut = (boxW + boxD) if bfal else 0
            b.draw_lockflap_end('bothead', boxH, 1, btsc, bfal, rounded=(btsc == "rwlf"))
            b.draw_cut_edge('botcut', boxH, 1, inicut, fingergrepa, fingergrepr)
        elif btsc == "fwnf":
            b.draw_hotmelt_end('botdraw', boxH, 1, bfal, hotmeltp)

        # --- dust flaps ---
        if tpsc != "notp":
            b.draw_dust_flaps('topglueflap', 0, -1, tpsc, tfal, top_gp)
        if btsc != "nobt":
            b.draw_dust_flaps('botglueflap', boxH, 1, btsc, bfal, bot_gp)


if __name__ == '__main__':
    InkPacking().run()
