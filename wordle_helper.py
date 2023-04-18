#!/usr/bin/python
"""This is a simple script to help output valid Wordle words that might make
good guesses, based on the feedback received about previous guesses."""

from typing import Callable, Optional

Position = int
Letter = str

WORDS_FILENAME = "five_letter_words.txt"
MAX_PRINT_RESULTS = 15
GLOBAL_LETTER_FREQUENCIES = {
    'a': 0.07852,
    'b': 0.02495,
    'c': 0.03281,
    'd': 0.04359,
    'e': 0.10704,
    'f': 0.01983,
    'g': 0.02473,
    'h': 0.02681,
    'i': 0.05582,
    'j': 0.00362,
    'k': 0.02168,
    'l': 0.0541,
    'm': 0.02932,
    'n': 0.04544,
    'o': 0.06474,
    'p': 0.03246,
    'q': 0.00208,
    'r': 0.06624,
    's': 0.10532,
    't': 0.0541,
    'u': 0.03793,
    'v': 0.01113,
    'w': 0.01762,
    'x': 0.00464,
    'y': 0.03074,
    'z': 0.00477
}


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
    score: float

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

    def calculate_score(self, frequency_dict: Optional[dict[Letter, float]] = None) -> float:
        """This calculates a word's "score" from the scores of its letters.
        This serves as a general proxy of how valuable its letters are
        in terms of gaining new information."""

        if frequency_dict is None:
            frequency_dict = GLOBAL_LETTER_FREQUENCIES

        return round(sum(frequency_dict[letter] for letter in self.letters) * 100, 3)


class Mask:
    """A Mask represents a set of filtering criteria that gets applied
    to a set of Words."""

    correct_positions: dict[Position, Letter] # Greens; Letters that must appear in a certain position
    incorrect_positions: dict[Position, set[Letter]] # Yellows; Letters that must NOT appear in a certain position
    incorrect_globals: set[Letter] # Blacks; Letters that must NOT appear anywhere

    # A set of letters that must appear somewhere in the word.
    # This gets calculated during __init__ - it's essentially "greens plus yellows".
    correct_letters: set[Letter]

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
        wordle_results: str | list[str],
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

    def filter_words(self, words: list[Word]) -> list[Word]:
        """This applies this Mask to an entire sequence of input Words."""
        return [word for word in words if self.is_word_accepted(word)]


def load_words(word_list_filename: str) -> list[Word]:
    """This reads in the list of five-letter words from the input text file,
    and returns a set of Word objects; one for each word in the file."""
    with open(word_list_filename, "r", encoding = "utf-8") as infile:
        return [Word(line.strip()) for line in infile.readlines()]


def apply_masks(words: list[Word], masks: list[Mask]) -> list[Word]:
    """This applies an arbitrary number of Masks to an input list of Words."""
    output_words = []
    for mask in masks:
        output_words = mask.filter_words(output_words if output_words else words)
    return output_words


def sort_words(
        filtered_words: list[Word],
        sort_function: Optional[Callable[[Word], float]] = None,
        reverse: bool = True,
    ) -> list[Word]:
    """This sorts a list of Words according to their score."""

    return sorted(
        filtered_words,
        key = lambda w: sort_function(w) if sort_function else w.score,
        reverse = reverse,
    )


def pprint_words(words: list[Word], num_words: int = MAX_PRINT_RESULTS) -> None:
    """This pretty-prints a list of Words for display to the console.
    The Words will be printed in the order they appear in `words`, so if they need
    to be sorted before printing them, you'll need to do that beforehand.
    Only a certain number of them are displayed."""

    print()
    print("\t".join(["Word", "Score"]))
    print("\t".join(["-----", "------"]))
    for word in words[:num_words]:
        print("\t".join([word.full_word, str(word.score)]))
    print()


def calculate_letter_frequency(words: list[Word]) -> dict[Letter, float]:
    """This runs a frequency analysis on all of the letters in the provided word list.
    It returns a dict that maps each letter to a percentage of that letter's
    representation across the entire word list. All letters are included in the dict,
    but their percentage value might be zero if the letter did not appear in the list.
    The percentages are expressed as float values (i.e. 0.0535 = 5.35%)."""

    total_num_letters = len(words) * 5 # We can cheat since we know all words have 5 letters
    letters = {chr(letter_int): 0 for letter_int in range(ord("a"), ord("z") + 1)}

    for word in words:
        for letter in word.full_word:
            letters[letter] += 1

    return {
        letter: round(count / total_num_letters, 5)
        for letter, count in letters.items()
    }


def interactive_prompt() -> None:
    """This provides an interactive prompt that helps to make use of this script."""

    words: list[Word] = load_words(WORDS_FILENAME)
    masks: list[Mask] = []

    while True:
        match (command := input("Enter a command: ")).lower().split():
            # Execution-flow commands.
            case ["quit"] | ["exit"] | ["quit()"]: # Exit the script
                return
            case ["debug"] | ["breakpoint"]: # Drop to the debug console
                breakpoint() # pylint: disable = forgotten-debug-statement
            case ["help"]:
                pass # Todo

            # Reload the word list from the file, in case it's been changed during runtime.
            case ["reload"]:
                words = load_words(WORDS_FILENAME)
                print("Word list reloaded from file.")

            # Allow the user to view and/or clear the list of current Masks.
            case ["masks"]:
                print([str(mask) for mask in masks])
            case ["reset"]:
                masks = []
                print("Mask list cleared.")

            # Allow the user to add a Mask to the current list of Masks.
            case ["add"]:
                guess = input("Enter the word you guessed: ")
                result = input("Enter the result of your guess: ")
                masks.append(Mask.from_wordle_results(guess, result))
            case ["add", guess, result]:
                masks.append(Mask.from_wordle_results(guess, result))

            # Allow the user to generate suggestions based on the current list of masks.
            case ["suggest", ("solve" | "info") as suggest_type]:
                if suggest_type == "info":
                    suggest_masks = [m.info_guess_version() for m in masks]
                else:
                    suggest_masks = masks

                result_words = apply_masks(words, suggest_masks)
                sorted_words = sort_words(
                    result_words,
                    sort_function = (
                        lambda w: w.calculate_score(calculate_letter_frequency(result_words))
                    ),
                    reverse = True
                )
                pprint_words(sorted_words)

            case _:
                print(f"Unknown command: {command}")


if __name__ == "__main__":
    interactive_prompt()
