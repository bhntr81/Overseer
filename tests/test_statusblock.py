import json
import unittest

from overseer.statusblock import parse


def block(status='SUCCESS', tests='TRUE', files='[a.py, b.py]',
          instruction='"do the next bounded step"'):
    """Build a four-line status block with the given raw field values."""
    return ('noise before the block\n'
            'STATUS: %s\n'
            'TESTS_PASSED: %s\n'
            'FILES_MODIFIED: %s\n'
            'NEXT_AGENT_INSTRUCTION: %s\n'
            'trailing noise\n' % (status, tests, files, instruction))


class StatusBlockTests(unittest.TestCase):
    def test_a_filled_block_is_parsed_into_closed_values(self):
        result = parse(block())
        self.assertTrue(result['found'])
        self.assertTrue(result['valid'])
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIs(result['tests_passed'], True)
        self.assertEqual(result['files_modified'], ['a.py', 'b.py'])
        self.assertEqual(result['next_instruction'], 'do the next bounded step')
        # The other closed values parse too.
        other = parse(block(status='STUCK_NEEDS_ESCALATION', tests='FALSE', files='[]'))
        self.assertEqual(other['status'], 'STUCK_NEEDS_ESCALATION')
        self.assertIs(other['tests_passed'], False)
        self.assertEqual(other['files_modified'], [])

    def test_the_last_block_wins(self):
        text = (block(status='SUCCESS', instruction='"first"')
                + 'intervening output\n'
                + block(status='STUCK_NEEDS_ESCALATION', instruction='"second"'))
        result = parse(text)
        self.assertTrue(result['valid'])
        self.assertEqual(result['status'], 'STUCK_NEEDS_ESCALATION')
        self.assertEqual(result['next_instruction'], 'second')

    def test_the_unfilled_template_is_invalid(self):
        template = ('STATUS: [SUCCESS | STUCK_NEEDS_ESCALATION]\n'
                    'TESTS_PASSED: [TRUE | FALSE]\n'
                    'FILES_MODIFIED: [<list of files>]\n'
                    'NEXT_AGENT_INSTRUCTION: "<clear self-contained prompt>"\n')
        result = parse(template)
        self.assertTrue(result['found'])
        self.assertFalse(result['valid'])
        self.assertIn('template not filled', result['reason'])
        self.assertIsNone(result['status'])

    def test_an_unknown_status_is_invalid(self):
        result = parse(block(status='DONE'))
        self.assertTrue(result['found'])
        self.assertFalse(result['valid'])
        self.assertIn('unknown status', result['reason'])
        self.assertIn('DONE', result['reason'])

    def test_an_instruction_with_a_control_character_is_invalid(self):
        # A JSON-escaped control character decodes to a real control char.
        result = parse(block(instruction='"line one\\u0007bell"'))
        self.assertTrue(result['found'])
        self.assertFalse(result['valid'])
        self.assertIn('control character', result['reason'])
        self.assertIsNone(result['next_instruction'])

    def test_an_over_long_instruction_is_invalid_not_truncated(self):
        result = parse(block(instruction=json.dumps('x' * 5000)))
        self.assertTrue(result['found'])
        self.assertFalse(result['valid'])
        self.assertIn('4000', result['reason'])
        # It is rejected, never truncated into a valid 4000-char value.
        self.assertIsNone(result['next_instruction'])

    def test_no_block_is_not_found(self):
        result = parse('just some terminal output\nnothing structured here\n')
        self.assertFalse(result['found'])
        self.assertFalse(result['valid'])
        self.assertIn('no status block', result['reason'])

    def test_the_parser_never_evaluates_text(self):
        payload = "__import__('os').system('echo pwned')"
        result = parse(block(instruction=json.dumps(payload)))
        self.assertTrue(result['valid'])
        # The instruction is returned verbatim as data; nothing was evaluated.
        self.assertEqual(result['next_instruction'], payload)


if __name__ == '__main__':
    unittest.main()
