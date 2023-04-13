#!/usr/bin/python
"""This tests elements of the wordle_helper script."""

import unittest
import wordle_helper as wordle

class TestWord(unittest.TestCase):
    """Tests elements of the Word class."""

    def test_init(self):
        """Test that Word.__init__ parses its input correctly
        and assigns the class attributes correctly."""
        test_word_1 = wordle.Word("slate")
        self.assertEqual(test_word_1.full_word, "slate")
        self.assertEqual(test_word_1.letters, set(["s", "l", "a", "t", "e"]))
        self.assertEqual(test_word_1.positions, {1: "s", 2: "l", 3: "a", 4: "t", 5: "e"})
        self.assertEqual(test_word_1.score, 13)

class TestMask(unittest.TestCase):
    """Tests elements of the Mask class."""

    def test_init(self):
        """Test that Mask.__init__ parses the input correctly
        and assigns the class attributes correctly."""
        test_mask_1 = wordle.Mask(
            wanted_letters = "abc",
            unwanted_letters = "def",
            wanted_positions = {1: "g", 2: "h", 3: "i", 4: "j", 5: "k"},
            unwanted_positions = {1: "lmn", 2: "opq"},
        )

        self.assertEqual(test_mask_1.wanted_letters, set(["a", "b", "c", "g", "h", "i", "j", "k"]))
        self.assertEqual(test_mask_1.unwanted_positions, {1: set(["l", "m", "n"]), 2: set(["o", "p", "q"])})

    def test_is_word_accepted(self):
        """Test that Mask.is_word_accepted correctly accepts and rejects words."""
        test_mask_1 = wordle.Mask(
            wanted_letters = "at",
            unwanted_letters = "sle",
            wanted_positions = {},
            unwanted_positions = {3: "a", 4: "t"},
        )

        self.assertTrue(test_mask_1.is_word_accepted("ratio"))

if __name__ == "__main__":
    unittest.main()
