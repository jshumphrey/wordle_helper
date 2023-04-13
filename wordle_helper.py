#!/usr/bin/python
"""This is a simple script to help output valid Wordle words that might make
good guesses, based on the feedback received about previous guesses."""

from typing import Iterator, Optional, Sequence

Letter = str

THREE_POINT_LETTERS = {"e", "t", "a", "o", "i", "n"}
TWO_POINT_LETTERS = {"s", "h", "r", "d", "l", "c", "u"}
ONE_POINT_LETTERS = {"m", "w", "f", "g", "y", "p", "b"}


class Word:
    """A Word represents a single valid Wordle word.
    Words also define a number of data structures to make comparison faster."""

    full_word: str
    letters: set[Letter]
    positions: dict[int, Letter] # This dict STARTS AT 1
    score: int

    def __init__(self, full_word: str) -> None:
        if len(full_word) != 5:
            raise ValueError("Words must have exactly five letters!")

        self.full_word = full_word
        self.letters = set(full_word)
        self.positions = dict(enumerate(full_word, start = 1))

        self.score = calculate_word_score(self)

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
    wanted_positions: dict[int, set[Letter]]
    unwanted_positions: dict[int, set[Letter]]

    def __init__(
        self,
        wanted_letters: Optional[Sequence[Letter]] = None,
        unwanted_letters: Optional[Sequence[Letter]] = None,
        wanted_positions: Optional[dict[int, str]] = None,
        unwanted_positions: Optional[dict[int, str]] = None,
    ) -> None:
        """Parse the input word and set up the data structures."""

        self.wanted_letters = set(wanted_letters) if wanted_letters else set()
        self.unwanted_letters = set(unwanted_letters) if unwanted_letters else set()

        if wanted_positions:
            self.wanted_positions = {pos: set(letters) for pos, letters in wanted_positions.items()}
            self.wanted_letters |= set().union(*self.wanted_positions.values())
        else:
            self.wanted_positions = {}

        if unwanted_positions:
            self.unwanted_positions = {pos: set(letters) for pos, letters in unwanted_positions.items()}
            # Do NOT add unwanted_positions to unwanted_letters, because that's not how that works
        else:
            self.unwanted_positions = {}

    def is_word_accepted(self, word: Word | str) -> bool:
        """This examines an input word and determines whether
        the word meets this Mask's filtering criteria."""

        if isinstance(word, str):
            word = Word(word)

        # If the word doesn't have any of the letters we want, reject it
        if self.wanted_letters and not self.wanted_letters.issubset(word.letters):
            return False

        # If the word has any of the letters we don't want, reject it
        if self.unwanted_letters and self.unwanted_letters.intersection(word.letters):
            return False

        # If the word doesn't have any of the specific position letters we want, reject it
        for position, letters in self.wanted_positions.items():
            if word[position] not in letters:
                return False

        # If the word has any of the specific position letters we don't want, reject it
        for position, letters in self.unwanted_positions.items():
            if word[position] in letters:
                return False

        return True

    def filter_words(self, words: Sequence[Word]) -> Iterator[Word]:
        """This applies this Mask to an entire sequence of input Words."""
        return (word for word in words if self.is_word_accepted(word))


def calculate_word_score(word: Word) -> int:
    """This calculates a word's "score" from the scores of its letters.
    This serves as a general proxy of how valuable its letters are
    in terms of gaining new information."""
    score = 0
    for letter in word.letters:
        if letter in THREE_POINT_LETTERS:
            score += 3
        elif letter in TWO_POINT_LETTERS:
            score += 2
        elif letter in ONE_POINT_LETTERS:
            score += 1

    return score


def load_words(word_list_filename: str) -> list[Word]:
    """This reads in the list of five-letter words from the input text file,
    and returns a set of Word objects; one for each word in the file."""
    with open(word_list_filename, "r", encoding = "utf-8") as infile:
        return [Word(line.strip()) for line in infile.readlines()]

def pprint_filter_results(mask: Mask, words: Sequence[Word]) -> None:
    """This pretty-prints the result of applying the provided Mask to the provided
    list of words."""
    filtered_words = sorted(
        mask.filter_words(words),
        key = lambda w: w.score,
        reverse = True,
    )
    print([
        f"{word.full_word} ({word.score})"
        for word in filtered_words
    ])

def main():
    """Execute top-level functionality."""
    words = load_words("five_letter_words.txt") # pylint: disable = unused-variable
    mask = Mask("at", "sle", {}, {3: "a", 4: "t"})
    pprint_filter_results(mask, words)
    breakpoint() # pylint: disable = forgotten-debug-statement

if __name__ == "__main__":
    main()
