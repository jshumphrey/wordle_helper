#!/usr/bin/python
"""This is a simple script to help output valid Wordle words that might make
good guesses, based on the feedback received about previous guesses."""

from typing import Iterator, Optional, Sequence

Position = int
Letter = str

THREE_POINT_LETTERS = {"e", "t", "a", "o", "i", "n"}
TWO_POINT_LETTERS = {"s", "h", "r", "d", "l", "c", "u"}
ONE_POINT_LETTERS = {"m", "w", "f", "g", "y", "p", "b"}

MAX_PRINT_RESULTS = 50

def _universal_repr(input_object) -> str:
    try:
        object_class = input_object.__class__
        object_module = object_class.__module__
        if object_module != "builtins":
            object_fq_class = f"{object_module}.{object_class.__qualname__}"
        else:
            object_fq_class = object_class.__qualname__
        object_item_names = [
            f"{str(key)}: {str(value)}"
            for key, value in input_object.__dict__.items()
        ]

        return f"<{object_fq_class}: {', '.join(object_item_names)}>"

    except AttributeError:
        return repr(input_object)


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

        self.score = self.calculate_score()

    def __str__(self) -> str:
        return self.full_word

    def __repr__(self) -> str:
        return _universal_repr(self)

    def __eq__(self, other: "Word") -> bool:
        return self.full_word == other.full_word

    def __getitem__(self, position: int) -> Letter:
        return self.positions[position]

    def __contains__(self, letter: Letter) -> bool:
        return letter in self.letters

    def calculate_score(self) -> int:
        """This calculates a word's "score" from the scores of its letters.
        This serves as a general proxy of how valuable its letters are
        in terms of gaining new information."""
        score = 0
        for letter in self.letters:
            if letter in THREE_POINT_LETTERS:
                score += 3
            elif letter in TWO_POINT_LETTERS:
                score += 2
            elif letter in ONE_POINT_LETTERS:
                score += 1

        return score


class Mask:
    """A Mask represents a set of filtering criteria that gets applied
    to a set of Words."""

    correct_positions: dict[Position, Letter] # Greens; Letters that must appear in a certain position
    incorrect_positions: dict[Position, set[Letter]] # Yellows; Letters that must NOT appear in a certain position
    incorrect_globals: set[Letter] # Blacks; Letters that must NOT appear anywhere

    correct_letters: set[Letter] #

    def __init__(
        self,
        correct_positions: Optional[dict[Position, Letter]] = None,
        incorrect_positions: Optional[dict[Position, set[Letter]]] = None,
        incorrect_globals: Optional[set[Letter]] = None,
    ) -> None:
        """Parse the inputs and set up the data structures."""

        self.correct_positions = correct_positions if correct_positions else {}
        self.incorrect_positions = {
            position: letters
            for position, letters in incorrect_positions.items()
            if letters
        } if incorrect_positions else {}
        self.incorrect_globals = incorrect_globals if incorrect_globals else set()

        self.correct_letters = (
            set(self.correct_positions.values())
            .union(*self.incorrect_positions.values())
        )

    def __str__(self) -> str:
        return "Word must have " + " and ".join(
            [f"{l} in position {p}" for p, l in self.correct_positions.items()]
            + [f"not {l} in position {p}" for p, ls in self.incorrect_positions.items() for l in ls]
            + [f"{l} nowhere" for l in self.incorrect_globals]
        )

    def __repr__(self) -> str:
        return _universal_repr(self)

    def __eq__(self, other: "Mask") -> bool:
        return all([
            self.correct_positions == other.correct_positions,
            self.incorrect_positions == other.incorrect_positions,
            self.incorrect_globals == other.incorrect_globals,
        ])

    def __add__(self, other: "Mask") -> "Mask":
        """This combines two Masks together to yield a new Mask
        that incorporates the information from both."""

        base_error_message = "These two Masks are incompatible and cannot be combined together! "

        # Check to make sure that the two Masks don't require different letters in the same position
        if conflicts := [
            pos for pos, letter in self.correct_positions.items()
            if pos in other.correct_positions
            and other.correct_positions[pos] != letter
        ]:
            raise ValueError(
                base_error_message
                + f"The Masks require different letters to be in the following positions: {conflicts}"
            )

        # Check to make sure that the two Masks don't conflict on wanting / not wanting any letters
        if conflicts := (
            (set(self.correct_positions.values()) ^ other.incorrect_globals)
            | (set(other.correct_positions.values()) ^ self.incorrect_globals)
        ):
            raise ValueError(
                base_error_message
                + f"The following letters are wanted by one Mask and unwanted by another: {conflicts}"
            )

        incorrect_positions = self.incorrect_positions
        for pos, letters in other.incorrect_positions.items():
            incorrect_positions[pos] = self.incorrect_positions.get(pos, set()) | letters

        return Mask(
            correct_positions = self.correct_positions | other.correct_positions,
            incorrect_positions = incorrect_positions,
            incorrect_globals = self.incorrect_globals | other.incorrect_globals,
        )

    @classmethod
    def from_wordle_results(
        cls,
        guessed_word: str,
        wordle_results: str | Sequence[str],
    ):
        """This allows you to create a Mask from the results of a Wordle guess.
        `input_word` should be the string of the word you guessed.
        `wordle_results` should be a five-char string of either "G", "Y", or "B":
        - "G" for "green" (correct letter in correct place)
        - "Y" for "yellow" (correct letter in incorrect place)
        - "B" for "black (incorrect letter; does not appear in the word)
        """

        guessed_word = guessed_word.lower()
        if isinstance(wordle_results, str):
            wordle_results = list(wordle_results)
        wordle_results = [l.lower() for l in wordle_results]

        if len(wordle_results) != 5:
            raise ValueError("`wordle_results` must be a 5-char string or len-5 list of chars!")
        if bad_chars := set(wordle_results) - {"g", "y", "b"}:
            raise ValueError(f"`wordle_results` must only contain 'G/g', 'Y/y', or 'B/b', but found {bad_chars}!")

        correct_positions = {}
        incorrect_positions = {i: set() for i in range(1, 6)}
        incorrect_globals = set()

        for index in range(1, 6):
            guess_letter = guessed_word[index - 1]
            result = wordle_results[index - 1]

            if result == "g":
                correct_positions[index] = guess_letter
            elif result == "y":
                incorrect_positions[index].add(guess_letter)
            elif result == "b":
                incorrect_globals.add(guess_letter)
            else:
                raise ValueError(
                    "`wordle_results` must only contain "
                    f"'G/g', 'Y/y', or 'B/b', but found {result}!"
                )

        return cls(
            correct_positions = correct_positions,
            incorrect_positions = incorrect_positions,
            incorrect_globals = incorrect_globals,
        )

    def info_guess_version(self) -> "Mask":
        """An "informational guess version" of a Mask assumes that it's being used
        not to try to solve the Wordle, but to get as much information as possible,
        for use in an upcoming guess.

        This means that it will reverse its attitude towards the correct positions
        (the greens): those become actively unwanted, since we already have those
        positions understood, and instead of repeating those letters in those positions
        in this guess, we might be able to use those positions to learn about a different
        letter instead.

        However, we also want to make sure we don't try any of our incorrect positions
        in those positions, since we _know_ we won't find them there. So we extend the
        incorrect positions by adding an incorrect position entry at each of the known
        positions, with the incorrect letters being the set union of all our current
        incorrect-position letters."""

        return Mask(
            correct_positions = {},
            incorrect_positions = self.incorrect_positions | {
                position: set().union(*self.incorrect_positions.values())
                for position in self.correct_positions
            },
            incorrect_globals = self.incorrect_globals | set(self.correct_positions.values()),
        )

    def is_word_accepted(self, word: Word | str) -> bool:
        """This examines an input word and determines whether
        the word meets this Mask's filtering criteria."""

        if isinstance(word, str):
            word = Word(word)

        # If the word doesn't have all of the letters we want, reject it
        if not self.correct_letters.issubset(word.letters):
            return False

        # If the word has any of the letters we don't want, reject it
        if self.incorrect_globals.intersection(word.letters):
            return False

        # If the word doesn't have any of the specific position letters we want, reject it
        for position, letter in self.correct_positions.items():
            if word[position] != letter:
                return False

        # If the word has any of the specific position letters we don't want, reject it
        for position, letters in self.incorrect_positions.items():
            if word[position] in letters:
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

def pprint_filter_results(mask: Mask, words: Sequence[Word]) -> list[str]:
    """This pretty-prints the result of applying the provided Mask to the provided
    list of words."""
    filtered_words = sorted(
        mask.filter_words(words),
        key = lambda w: w.score,
        reverse = True,
    )

    return [
        f"{word.full_word} ({word.score})"
        for word in filtered_words[:MAX_PRINT_RESULTS]
    ]

def main():
    """Execute top-level functionality."""
    words = load_words("five_letter_words.txt") # pylint: disable = unused-variable
    mask = Mask(
        correct_positions = {},
        incorrect_positions = {3: {"a"}, 4: {"t"}},
        incorrect_globals = set("sle"),
    )
    pprint_filter_results(mask, words)
    breakpoint() # pylint: disable = forgotten-debug-statement

if __name__ == "__main__":
    main()
