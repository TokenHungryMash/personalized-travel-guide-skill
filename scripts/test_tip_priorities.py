import unittest
from build_render_bindings import tips
from _current_system_adapter import runtime_bindings
from test_current_system_build import profile
class TipTests(unittest.TestCase):
    def test_duplicate_titles_keep_independent_priorities(self):
        p=profile();p['module_groups']['travel_notes']=[{'title':'组','items':[{'title':'相同标题','note':'内容','priority':v} for v in ('必须','建议','随缘')]}]
        html=tips(p)
        for v in ('必须','建议','随缘'):self.assertIn('data-tip-priority="'+v+'"',html)
if __name__=='__main__':unittest.main()
