"""Shorten only the empty return trip in the pinned Platane/snk SVG output.

No third-party packages are needed. Cells, the progress bar and every snake
segment share a piecewise-linear clock. A segment crossing the speed-change
point needs an interpolated keyframe there, or its earlier motion would change.
The parser intentionally accepts the pinned generator's CSS, not arbitrary SVG.
"""

import argparse
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET


STYLE = re.compile(r"(<style>)(.*?)(</style>)", re.DOTALL)
KEYFRAMES = re.compile(r"@keyframes\s+([a-z0-9]+)\s*\{((?:[^{}]*\{[^{}]*\}\s*)+)\}")
FRAME = re.compile(r"([^{}]+)\{([^{}]*)\}")
NUMBER = r"-?(?:\d+(?:\.\d+)?|\.\d+)"
TRANSLATE = re.compile(rf"transform:translate\(({NUMBER})px,({NUMBER})px\);?")
DURATION = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)ms\b")


def compact(value):
    return re.sub(r"\s+", "", value).rstrip(";")


def number(value):
    return f"{value:.8f}".rstrip("0").rstrip(".")


def parse_frames(body):
    frames = {}
    position = 0
    for match in FRAME.finditer(body):
        if body[position:match.start()].strip():
            raise ValueError("Unsupported keyframe syntax")
        for selector in match[1].split(","):
            if not re.fullmatch(r"\s*\d+(?:\.\d+)?%\s*", selector):
                raise ValueError(f"Unsupported keyframe selector: {selector}")
            percent = float(selector.strip()[:-1])
            if not 0 <= percent <= 100 or percent in frames:
                raise ValueError("Invalid or duplicate keyframe offset")
            frames[percent] = match[2].strip()
        position = match.end()
    if not frames or body[position:].strip():
        raise ValueError("Incomplete keyframes")
    return frames


def split_snake_motion(frames, pivot):
    positions = {}
    for percent, style in frames.items():
        match = TRANSLATE.fullmatch(compact(style))
        if not match:
            raise ValueError("Unsupported snake transform")
        positions[percent] = (float(match[1]), float(match[2]))
    if 0 not in positions or positions[max(positions)] != positions[0]:
        raise ValueError("Snake does not return to its initial pose")

    # The generator relies on the underlying style for the implicit 100% frame.
    # Make that endpoint explicit before interpolating across the speed change.
    positions[100] = positions[0]
    if pivot not in positions:
        before = max(p for p in positions if p < pivot)
        after = min(p for p in positions if p > pivot)
        ratio = (pivot - before) / (after - before)
        positions[pivot] = tuple(
            a + (b - a) * ratio
            for a, b in zip(positions[before], positions[after])
        )
    return {
        p: f"transform:translate({number(x)}px,{number(y)}px)"
        for p, (x, y) in positions.items()
    }


def retime_svg(svg, return_ms=2000):
    """Return (SVG, timing report); reject unknown formats before publishing."""
    if not math.isfinite(return_ms) or return_ms <= 0:
        raise ValueError("Return duration must be a positive finite number")
    root = ET.fromstring(svg)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Expected an SVG document")
    styles = list(STYLE.finditer(svg))
    if len(styles) != 1:
        raise ValueError("Expected exactly one SVG style block")
    style_match = styles[0]
    css = style_match[2]
    animations = list(KEYFRAMES.finditer(css))
    if len(animations) != len(re.findall(r"@keyframes\b", css)):
        raise ValueError("Unrecognized animation syntax")
    frames_by_name = {}
    for match in animations:
        name = match[1]
        if not re.fullmatch(r"[cus][0-9a-z]+", name) or name in frames_by_name:
            raise ValueError(f"Unexpected animation: {name}")
        frames_by_name[name] = parse_frames(match[2])

    cell_names = {name for name in frames_by_name if name.startswith("c")}
    drawn_cells = {
        name
        for element in root.iter()
        if "c" in element.get("class", "").split()
        for name in element.get("class", "").split()
        if name != "c"
    }
    if cell_names != drawn_cells:
        raise ValueError("Contribution cells and animations do not match")
    if not cell_names:
        return svg, "unchanged: no contribution cells to eat"

    clear_times = []
    for name in cell_names:
        empty = [p for p, s in frames_by_name[name].items() if compact(s) == "fill:var(--ce)"]
        if len(empty) != 2 or 100 not in empty:
            raise ValueError(f"Cannot identify when {name} is eaten")
        clear_times.append(min(empty))
    pivot = max(clear_times)

    declarations = re.findall(r"\banimation\s*:\s*([^;}]+)", css)
    durations = []
    for declaration in declarations:
        values = DURATION.findall(declaration)
        if len(values) != 1 or "linear" not in declaration or "infinite" not in declaration:
            raise ValueError("Expected a shared, linear, looping animation clock")
        durations.append(float(values[0]))
    if len(durations) != 3 or len(set(durations)) != 1 or durations[0] <= 0:
        raise ValueError("Cells, progress bar and snake must have the same duration")
    if "s0" not in frames_by_name:
        raise ValueError("Missing snake head animation")

    duration = durations[0]
    eating_ms = duration * pivot / 100
    old_return_ms = duration - eating_ms
    # Do not slow down a short return or retime an already processed file.
    if old_return_ms <= return_ms + 0.001:
        return svg, "unchanged: return trip is already within the limit"
    new_duration = eating_ms + return_ms

    def clock(percent):
        time = duration * percent / 100
        if percent > pivot:
            time = eating_ms + (time - eating_ms) * return_ms / old_return_ms
        return 100 * time / new_duration

    def rewrite(match):
        name = match[1]
        frames = frames_by_name[name]
        if name.startswith("s"):
            frames = split_snake_motion(frames, pivot)
        body = "".join(
            f"{number(clock(p))}%{{{style}}}" for p, style in sorted(frames.items())
        )
        return f"@keyframes {name}{{{body}}}"

    css = KEYFRAMES.sub(rewrite, css)
    css = re.sub(
        r"\banimation\s*:\s*([^;}]+)",
        lambda m: "animation:" + DURATION.sub(number(new_duration) + "ms", m[1]),
        css,
    )
    result = svg[:style_match.start(2)] + css + svg[style_match.end(2):]
    ET.fromstring(result)
    report = (
        f"eat {eating_ms / 1000:.3f}s unchanged; "
        f"return {old_return_ms / 1000:.3f}s -> {return_ms / 1000:.3f}s; "
        f"loop {duration / 1000:.3f}s -> {new_duration / 1000:.3f}s"
    )
    return result, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--return-ms", type=float, default=2000)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        # Validate both themes before changing either generated file.
        results = [(path, *retime_svg(path.read_text(encoding="utf-8"), args.return_ms)) for path in args.files]
    except (OSError, ValueError, ET.ParseError) as error:
        parser.exit(1, f"Cannot retime contribution snake: {error}\n")
    for path, svg, report in results:
        path.write_text(svg, encoding="utf-8")
        print(f"{path.name}: {report}")


if __name__ == "__main__":
    main()
