#!/usr/bin/python
"""This tests elements of the wordle_helper script."""

import unittest
import wordle_helper as wordle

unittest.util._MAX_LENGTH = 999999999 # type: ignore  pylint: disable = protected-access

class TestWord(unittest.TestCase):
    """Tests elements of the Word class."""

    def test_init(self):
        """Test that Word.__init__ parses its input correctly
        and assigns the class attributes correctly."""
        test_word_1 = wordle.Word("slate")
        self.assertEqual(test_word_1.full_word, "slate")
        self.assertEqual(test_word_1.letters, set(["s", "l", "a", "t", "e"]))
        self.assertEqual(test_word_1.positions, {1: "s", 2: "l", 3: "a", 4: "t", 5: "e"})
        self.assertEqual(test_word_1.letter_counts, {"s": 1, "l": 1, "a": 1, "t": 1, "e": 1})

        test_word_2 = wordle.Word("teeth")
        self.assertEqual(test_word_2.letter_counts, {"t": 2, "e": 2, "h": 1})

    def test_calculate_guess_results_normal(self):
        """Test that Word.calculate_guess_results correctly calculates Wordle guess results
        when the input word and guessed words don't have any duplicate letters."""
        test_word_1 = wordle.Word("slate")
        self.assertEqual(test_word_1.calculate_guess_results(wordle.Word("ratio")), "byybb")
        self.assertEqual(test_word_1.calculate_guess_results(wordle.Word("slide")), "ggbbg")
        self.assertEqual(test_word_1.calculate_guess_results(wordle.Word("slate")), "ggggg")

    def test_calculate_guess_results_dupes(self):
        """Test that Word.calculate_guess_results correctly calculates Wordle guess results
        when the input word or guessed words do have duplicate letters."""
        test_word_1 = wordle.Word("teeth")
        self.assertEqual(test_word_1.calculate_guess_results(wordle.Word("table")), "gbbby")
        self.assertEqual(test_word_1.calculate_guess_results(wordle.Word("genie")), "bgbby")
        self.assertEqual(test_word_1.calculate_guess_results(wordle.Word("teens")), "gggbb")
        self.assertEqual(test_word_1.calculate_guess_results(wordle.Word("epees")), "ybgbb")


class TestWordList(unittest.TestCase):
    """Tests elements of the WordList class."""

    def test_from_file(self):
        """Make sure that WordList.from_file can successfully read in a file of test words."""
        try:
            test_wl = wordle.WordList.from_file("test_words_file.txt")
            self.assertEqual(list(w.full_word for w in test_wl), ["abcde", "fghij", "klmno"])

        except Exception as ex:
            raise AssertionError from ex


class TestMask(unittest.TestCase):
    """Tests elements of the Mask class."""

    def test_init(self):
        """Test that Mask.__init__ parses the input correctly
        and assigns the class attributes correctly."""
        test_mask_1 = wordle.Mask(
            correct_positions = {1: "g", 2: "h", 3: "i", 4: "j", 5: "k"},
            incorrect_positions = {1: set("lmn"), 2: set("opq")},
            incorrect_globals = set("def"),
        )

        self.assertEqual(test_mask_1.correct_letters, set("ghijklmnopq"))

    def test_is_word_accepted(self):
        """Test that Mask.is_word_accepted correctly accepts and rejects words."""
        test_mask_1 = wordle.Mask(
            correct_positions = {},
            incorrect_positions = {3: set("a"), 4: set("t")},
            incorrect_globals = set("sle"),
        )

        self.assertTrue(test_mask_1.is_word_accepted("ratio"))

    def test_is_word_accepted_dupes(self):
        """Test that Mask.is_word_accepted correctly accepts and rejects words
        when the guessed word contains duplicate letters."""

        # This Mask simulates guessing the word "arose" against a target of "adobo"
        test_mask_1 = wordle.Mask.from_wordle_results("arose", "gbgbb")
        self.assertTrue(test_mask_1.is_word_accepted("adobo"))

        test_mask_2 = (
            wordle.Mask.from_wordle_results("slate", "bbbbb")
            + wordle.Mask.from_wordle_results("crony", "bbbbg")
            + wordle.Mask.from_wordle_results("dumpy", "bgbgg")
        )
        self.assertTrue(test_mask_2.is_word_accepted("puppy"))

    def test_from_wordle_results(self):
        """Test that Mask.from_wordle_results correctly creates a Mask with the given inputs."""
        self.assertEqual(
            wordle.Mask.from_wordle_results("slate", "bbyyb"),
            wordle.Mask(
                correct_positions = {},
                incorrect_positions = {3: set("a"), 4: set("t")},
                incorrect_globals = set("sle"),
            )
        )

        self.assertEqual(
            wordle.Mask.from_wordle_results("chart", "gbyyg"),
            wordle.Mask(
                correct_positions = {1: "c", 5: "t"},
                incorrect_positions = {3: {"a"}, 4: {"r"}},
                incorrect_globals = {"h"},
            )
        )

    def test_from_wordle_results_dupes(self):
        """Test that mask.from_wordle_results correctly cretaes a Mask with the given inputs
        when the guessed word contains duplicate letters."""

        # This Mask simulates guessing the word "aloha" against a target of "adobo"
        self.assertEqual(
            wordle.Mask.from_wordle_results("aloha", "gbgbb"),
            wordle.Mask(
                correct_positions = {1: "a", 3: "o"},
                incorrect_positions = {},
                incorrect_globals = set("lh"),
                max_occurrences = {"a": 1},
            )
        )

        # This Mask simulates guessing the word "babes" against a target of "bases"
        self.assertEqual(
            wordle.Mask.from_wordle_results("babes", "ggbgg"),
            wordle.Mask(
                correct_positions = {1: "b", 2: "a", 4: "e", 5: "s"},
                incorrect_positions = {},
                incorrect_globals = set(),
                max_occurrences = {"b": 1},
            )
        )

    def test_info_guess_version(self):
        """Test that Mask.info_guess_version returns a Mask with the correct attributes."""
        test_mask_1 = wordle.Mask(
            correct_positions = {1: "s", 4: "t"},
            incorrect_positions = {5: {"e"}},
            incorrect_globals = set("la")
        )

        self.assertEqual(
            test_mask_1.info_guess_version(),
            wordle.Mask(
                correct_positions = {},
                incorrect_positions = {1: {"e"}, 4: {"e"}, 5: {"e"}},
                incorrect_globals = set("slat")
            )
        )


if __name__ == "__main__":
    unittest.main()
