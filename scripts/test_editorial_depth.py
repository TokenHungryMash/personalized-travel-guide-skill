import unittest
from audit_editorial_depth import audit


class EditorialDepthTests(unittest.TestCase):
    def test_two_short_rows_are_not_graded_by_length(self):
        report=audit({}, {k:[['背景','看海。'],['做法','坐车。']] for k in ('portrait','stays','culture','shopping')})
        self.assertEqual(len(report['reviewCandidates']),0)

    def test_short_copy_has_no_automatic_quality_verdict(self):
        report = audit({}, {k: [['标题', '只有一句提醒。']] for k in ('portrait', 'stays', 'culture', 'shopping')})
        self.assertEqual(len(report['reviewCandidates']), 0)
        self.assertEqual(report['errors'], [])

    def test_original_regression_reuses_deck_and_experience(self):
        text = '从同一片开阔地先看景物再决定是否继续往里面走，时间紧时就从这一处开始。'
        g = {'areas': [{'id': 'a', 'deck': text}, {'id': 'b', 'deck': text}]}
        t = {'area_sections': {'a': [['甲', text]], 'b': [['乙', text]]},
             'route_experiences': [{'areaId': i, 'copy': text} for i in ('a', 'b')]}
        errors = audit(g, t)['errors']
        self.assertTrue(any('deck verbatim' in e for e in errors))
        self.assertTrue(any('across regions' in e for e in errors))

    def test_repeated_padding_reports_place_ids(self):
        g = {'places': [{'id': str(i), 'tip': '若下一站有预约，出发前先查步行路线和实际入口，再决定本段停留多久。'} for i in range(3)]}
        self.assertEqual(audit(g, {})['reviewCandidates'][-1]['places'], ['0', '1', '2'])

    def test_short_shared_labels_are_not_duplicate_prose(self):
        t = {k: [['一个完整主题', '独立正文。' * 40]] for k in ('portrait', 'stays', 'culture', 'shopping')}
        t['route_experiences'] = [{'areaId': 'a', 'copy': '建议步行'}, {'areaId': 'b', 'copy': '建议步行'}]
        report = audit({}, t)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['reviewCandidates'], [])


if __name__ == '__main__':
    unittest.main()
