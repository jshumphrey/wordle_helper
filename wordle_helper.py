#!/usr/bin/python
"""This is a simple script to help output valid Wordle words that might make
good guesses, based on the feedback received about previous guesses."""

from typing import Iterator, Optional, Sequence

Letter = str

class Word:
    """A Word represents a single valid Wordle word.
    Words also define a number of data structures to make comparison faster."""

    full_word: str
    letters: set[Letter]
    positions: dict[int, Letter] # This dict STARTS AT 1

    def __init__(self, full_word: str) -> None:
        if len(full_word) != 5:
            raise ValueError("Words must have exactly five letters!")

        self.full_word = full_word
        self.letters = set(full_word)
        self.positions = dict(enumerate(full_word, start = 1))

    def __str__(self) -> str:
        return self.full_word

    def __repr__(self) -> str:
        return f"<Word '{self.full_word}'>"

    def __getitem__(self, position: int) -> Letter:
        return self.positions[position]

    def __contains__(self, letter: Letter) -> bool:
        return letter in self.letters


class Mask:
    """A Mask represents a set of filtering criteria that gets applied
    to a set of Words."""

    wanted_letters: set[Letter]
    unwanted_letters: set[Letter]
    wanted_positions: dict[int, Letter]

    def __init__(
        self,
        wanted_letters: Optional[Sequence[Letter]] = None,
        unwanted_letters: Optional[Sequence[Letter]] = None,
        wanted_positions: Optional[dict[int, Letter]] = None,
        unwanted_positions: Optional[dict[int, Letter]] = None,
    ) -> None:
        self.wanted_letters = set(wanted_letters) if wanted_letters else set()
        self.unwanted_letters = set(unwanted_letters) if unwanted_letters else set()

        self.wanted_positions = wanted_positions if wanted_positions else {}
        self.wanted_letters |= set(self.wanted_positions.values())

        self.unwanted_positions = unwanted_positions if unwanted_positions else {}
        # Do NOT add unwanted_positions to unwanted_letters, because that's not how that works

    def is_word_accepted(self, word: Word) -> bool:
        """This examines an input word and determines whether
        the word meets this Mask's filtering criteria."""

        # If the word doesn't have any of the letters we want, reject it
        if self.wanted_letters and not self.wanted_letters.issubset(word.letters):
            return False

        # If the word has any of the letters we don't want, reject it
        if self.unwanted_letters and self.unwanted_letters.intersection(word.letters):
            return False

        # If the word doesn't have any of the specific position letters we want, reject it
        for position, letter in self.wanted_positions.items():
            if word[position] is not letter:
                return False

        # If the word has any of the specific position letters we don't want, reject it
        for position, letter in self.unwanted_positions.items():
            if word[position] is letter:
                return False

        return True

    def filter_words(self, words: Sequence[Word]) -> Iterator[Word]:
        """This applies this Mask to an entire sequence of input Words."""
        return (word for word in words if self.is_word_accepted(word))

def load_words(word_list_filename: str) -> list[Word]:
    """This reads in the list of five-letter words from the input text file,
    and returns a set of Word objects; one for each word in the file."""
    with open(word_list_filename, "r", encoding = "utf-8") as infile:
        return [Word(line.strip()) for line in infile.readlines()]

def main():
    """Execute top-level functionality."""
    words = load_words("five_letter_words.txt") # pylint: disable = unused-variable
    breakpoint() # pylint: disable = forgotten-debug-statement

main()
