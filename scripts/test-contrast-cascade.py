"""Regressions for the independent review's false passes, plus cascade order."""
import unittest
from css_cascade import audit_sources, specificity
from contrast_colours import colour, ratio

BASE='''
:root { --ink: #eee; --paper: #06070b; --accent: #888; }
body { color: var(--ink); background: var(--paper); }
.gitm-reader { color: var(--ink); }
.gitm-source-note { color: var(--ink); }
'''


def report(extra):return audit_sources([('voices.css',BASE+extra)])


class CascadeTests(unittest.TestCase):
    def rejected(self,extra):
        r=report(extra);self.assertTrue(r['failures'] or r['unsupported'],extra)
        return r
    def test_baseline(self):
        r=report('');self.assertGreater(len(r['pairs']),0);self.assertFalse(r['failures']);self.assertFalse(r['unsupported'])
    def test_rgba_black(self):self.rejected('.gitm-source-note {color:rgba(0,0,0,1)}')
    def test_hsl_fails_explicitly(self):
        self.assertTrue(self.rejected('.gitm-source-note {color:hsl(0 0% 0%)}')['unsupported'])
    def test_important_survives_later_normal_rule(self):
        self.rejected('.gitm-source-note {color:#000 !important} .gitm-source-note {color:#eee}')
    def test_important_good_colour_wins(self):
        r=report('.gitm-source-note {color:#eee !important} .gitm-source-note {color:#000}')
        self.assertFalse(r['failures']);self.assertFalse(r['unsupported'])
    def test_selector_specificity_beats_source_order(self):
        self.rejected('.voiced .gitm-source-note {color:#000} .gitm-source-note {color:#eee}')
        self.assertGreater(specificity('#article .gitm-source-note'),specificity('.voiced .gitm-source-note'))
    def test_same_rule_custom_property_beats_fallback(self):
        self.rejected('.gitm-source-note {--bad:#000; color:var(--bad,#eee)}')
    def test_missing_custom_property_uses_fallback(self):
        r=report('.gitm-source-note {color:var(--absent,#eee)}');self.assertFalse(r['failures']);self.assertFalse(r['unsupported'])
    def test_custom_property_inherits_from_reading_surface(self):
        self.rejected('.gitm-reader__body {--ink:#000}')
    def test_background_only_rule_is_checked(self):
        self.rejected('.gitm-reader__body {background:#eee}')
    def test_parent_opacity_is_composited(self):
        self.rejected('.gitm-reader__body {opacity:.01}')
    def test_portrait_focus_outline_not_skipped(self):
        r=self.rejected('a.gitm-card__portrait-link:focus-visible {outline:2px solid #06070b}')
        self.assertTrue(any(p['role']=='focus outline' for p in r['failures']))
    def test_unknown_background_colour_function_rejected(self):
        self.assertTrue(self.rejected('.new-component {background:lab(90 0 0)}')['unsupported'])
    def test_new_background_only_selector_not_skipped(self):self.rejected('.new-component {background:#eee}')
    def test_unsupported_selector_explicit(self):
        self.assertTrue(self.rejected('.new-component:nth-child(2) {color:#000}')['unsupported'])
    def test_important_custom_property(self):
        self.rejected('.gitm-source-note {--ink:#000!important} .gitm-source-note {--ink:#eee}')
    def test_hidden_tooltip_is_checked_when_hovered(self):
        self.rejected('.gitm-tone-popover {opacity:0} .gitm-claude-reader__hint-help:hover .gitm-tone-popover {opacity:1} .gitm-tone-popover dt {color:#000}')
    def test_brightness_affects_text(self):self.rejected('.gitm-source-note {filter:brightness(.1)}')
    def test_unknown_filter_fails_explicitly(self):self.assertTrue(self.rejected('.gitm-source-note {filter:hue-rotate(10deg)}')['unsupported'])
    def test_new_colour_conditional_fails_explicitly(self):self.assertTrue(self.rejected('@supports (animation-timeline: view()) {.gitm-source-note {color:#000}}')['unsupported'])
    def test_empty_inventory_cannot_pass(self):self.assertTrue(audit_sources([])['unsupported'])
    def test_transparent_text_without_glyph_clip_fails(self):self.rejected('.new-component {color:transparent;background:linear-gradient(#eee,#eee)}')
    def test_reset_cannot_silently_pass(self):self.assertTrue(self.rejected('.gitm-source-note {all:initial}')['unsupported'])
    def test_unknown_variable_escape_cannot_select_white_fallback(self):self.assertTrue(self.rejected(r'.gitm-source-note {color:var(--bad\31,#eee)}')['unsupported'])


class RoundFourTests(unittest.TestCase):
    rejected=CascadeTests.rejected
    def test_unsampled_media_interval(self):
        result=self.rejected('@media (min-width:600px) and (max-width:700px){.gitm-source-note{color:#06070b;background:#06070b}}')
        self.assertTrue(any(600<=p['width']<=700 for p in result['failures']))
        self.assertTrue({320,390,768,1024,1280,599,600,601,699,700,701}.issubset(set(result['viewports']['voices.css']['widths'])))
    def test_unsupported_media_units_fail(self):self.assertTrue(self.rejected('@media (max-width:50em){.gitm-source-note{color:#000}}')['unsupported'])
    def test_linear_mix_reviewer_reproduction(self):
        mixed=colour('color-mix(in srgb-linear,#000 70%,#fff)',{})
        self.assertAlmostEqual(mixed[0],.5838314900602575,places=9)
        self.assertAlmostEqual(ratio(mixed,colour('#eee',{})),2.5856931660692397,places=8)
        self.rejected('.review-mix{background:#eee;color:color-mix(in srgb-linear,#000 70%,#fff)}')
    def test_background_inherit_keeps_alpha_layer(self):
        result=self.rejected('body{background:#000;color:#eee}.gitm-reader__body{background:rgba(255,255,255,.3)}.gitm-source-note{color:#eee;background:inherit}')
        ratios=[p['ratio'] for p in result['pairs'] if p['selector']=='.gitm-source-note']
        self.assertTrue(ratios);self.assertAlmostEqual(ratios[0],3.309971799383957,places=4)
    def test_mix_spaces_are_distinct(self):
        self.assertAlmostEqual(colour('color-mix(in srgb,#000,#fff)',{})[0],.5,places=9)
        self.assertAlmostEqual(colour('color-mix(in srgb-linear,#000,#fff)',{})[0],.7353569830524495,places=9)
        for space in ['oklab','oklch']:self.assertAlmostEqual(colour('color-mix(in '+space+',#000,#fff)',{})[0],.38857286,places=6)
    def test_mixing_percentages_and_alpha(self):
        self.assertEqual(colour('color-mix(in srgb,#000 20%,#fff 20%)',{}),[.5,.5,.5,.4])
        self.assertEqual(colour('color-mix(in srgb,#000 25%,transparent)',{}),[0,0,0,.25])
        self.assertEqual(colour('color-mix(in srgb,rgba(255,0,0,.5),rgba(0,0,255,1))',{}),[1/3,0,2/3,.75])
    def test_hue_arc_selection(self):
        from colour_spaces import mix
        a=('oklch',[.7,.1,350],1);b=('oklch',[.7,.1,10],1)
        self.assertAlmostEqual(mix('in oklch',a,b,50,50)[1][2],0)
        self.assertAlmostEqual(mix('in oklch longer hue',a,b,50,50)[1][2],180)
    def test_unknown_interpolation_space_rejected(self):
        with self.assertRaises(ValueError):colour('color-mix(in made-up,#000,#fff)',{})
    def test_lab_round_trip(self):
        from colour_spaces import convert
        for rgb in [[0,0,0],[1,1,1],[1,0,0],[.1,.5,.9]]:
            for expected,actual in zip(rgb,convert(convert(rgb,'srgb','oklab'),'oklab','srgb')):self.assertAlmostEqual(expected,actual,places=5)


if __name__=='__main__':unittest.main()
