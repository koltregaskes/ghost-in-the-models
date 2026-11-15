"""Regressions for the independent review's false passes, plus cascade order."""
import unittest
from css_cascade import audit_sources, specificity

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


if __name__=='__main__':unittest.main()
