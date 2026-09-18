#!/usr/bin/env python3
"""Turn a reMarkable .rm page into an animated drawn-title asset.

The tablet's own SVG export is no use here: it unions overlapping pen strokes
into filled outlines, which discards both the pen's route and the order you
wrote in. The raw .rm file keeps all of it -- one Line per stroke, in the order
drawn, each a list of centerline points carrying width and pressure. That is
what this reads.

Because the centerline is the pen's actual route, the asset needs no mask and
no wide-brush trick: a dash animation runs straight along the stroke. Strokes
are emitted in written order and carry their own --draw-delay/--draw-dur, so
the title replays the way it was written.

A ballpoint changes width with pressure, so a stroke is cut into runs of
near-constant width, each its own <path>. Their delays are contiguous and the
caps are round, so the run boundaries neither show nor stutter.

    ./rm-to-title.py page.rm --list
    ./rm-to-title.py page.rm --strokes 0-13 -o src/assets/titles/my-title.svg

Needs rmscene:  pip install rmscene
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

from rmscene import read_tree, scene_items as si

# How long the finished title takes to write itself, in seconds. Overridable
# with --duration.
DURATION = 2.6
# Pacing is length-proportional: the pen covers viewBox units at a constant
# rate, and the whole thing is then scaled to DURATION. The tablet does record
# a per-point speed, but its units are undocumented, so we do not use it.
#
# A pen lift between strokes costs as much as this many units of travel.
# Without a gap the title reads as one continuous scrawl; too large and it
# dawdles between letters. Strokes here average around 145 units.
LIFT_UNITS = 54.0
# Floor on a run's share, so a very short run still gets visible time.
MIN_UNITS = 3.0
# Padding around the ink, in viewBox units, so the widest stroke is not clipped.
PADDING = 8
# Point.width is in tablet units. Dividing by this, times the pen-size
# multiplier the user picked, lands in viewBox units. Checked against the
# tablet's own SVG export, whose ink sits half a pen width outside these
# centerlines: that gives a 3.0-3.2 unit pen, and so does this.
WIDTH_UNITS = 10
# Width is quantised to this many viewBox units before splitting a stroke into
# runs. Smaller is more faithful and more paths; this keeps a title in the low
# hundreds rather than one path per point.
WIDTH_STEP = 0.2


@dataclass
class Stroke:
    """One pen stroke: the route, and how wide the pen was along it."""

    points: list[tuple[float, float]]
    widths: list[float]
    tool: str

    @property
    def length(self) -> float:
        return sum(math.dist(a, b) for a, b in zip(self.points, self.points[1:]))

    def bbox(self) -> tuple[float, float, float, float]:
        # Half a pen width either side of the route is what actually gets inked.
        pad = max(self.widths) / 2
        xs = [x for x, _ in self.points]
        ys = [y for _, y in self.points]
        return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad

    def runs(self) -> list[tuple[list[tuple[float, float]], float]]:
        """Split into stretches of near-constant width.

        Consecutive runs share their boundary point, so the stroke stays
        unbroken when each run is drawn as a separate path.
        """
        stepped = [round(w / WIDTH_STEP) * WIDTH_STEP for w in self.widths]
        out: list[tuple[list[tuple[float, float]], float]] = []
        start = 0
        for i in range(1, len(self.points)):
            if stepped[i] != stepped[start]:
                out.append((self.points[start : i + 1], stepped[start]))
                start = i
        out.append((self.points[start:], stepped[start]))
        # A run needs two points to be a line.
        return [(pts, w) for pts, w in out if len(pts) >= 2]


def read_strokes(path: str) -> list[Stroke]:
    """Every pen stroke on the page, in the order it was drawn."""
    tree = read_tree(open(path, "rb"))
    out: list[Stroke] = []

    def walk(group: si.Group) -> None:
        # children is a CrdtSequence; iterating it yields document order, which
        # for a freehand layer is the order the strokes were laid down.
        for item in group.children.values():
            if isinstance(item, si.Group):
                walk(item)
            elif isinstance(item, si.Line):
                if item.tool in (si.Pen.ERASER, si.Pen.ERASER_AREA):
                    continue
                pts = [(p.x, p.y) for p in item.points]
                wds = [p.width * item.thickness_scale / WIDTH_UNITS for p in item.points]
                # Consecutive duplicates add no length but do make zero-length
                # segments, which some renderers dislike.
                keep = [0] + [
                    i for i in range(1, len(pts)) if math.dist(pts[i - 1], pts[i]) > 1e-6
                ]
                pts = [pts[i] for i in keep]
                wds = [wds[i] for i in keep]
                if len(pts) < 2:
                    # A tap, not a stroke. Nudge it so it renders as a dot.
                    pts = [pts[0], (pts[0][0] + 0.01, pts[0][1])]
                    wds = [wds[0], wds[0]]
                out.append(Stroke(points=pts, widths=wds, tool=item.tool.name))

    walk(tree.root)
    return out


def parse_selection(spec: str, count: int) -> list[int]:
    picked: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part.lstrip("-"):
            lo, hi = part.split("-", 1)
            picked.extend(range(int(lo), int(hi) + 1))
        else:
            picked.append(int(part))
    bad = [i for i in picked if not 0 <= i < count]
    if bad:
        sys.exit(f"no such stroke: {bad} (file has {count})")
    return picked


def fmt(value: float) -> str:
    """Trim coordinates to something a human can diff."""
    return f"{value:.2f}".rstrip("0").rstrip(".") or "0"


def build_svg(
    strokes: list[Stroke], label: str, duration: float
) -> tuple[str, int]:
    x0 = min(s.bbox()[0] for s in strokes) - PADDING
    y0 = min(s.bbox()[1] for s in strokes) - PADDING
    x1 = max(s.bbox()[2] for s in strokes) + PADDING
    y1 = max(s.bbox()[3] for s in strokes) + PADDING

    # Lay the timeline out in units of pen travel first, then scale it to the
    # duration asked for. Doing it in this order keeps the relative pacing of
    # strokes and lifts fixed however long the title is told to take.
    timeline: list[tuple[list[tuple[float, float]], float, float]] = []
    units = 0.0
    for stroke in strokes:
        # Pace every run of a stroke off one rate, so width changes do not
        # speed the pen up or slow it down.
        for pts, width in stroke.runs():
            span = max(sum(math.dist(a, b) for a, b in zip(pts, pts[1:])), MIN_UNITS)
            timeline.append((pts, width, span))
            units += span
        units += LIFT_UNITS
    units -= LIFT_UNITS  # no lift after the last stroke

    scale = duration / units if units else 0

    chunks: list[str] = []
    clock = 0.0
    for stroke in strokes:
        for pts, width in stroke.runs():
            _, _, span = timeline.pop(0)
            dur = span * scale
            d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
            chunks.append(
                f'  <path pathLength="1" stroke-width="{fmt(width)}"'
                f' style="--draw-delay:{clock:.3f}s;--draw-dur:{dur:.3f}s"'
                f' d="{d}"/>'
            )
            clock += dur
        clock += LIFT_UNITS * scale

    body = "\n".join(chunks)
    svg = f"""<!--
  "{label}", replayed from the reMarkable strokes that drew it.

  Generated by scripts/rm-to-title.py. Edit the notebook and regenerate;
  do not hand-edit this file.

  Each path is a stretch of one pen stroke, in the order it was written, along
  the pen's own centerline, with the width the pen had there. pathLength="1"
  makes the dash maths scale-free, and the draw-delay/draw-dur custom
  properties carry its slice of the {duration:.2f}s timeline. The animation
  itself lives in editorial.css.

  Keep this comment free of double hyphens. XML forbids them inside comments.
-->
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="{fmt(x0)} {fmt(y0)} {fmt(x1 - x0)} {fmt(y1 - y0)}"
     class="drawn-title-ink" role="img">
{body}
</svg>
"""
    return svg, len(chunks)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rm", help="a .rm page from the tablet")
    ap.add_argument("-o", "--output", help="where to write the SVG (default: stdout)")
    ap.add_argument("--list", action="store_true", help="describe each stroke and exit")
    ap.add_argument("--strokes", help='which to keep, e.g. "0-13,15" (default: all)')
    ap.add_argument("--label", default="Drawn title", help="name used in the file comment")
    ap.add_argument(
        "--duration", type=float, default=DURATION,
        help=f"seconds the title takes to write itself (default: {DURATION})",
    )
    args = ap.parse_args()

    strokes = read_strokes(args.rm)
    if not strokes:
        sys.exit("no pen strokes in that page")

    if args.list:
        for i, s in enumerate(strokes):
            bx0, by0, bx1, by1 = s.bbox()
            print(
                f"{i:3d} pts={len(s.points):4d} len={s.length:7.1f} "
                f"w={min(s.widths):4.2f}-{max(s.widths):4.2f} "
                f"x[{bx0:8.1f},{bx1:8.1f}] y[{by0:8.1f},{by1:8.1f}] {s.tool}"
            )
        return

    if args.strokes:
        strokes = [strokes[i] for i in parse_selection(args.strokes, len(strokes))]

    svg, count = build_svg(strokes, args.label, args.duration)
    lo = min(w for s in strokes for w in s.widths)
    hi = max(w for s in strokes for w in s.widths)
    print(
        f"{len(strokes)} strokes -> {count} paths, "
        f"pen {lo:.2f}-{hi:.2f} units ({hi / lo:.2f}x), {args.duration:.2f}s",
        file=sys.stderr,
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(svg)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(svg)


if __name__ == "__main__":
    main()
