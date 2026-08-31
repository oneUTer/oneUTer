"""Offline regression tests for the pinned snake SVG format."""

import unittest
import xml.etree.ElementTree as ET

from retime_snake import KEYFRAMES, TRANSLATE, compact, parse_frames, retime_svg


FIXTURE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -32 880 192">
<desc>Timing test fixture</desc><style>
:root{--cs:#7c3aed;--ce:#ebedf0;--c1:#bae6fd}
.c{fill:var(--ce);animation:none 10000ms linear infinite}
@keyframes c0{19.99%{fill:var(--c1)}20.01%,100%{fill:var(--ce)}}
.c.c0{fill:var(--c1);animation-name:c0}
@keyframes c1{69.98%{fill:var(--c1)}70%,100%{fill:var(--ce)}}
.c.c1{fill:var(--c1);animation-name:c1}
.u{transform:scale(0,1);animation:none linear 10000ms infinite}
@keyframes u0{19.99%{transform:scale(0,1)}20.01%,69.98%{transform:scale(0.5,1)}70%,100%{transform:scale(1,1)}}
.u.u0{animation-name:u0}
.s{fill:var(--cs);animation:none linear 10000ms infinite}
@keyframes s0{0%,99%{transform:translate(0px,-16px)}10%{transform:translate(0px,0px)}80%{transform:translate(112px,0px)}90%{transform:translate(112px,-16px)}}
.s.s0{transform:translate(0px,-16px);animation-name:s0}
@keyframes s1{0%,99%{transform:translate(16px,-16px)}20%{transform:translate(0px,-16px)}30%{transform:translate(0px,0px)}90%{transform:translate(96px,0px)}98%{transform:translate(96px,-16px)}}
.s.s1{transform:translate(16px,-16px);animation-name:s1}
</style><rect class="c c0"/><rect class="c c1"/>
<rect class="s s0"/><rect class="s s1"/><rect class="u u0"/></svg>"""


def animations(svg):
    return {m[1]: parse_frames(m[2]) for m in KEYFRAMES.finditer(svg)}


def position_at(frames, percent):
    positions = {}
    for p, style in frames.items():
        match = TRANSLATE.fullmatch(compact(style))
        positions[p] = (float(match[1]), float(match[2]))
    positions.setdefault(100, positions[0])
    left = max(p for p in positions if p <= percent)
    right = min(p for p in positions if p >= percent)
    if left == right:
        return positions[left]
    ratio = (percent - left) / (right - left)
    return tuple(a + (b - a) * ratio for a, b in zip(positions[left], positions[right]))


class SnakeTimingTests(unittest.TestCase):
    def test_changes_only_styles_and_shared_duration(self):
        result, report = retime_svg(FIXTURE)
        self.assertEqual(result.count("9000ms"), 3)
        self.assertNotIn("10000ms", result)
        self.assertIn("eat 7.000s unchanged", report)
        self.assertIn("return 3.000s -> 2.000s", report)
        original_root, new_root = ET.fromstring(FIXTURE), ET.fromstring(result)
        for root in (original_root, new_root):
            root.find("{http://www.w3.org/2000/svg}style").text = ""
        self.assertEqual(ET.tostring(original_root), ET.tostring(new_root))

    def test_preserves_snake_path_at_every_sample_before_and_after_cutoff(self):
        updated = animations(retime_svg(FIXTURE)[0])
        original = animations(FIXTURE)
        for name in ("s0", "s1"):
            self.assertIn(round(7000 / 9000 * 100, 8), updated[name], "Must split a straight segment at the speed change")
            for old_ms in range(0, 10001, 25):
                new_ms = old_ms if old_ms <= 7000 else 7000 + (old_ms - 7000) * 2 / 3
                before = position_at(original[name], old_ms / 100)
                after = position_at(updated[name], new_ms / 90)
                for a, b in zip(before, after):
                    self.assertAlmostEqual(a, b, places=6)

    def test_contribution_and_progress_events_keep_their_absolute_times(self):
        original = animations(FIXTURE)
        updated = animations(retime_svg(FIXTURE)[0])
        for name in ("c0", "c1", "u0"):
            for old_percent, style in original[name].items():
                new_percent = round(old_percent * 10000 / 9000, 8) if old_percent < 100 else 100
                self.assertEqual(updated[name][new_percent], style)

    def test_loop_end_matches_start_for_every_segment(self):
        updated = animations(retime_svg(FIXTURE)[0])
        for name in ("s0", "s1"):
            self.assertEqual(updated[name][0], updated[name][100])

    def test_both_palettes_and_base36_cell_names(self):
        dark = FIXTURE.replace("#7c3aed", "#a78bfa").replace("#ebedf0", "#161b22")
        # The generator names cells c0 ... cz, c10, c11, etc.
        dark = dark.replace("keyframes c1", "keyframes c10").replace(".c.c1", ".c.c10")
        dark = dark.replace("animation-name:c1", "animation-name:c10").replace('class="c c1"', 'class="c c10"')
        result, _ = retime_svg(dark)
        self.assertIn("#161b22", result)
        self.assertIn("#a78bfa", result)
        self.assertIn("c10", animations(result))
        self.assertEqual(result.count("9000ms"), 3)

    def test_existing_keyframe_at_cutoff(self):
        source = FIXTURE.replace("80%{transform:translate(112px,0px)}", "70%{transform:translate(112px,0px)}")
        frames = animations(retime_svg(source)[0])["s0"]
        self.assertEqual(frames[round(7000 / 9000 * 100, 8)], "transform:translate(112px,0px)")

    def test_idempotent_and_short_return_not_slowed_down(self):
        first, _ = retime_svg(FIXTURE)
        self.assertEqual(retime_svg(first)[0], first)
        self.assertEqual(retime_svg(FIXTURE, 3000)[0], FIXTURE)
        self.assertEqual(retime_svg(FIXTURE, 4000)[0], FIXTURE)

    def test_empty_contribution_graph_is_unchanged(self):
        source = '<svg xmlns="http://www.w3.org/2000/svg"><style>.s{animation:none linear 0ms infinite}</style><rect class="c"/></svg>'
        self.assertEqual(retime_svg(source)[0], source)

    def test_custom_return_duration(self):
        result, report = retime_svg(FIXTURE, 500)
        self.assertEqual(result.count("7500ms"), 3)
        self.assertIn("return 3.000s -> 0.500s", report)

    def test_invalid_duration_rejected(self):
        for duration in (0, -1, float("nan"), float("inf")):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                retime_svg(FIXTURE, duration)

    def test_unexpected_generator_output_rejected(self):
        for source in (
            FIXTURE.replace("10000ms", "9000ms", 1),
            FIXTURE.replace('class="c c1"', 'class="c c2"'),
            FIXTURE.replace("@keyframes s0", "@keyframes x0"),
            FIXTURE.replace("transform:translate(112px,0px)", "transform:rotate(90deg)"),
            FIXTURE.replace("70%,100%{fill:var(--ce)}", "70%{fill:var(--ce)}"),
            FIXTURE.replace("0%,99%{transform:translate(0px,-16px)}", "0%{transform:translate(0px,-16px)}"),
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                retime_svg(source)


if __name__ == "__main__":
    unittest.main()
