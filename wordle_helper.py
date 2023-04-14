#!/usr/bin/python
"""This is a simple script to help output valid Wordle words that might make
good guesses, based on the feedback received about previous guesses."""

from typing import Iterator, Optional, Sequence

Letter = str
LettersInput = str | list[Letter] | set[Letter] | tuple[Letter]

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

    wanted_letters: set[Letter] # Letters that must appear somewhere
    unwanted_letters: set[Letter] # Letters that must NOT appear anywhere
    wanted_positions: dict[int, Letter] # Letters that must appear in a certain position
    unwanted_positions: dict[int, set[Letter]] # Letters that must NOT appear in a certain position

    # "Ignored wanted letters" are a weird case, specifically to give Masks a way to
    # "pass information" to one another. You might make a Wordle guess that doesn't
    # make use of some green letters that you know are there, because you'd rather
    # get more information about letters you don't already know about.
    #
    # Since this Mask might be combined with another Mask later on, we want to be able to
    # indicate that this Mask _did_ know about these green letters, but chose not to use them.
    # Thus, ignored_wanted_positions stores those green letters for later use.
    ignored_wanted_positions: dict[int, set[Letter]]

    def __init__(
        self,
        wanted_letters: Optional[LettersInput] = None,
        unwanted_letters: Optional[LettersInput] = None,
        wanted_positions: Optional[dict[int, Letter]] = None,
        unwanted_positions: Optional[dict[int, LettersInput]] = None,
        ignored_wanted_positions: Optional[dict[int, LettersInput]] = None,
    ) -> None:
        """Parse the input word and set up the data structures."""

        self.wanted_letters = set(wanted_letters) if wanted_letters else set()
        self.unwanted_letters = set(unwanted_letters) if unwanted_letters else set()

        if wanted_positions:
            self.wanted_positions = {
                pos: letter
                for pos, letter in wanted_positions.items()
                if letter
            }
            self.wanted_letters |= set(self.wanted_positions.values())
        else:
            self.wanted_positions = {}

        if unwanted_positions:
            self.unwanted_positions = {
                pos: set(letters)
                for pos, letters in unwanted_positions.items()
                if letters
            }
            # Do NOT add unwanted_positions to unwanted_letters, because that's not how that works
        else:
            self.unwanted_positions = {}

        if ignored_wanted_positions:
            self.ignored_wanted_positions = {
                pos: set(letters)
                for pos, letters in ignored_wanted_positions.items()
                if letters
            }
        else:
            self.ignored_wanted_positions = {}

    def __str__(self) -> str:
        output = []

        output.append(*[f"{letter} somewhere" for letter in self.wanted_letters])
        output.append(*[f"{letter} nowhere" for letter in self.unwanted_letters])
        output.append(*[
            f"{letter} in position {position}"
            for position, letter_set in self.wanted_positions.items()
            for letter in letter_set
        ])
        output.append(*[
            f"not {letter} in position {position}"
            for position, letter_set in self.unwanted_positions.items()
            for letter in letter_set
        ])

        return "Word must have " + " and ".join(output)

    def __repr__(self) -> str:
        return _universal_repr(self)

    def __eq__(self, other: "Mask") -> bool:
        return all([
            self.wanted_letters == other.wanted_letters,
            self.unwanted_letters == other.unwanted_letters,
            self.wanted_positions == other.wanted_positions,
            self.unwanted_positions == other.unwanted_positions,
        ])

    def __add__(self, other: "Mask") -> "Mask":
        """This combines two Masks together to yield a new Mask
        that incorporates the information from both."""

        base_error_message = "These two Masks are incompatible and cannot be combined together! "

        # Check to make sure that the two Masks don't require different letters in the same position
        if conflicts := [
            pos for pos, letter in self.wanted_positions.items()
            if pos in other.wanted_positions
            and other.wanted_positions[pos] != letter
        ]:
            raise ValueError(
                base_error_message
                + f"Both Masks require different letters to be in the following positions: {conflicts}"
            )

        # Check to make sure that the two Masks don't conflict on wanting / not wanting any letters
        if conflicts := (
            (self.wanted_letters ^ other.unwanted_letters)
            | (self.unwanted_letters ^ other.wanted_letters)
        ):
            raise ValueError(
                base_error_message
                + f"The following letters are wanted by one Mask and unwanted by another: {conflicts}"
            )

        unwanted_positions = self.unwanted_positions
        for pos, letters in other.unwanted_positions.items():
            unwanted_positions[pos] = self.unwanted_positions.get(pos, set()) | letters

        ignored_wanted_positions = self.ignored_wanted_positions
        for pos, letters in other.unwanted_positions.items():
            ignored_wanted_positions[pos] = self.ignored_wanted_positions.get(pos, set()) | letters

        return Mask(
            wanted_letters = self.wanted_letters | other.wanted_letters,
            unwanted_letters = self.unwanted_letters | other.unwanted_letters,
            wanted_positions = self.wanted_positions | other.wanted_positions,
            unwanted_positions = unwanted_positions,
            ignored_wanted_positions = ignored_wanted_positions,
        )

    @classmethod
    def from_wordle_results(
        cls,
        guessed_word: str,
        wordle_results: str | Sequence[str],
        ignore_greens: bool = False,
    ):
        """This allows you to create a Mask from the results of a Wordle guess.
        `input_word` should be the string of the word you guessed.
        `wordle_results` should be a five-char string of either "G", "Y", or "B":
        - "G" for "green" (correct letter in correct place)
        - "Y" for "yellow" (correct letter in incorrect place)
        - "B" for "black (incorrect letter; does not appear in the word)

        The `ignore_greens` parameter dictates whether or not green letters should be
        ignored; if True, green letters will not be added to Mask.wanted_letters or
        Mask.wanted_positions. You might want to do this if you'd rather gather information
        about which letters might also be in the word, instead of trying to solve the puzzle
        with this guess."""

        guessed_word = guessed_word.lower()
        if isinstance(wordle_results, str):
            wordle_results = list(wordle_results)
        wordle_results = [l.lower() for l in wordle_results]

        if len(wordle_results) != 5:
            raise ValueError("`wordle_results` must be a 5-char string or len-5 list of chars!")
        if bad_chars := set(wordle_results) - {"g", "y", "b"}:
            raise ValueError(f"`wordle_results` must only contain 'G/g', 'Y/y', or 'B/b', but found {bad_chars}!")

        wanted_letters = []
        unwanted_letters = []
        wanted_positions: dict[int, Letter] = {}
        unwanted_positions: dict[int, list[Letter]] = {i: [] for i in range(1, 6)}

        for index in range(1, 6):
            guess_letter = guessed_word[index - 1]
            result = wordle_results[index - 1]

            if result == "g":
                if ignore_greens is False:
                    wanted_positions[index] = guess_letter
                else:
                    unwanted_letters.append(guess_letter)

            elif result == "y":
                wanted_letters.append(guess_letter)
                unwanted_positions[index].append(guess_letter)

            elif result == "b":
                unwanted_letters.append(guess_letter)

            else:
                raise ValueError(f"`wordle_results` must only contain 'G/g', 'Y/y', or 'B/b', but found {result}!")

        return cls(
            wanted_letters,
            unwanted_letters,
            wanted_positions,
            unwanted_positions,
        )

    def is_word_accepted(self, word: Word | str) -> bool:
        """This examines an input word and determines whether
        the word meets this Mask's filtering criteria."""

        if isinstance(word, str):
            word = Word(word)

        # If the word doesn't have any of the letters we want, reject it
        if self.wanted_letters and not self.wanted_letters.issubset(word.letters):
            return False

        # If the word has any of the letters we don't want, reject it
        combined_unwanted_letters = set().union(self.unwanted_letters, self.ignored_wanted_positions)
        if combined_unwanted_letters and combined_unwanted_letters.intersection(word.letters):
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
    mask = Mask("at", "sle", {}, {3: "a", 4: "t"})
    pprint_filter_results(mask, words)
    breakpoint() # pylint: disable = forgotten-debug-statement

if __name__ == "__main__":
    main()
