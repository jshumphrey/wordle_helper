#!/usr/bin/python
"""This is a simple script to help output valid Wordle words that might make
good guesses, based on the feedback received about previous guesses."""

import textwrap  # Used to pretty-print long blocks of text so that they appear nicely
import typing  # Used for type-checking throughout the script
from typing import Any, Callable, Iterator, Sequence, Optional, Self
from tqdm import tqdm  # Used to display progress bars for long-running operations

Position = int
Letter = str

WORDS_FILENAME = "five_letter_words.txt"
MAX_PRINT_RESULTS = 15  # The default number of words to print out in the suggestion table.

# This is precompiled and stored globally because it'll be used often,
# and because it's the frequencies for the entire word list (i.e. it's expensive).
# Frequency plots for smaller lists can be calculated at runtime as needed.
GLOBAL_LETTER_FREQUENCIES = {
    'a': 0.07927, 'b': 0.02503, 'c': 0.03363, 'd': 0.04408, 'e': 0.10927, 'f': 0.01983,
    'g': 0.02434, 'h': 0.02705, 'i': 0.05654, 'j': 0.00340, 'k': 0.02093, 'l': 0.05457,
    'm': 0.02880, 'n': 0.04527, 'o': 0.06496, 'p': 0.03170, 'q': 0.00212, 'r': 0.06777,
    's': 0.10738, 't': 0.05466, 'u': 0.03754, 'v': 0.01132, 'w': 0.01771, 'x': 0.00474,
    'y': 0.02360, 'z': 0.00446,
}

# This is a set of words that end in "-es" but are still valid words.
VALID_FAUX_PLURAL_WORDS = {
    "apres", "bakes", "bares", "bases", "bides", "blues", "bodes", "bores", "bowes",
    "cares", "cedes", "cites", "comes", "copes", "cries", "dazes", "dices", "dines",
    "dotes", "doxes", "dozes", "eases", "gives", "gores", "hades", "hates", "hazes",
    "hones", "hypes", "idles", "lases", "loses", "makes", "maxes", "metes", "mixes",
    "mopes", "mutes", "nixes", "ogles", "pales", "pares", "paves", "plies", "pokes",
    "pries", "rares", "rases", "riles", "rises", "roves", "sates", "shies", "tames",
    "tares", "tases", "vexes", "wades", "wakes", "wanes", "wises"
}

class Word:
    """A Word represents a single valid Wordle word.
    Words also define a number of data structures to make comparison faster."""

    full_word: str
    letters: set[Letter]

    positions: dict[int, Letter]  # Position indices START AT 1
    letter_counts: dict[Letter, int]  # Dict of {letter: count of occurrences}

    score: float

    def __init__(self, full_word: str) -> None:
        if len(full_word) != 5:
            raise ValueError("Words must have exactly five letters!")

        self.full_word = full_word
        self.letters = set(full_word)

        self.positions = dict(enumerate(full_word, start = 1))
        self.letter_counts = {letter: self.full_word.count(letter) for letter in self.letters}

        self.score = self.calculate_score()

    def __str__(self) -> str:
        return self.full_word

    def __repr__(self) -> str:
        return (
            f"<wordle_helper.Word at {hex(id(self))}: "
            f"full_word: {self.full_word}"
            f", score: {self.score}"
            f">"
        )

    def __eq__(self, other: Self) -> bool:
        return self.full_word == other.full_word

    def __getitem__(self, position: int) -> Letter:
        return self.positions[position]

    def __contains__(self, letter: Letter) -> bool:
        return letter in self.letters

    def __key(self):
        return self.full_word

    def __hash__(self):
        return hash(self.__key())

    def calculate_score(self, frequency_dict: Optional[dict[Letter, float]] = None) -> float:
        """This calculates a word's "score" from the scores of its letters.
        This serves as a general proxy of how valuable its letters are
        in terms of gaining new information."""

        if frequency_dict is None:
            frequency_dict = GLOBAL_LETTER_FREQUENCIES

        return round(sum(frequency_dict[letter] for letter in self.letters) * 100, 3)

    def calculate_guess_results(self, guessed_word: Self) -> str:
        """This takes in a guessed word and returns the Wordle results string.
        In other words, this pretends that this Word is being used as the target
        word in a Wordle game, and the guessed word is an attempt to solve the Wordle.

        With that in mind, this function returns the "guess results" string in the same
        format as used in interactive_prompt or in Mask.from_wordle_results - a five-char
        string composed of "g", "y", or "b", one for each letter in the guessed word.

        One quirk about Wordle results involves words with multiple instances of the same letter.

        If the target word is "teeth", and the user guesses "genie", the results will be "bgbby".
        Note that the second "e" in "genie" gets a "y": even though it's in the wrong place,
        there _is_ a second "e" in the word that needs to be guessed, so it doesn't get a "b".

        On the other hand, if the guess was "epees", the results would be "ybgbb".
        There is no _third_ "e" in the target word, so that third "e" gets a "b".

        To handle this, the `used_counts` dict keeps track of how many times we've processed
        each letter in the guessed word, so that we can start assigning "b"s once we've
        "used up" the occurrences of that letter in the target word."""

        used_counts = {}
        results = ""

        for position, letter in guessed_word.positions.items():
            if letter in self:
                if self[position] == letter:  # Match at this position
                    results += "g"

                else:  # Letter is in the word, but the position is wrong
                    if used_counts.get(letter, 0) < self.letter_counts[letter]:
                        results += "y"  # There's still occurrences left, so assign "y"
                    else:
                        results += "b"  # We've used up all the occurrences, so assign "b"

                used_counts[letter] = used_counts.get(letter, 0) + 1

            else:  # Letter not in this word at all
                results += "b"

        return results


class WordList:
    """A WordList represents a list of Words, and provides a number of functions
    to assist in working with groups of Words (rather than individually).

    Note that WordLists are named WordLISTS for a reason (as opposed to WordSets):
    they are ordered collections, and x in WordList is O(n)."""

    _words: list[Word]
    letter_frequency: dict[Letter, float]

    def __init__(self, words: Sequence[Word | str]) -> None:
        self._words = [Word(w) if isinstance(w, str) else w for w in words]

        # It might seem weird to go ahead and calculate the letter frequency
        # for all new WordLists, but in practice, this gets used a _ton_,
        # and it's honestly better to just calculate it at the beginning and
        # cache it for later. Sooner or later, we're _going_ to need it,
        # and calculating it is O(self._words), so should just do it once.
        self.letter_frequency = self.calculate_letter_frequency()

    def __str__(self) -> str:
        return f"WordList containing {len(self)} words"

    def __repr__(self) -> str:
        return (
            f"<wordle_helper.WordList at {hex(id(self))}: "
            f"_words: {[str(w) for w in self._words]}"
            f", letter_frequency: {self.letter_frequency}"
            f">"
        )

    def __bool__(self) -> bool:
        return self._words != []

    def __eq__(self, other: Self) -> bool:
        return set(self) == set(other)

    def __contains__(self, word: Word) -> bool:
        return word in self._words

    def __len__(self) -> int:
        return len(self._words)

    def __iter__(self) -> Iterator[Word]:
        yield from self._words

    def __add__(self, other: Self) -> Self:
        """Using dict.fromkeys preserves the insert order of the combined list,
        while removing duplicates."""
        return WordList(list(dict.fromkeys(self._words + other._words)))

    def __radd__(self, other: Self) -> Self:
        return other.__add__(self)

    @typing.overload
    def __getitem__(self, key: slice) -> Self:
        pass

    @typing.overload
    def __getitem__(self, key: int) -> Word:
        pass

    def __getitem__(self, key):
        if isinstance(key, slice):
            return WordList(self._words[key])

        if isinstance(key, int):
            return self._words[key]

        raise TypeError(
            "WordList.__getitem__ expects keys that are integers or slices, "
            f"but got {type(key)} instead!"
        )

    @classmethod
    def from_file(cls, filename: str) -> Self:
        """This sets up a WordList by reading Words from a text file."""
        with open(filename, "r", encoding = "utf-8") as infile:
            return cls([line.strip() for line in infile.readlines() if line])

    def copy(self) -> Self:
        """This returns a deep copy of this WordList."""
        return WordList(self._words[:])

    def sort(
        self,
        sort_function: Callable[[Word], Any],
        reverse: bool = False,
    ) -> None:
        """This sorts self._words according to the provided callable."""
        self._words.sort(key = sort_function, reverse = reverse)

    def frequency_sort(self) -> None:
        """This is a common special case for sorting a WordList, where we want to sort
        the WordList by the scores of its Words, where those scores are calculated
        based on this WordList's letter-frequency distribution, and in descending
        order of those scores (i.e. highest scores first)."""

        self.sort(
            sort_function = lambda w: w.calculate_score(self.letter_frequency),
            reverse = True
        )

    def calculate_best_freqsort_word(self) -> Word:
        """This encapsulates a common use-case for a WordList: getting the single Word
        with the highest score according to this WordList's letter frequency."""
        self.frequency_sort()
        return self[0]

    def apply_masks(self, masks: list["Mask"]) -> Self:
        """This returns a WordList of all of the Words in this WordList
        that meet ALL of the filtering criteria in the provided Masks."""

        # Trivial cases: 0 or 1 masks
        if not masks:
            return self
        if len(masks) == 1:
            return masks[0].filter_words(self)

        # If we have multiple masks, add them all together before filtering ONCE
        total_mask = masks[0]
        for mask in masks[1:]:
            total_mask += mask
        return total_mask.filter_words(self)

    def calculate_letter_frequency(self) -> dict[Letter, float]:
        """This runs a frequency analysis on all of the letters in the provided word list.
        It returns a dict that maps each letter to a percentage of that letter's
        representation across the entire word list. All letters are included in the dict,
        but their percentage value might be zero if the letter did not appear in the list.
        The percentages are expressed as float values (i.e. 0.0535 = 5.35%)."""

        total_num_letters = len(self) * 5  # Shortcut since we know all words have 5 letters

        # Instantiating letters this way guarantees that we have an entry for every letter,
        # including letters that don't appear in any of this WordList's words
        letters = {chr(letter_int): 0 for letter_int in range(ord("a"), ord("z") + 1)}

        if not self._words:
            return {letter: 0.0 for letter in letters.keys()}

        for word in self:
            for letter in word.full_word:
                letters[letter] += 1

        return {
            letter: round(count / total_num_letters, 5)
            for letter, count in letters.items()
        }

    def pprint(self, num_words: int = MAX_PRINT_RESULTS) -> None:
        """This pretty-prints a list of Words for display to the console.
        The Words will be printed in the order they appear in `self._words`,
        so if they need to be sorted before printing them, you'll need to
        do that beforehand. Only a certain number of them are displayed."""

        print()
        print(f"Found {len(self)} total words; here are the top {num_words} of them.")
        print("  ".join(["Word ", "Score (These Words)", "Score (All Words)"]))
        print("  ".join(["-----", "-------------------", "-----------------"]))
        for word in self[:num_words]:
            print("  ".join([
                word.full_word,
                str(word.calculate_score(self.letter_frequency)).ljust(19, " "),
                str(word.score),
            ]))
        print()


class Mask:
    """A Mask represents a set of filtering criteria that gets applied to a WordList."""

    correct_positions: dict[Position, Letter]  # Greens; Letters that must appear in a certain position
    incorrect_positions: dict[Position, set[Letter]]  # Yellows; Letters that must NOT appear in a certain position
    incorrect_globals: set[Letter]  # Blacks; Letters that must NOT appear anywhere

    # A set of letters that must appear somewhere in the word.
    # This gets calculated during __init__ - it's essentially "greens plus yellows".
    correct_letters: set[Letter]

    # A dict of letter: number of occurrences. For words that repeat letters,
    # we need to be able to store information about how many times those letters
    # are allowed to occur.
    max_occurrences: dict[Letter, Position]

    def __init__(
        self,
        correct_positions: Optional[dict[Position, Letter]] = None,
        incorrect_positions: Optional[dict[Position, set[Letter]]] = None,
        incorrect_globals: Optional[set[Letter]] = None,
        max_occurrences: Optional[dict[Letter, Position]] = None,
    ) -> None:
        """Parse the inputs and set up the data structures."""

        self.correct_positions = correct_positions if correct_positions else {}
        self.incorrect_positions = {
            position: letters
            for position, letters in incorrect_positions.items()
            if letters
        } if incorrect_positions else {}
        self.incorrect_globals = incorrect_globals if incorrect_globals else set()
        self.max_occurrences = max_occurrences if max_occurrences else {}

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
        return (
            f"<wordle_helper.Mask at {hex(id(self))}: "
            f"correct_positions: {self.correct_positions}"
            f", incorrect_positions: {self.incorrect_positions}"
            f", incorrect_globals: {self.incorrect_globals}"
            f", max_occurrences: {self.max_occurrences}"
            f">"
        )

    def __eq__(self, other: Self) -> bool:
        return all([
            self.correct_positions == other.correct_positions,
            self.incorrect_positions == other.incorrect_positions,
            self.incorrect_globals == other.incorrect_globals,
        ])

    def __add__(self, other: Self) -> Self:
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
            (set(self.correct_positions.values()) & other.incorrect_globals)
            | (set(other.correct_positions.values()) & self.incorrect_globals)
        ):
            raise ValueError(
                base_error_message
                + f"The following letters are wanted by one Mask and unwanted by another: {conflicts}"
            )

        # Check to make sure that the two masks don't disagree on how many times letters can occur
        if conflicts := [
            letter for letter, max_occurrences in self.max_occurrences.items()
            if letter in other.max_occurrences
            and other.max_occurrences[letter] != max_occurrences
        ]:
            raise ValueError(
                base_error_message
                + f"The Masks disagree on how many times the following letters may occur: {conflicts}"
            )

        incorrect_positions = self.incorrect_positions
        for pos, letters in other.incorrect_positions.items():
            incorrect_positions[pos] = self.incorrect_positions.get(pos, set()) | letters

        return Mask(
            correct_positions = self.correct_positions | other.correct_positions,
            incorrect_positions = incorrect_positions,
            incorrect_globals = self.incorrect_globals | other.incorrect_globals,
            max_occurrences = self.max_occurrences | other.max_occurrences,
        )

    def __radd__(self, other: Self) -> Self:
        return self.__add__(other)

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
        max_occurrences = {}

        for index in range(1, 6):
            guess_letter = guessed_word[index - 1]
            result = wordle_results[index - 1]

            if result == "g":
                correct_positions[index] = guess_letter

            elif result == "y":
                incorrect_positions[index].add(guess_letter)

            # This one is more difficult. If the guessed word contains more than one occurrence
            # of the letter, this "b" might be due to previous occurrences getting a "g" or "y",
            # but the guess_word doesn't have this many occurrences of guess_letter.
            # As a result, we need to check a couple of things before we can safely ban guess_letter.
            elif result == "b":
                # Get a list of the indices that guess_letter appears in guess_word
                indices = [i for i, l in enumerate(guessed_word) if l == guess_letter]

                # If the letter only shows up once, ban it
                if len(indices) == 1:
                    incorrect_globals.add(guess_letter)

                # If the letter gets a "b" every time it shows up, ban it
                elif all(wordle_results[i] == "b" for i in indices):
                    incorrect_globals.add(guess_letter)

                else:
                    if guess_letter not in max_occurrences:
                        max_occurrences[guess_letter] = len([
                            i for i in indices
                            if wordle_results[i] != "b"
                        ])

                    else: # We don't need to reprocess this letter.
                        pass

            else:
                raise ValueError(
                    "`wordle_results` must only contain "
                    f"'G/g', 'Y/y', or 'B/b', but found {result}!"
                )

        return cls(
            correct_positions = correct_positions,
            incorrect_positions = incorrect_positions,
            incorrect_globals = incorrect_globals,
            max_occurrences = max_occurrences,
        )

    def info_guess_version(self) -> Self:
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

        word = word if isinstance(word, Word) else Word(word)

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

        # If we have any letters that can only occur a certain number of times,
        # and the word uses those letters more than we allow, reject it
        for letter, max_occurrences in self.max_occurrences.items():
            if letter not in word:
                return False
            if word.letter_counts[letter] > max_occurrences:
                return False

        # If none of the rejection criteria apply, accept the word by returning True.
        return True

    def filter_words(self, words: WordList) -> WordList:
        """This applies this Mask to an entire sequence of input Words."""
        return WordList([word for word in words if self.is_word_accepted(word)])


def print_help() -> None:
    """This prints out some instructional text on how to use the interactive prompt."""
    wrapper = textwrap.TextWrapper(fix_sentence_endings = True, replace_whitespace = False)
    print()
    with open("README.md", "r", encoding = "utf-8") as infile:
        for line in infile.readlines():
            print(wrapper.fill(line))
    print()


def solve_wordle(
    target_word: Word | str,
    all_words: WordList,
    starting_word: Optional[Word] = None,
    print_output: bool = False,
) -> int:
    """This attempts to solve the Wordle whose target is target_word, based on
    the provided list of possible words. It returns the number of guesses it took
    to solve the Wordle.

    The goal for the solver is to maximise the amount of 3-guess solves, since
    1-guess and 2-guess solves are mostly a result of blind luck. As a result,
    the first two guesses are "informational" guesses (see Mask.info_guess_version),
    and guesses from the third guess onward are "solve" guesses.

    If desired, an alternative initial guess can be provided with the
    `starting_word` parameter."""

    target_word = Word(target_word) if isinstance(target_word, str) else target_word
    num_guesses = 0
    masks = []

    possible_words = all_words.copy() # Need to be careful not to modify all_words
    guess_word = starting_word if starting_word else possible_words.calculate_best_freqsort_word()

    while True:
        num_guesses += 1

        # See if we've correctly guessed the word
        if guess_word == target_word:
            if print_output:
                print(f"Guess #{num_guesses}: Guessed '{guess_word}' and solved the Wordle!")
            return num_guesses

        # If we're wrong, identify the new guess word and go again.
        guess_results = target_word.calculate_guess_results(guess_word)
        masks.append(Mask.from_wordle_results(guess_word.full_word, guess_results))

        possible_words = possible_words.apply_masks(masks)
        info_words = possible_words.apply_masks([m.info_guess_version() for m in masks])
        if print_output:
            print(
                f"Guess #{num_guesses}: Guessed '{guess_word}' and got '{guess_results}'; "
                f"{len(possible_words)} possible words left"
            )

        # Check to make sure we're not in an "impossible situation"; raise if so.
        if not possible_words or (len(possible_words) == 1 and possible_words != [target_word]):
            raise RuntimeError(
                f"Stuck in impossible situation when trying to solve the word '{target_word}'! "
                f"Current masks: {[str(m) for m in masks]}; "
                f"current possible words: {[str(w) for w in possible_words]}"
            )

        if len(possible_words) >= 20 and len(info_words) >= 10:
            guess_word = info_words.calculate_best_freqsort_word()
        else:
            guess_word = possible_words.calculate_best_freqsort_word()


def solve_all_wordles(words: WordList) -> None:
    """This attempts to solve all possible Wordles, based on the script's
    suggested words. At the end, statistics are printed about the numbers of
    guesses it took to solve each word."""

    results: dict[Word, int] = {}  # Stores the number of guesses it took to solve the Word

    # Precalculate the starting word to avoid having to redo it for each target word.
    starting_word = words.calculate_best_freqsort_word()
    for word in tqdm(words, desc = "Playing all Wordles"):
        results[word] = solve_wordle(
            target_word = word,
            all_words = words,
            starting_word = starting_word
        )

    solve_counts = {n: 0 for n in range(1, 8)}
    max_guesses = 0
    max_guess_words = []

    for word, guesses in results.items():
        if guesses > max_guesses:
            max_guesses = guesses
            max_guess_words = [word]
        elif guesses == max_guesses:
            max_guess_words.append(word)
        solve_counts[min(guesses, 7)] += 1

    print()
    print("Successfully solved all Wordles.")
    for n in range(1, 8):  # pylint: disable = invalid-name
        percent = round((solve_counts[n] / len(words)) * 100, 2)
        pprint_n = str(n) if n < 7 else "more than 6"
        print(f"Words solved in {pprint_n} guesses: {solve_counts[n]} ({percent}%)")
    print()
    print(f"Highest number of guesses to solve: {max_guesses}")
    print(
        f"Words that took {max_guesses} guesses to solve: "
        + ", ".join([str(w) for w in max_guess_words[:5]])
    )
    print()


def interactive_prompt() -> None:
    """This provides an interactive prompt that helps to make use of this script."""

    words: WordList = WordList.from_file(WORDS_FILENAME)
    masks: list[Mask] = []

    while True:
        match (command := input("Enter a command ('h' for help, 'q' to quit): ")).lower().split():
            # Exit the script
            case ["quit"] | ["exit"] | ["quit()"] | ["q"]:
                return

            # Print out some help text
            case ["help"] | ["h"] | ["?"]:
                print_help()

            # Drop to the debug console
            case ["debug"] | ["breakpoint"]:
                breakpoint()  # pylint: disable = forgotten-debug-statement

            # Reload the word list from the file, in case it's been changed during runtime.
            case ["reload"]:
                words = WordList.from_file(WORDS_FILENAME)
                print("Word list reloaded from file.")

            # Allow the user to view and/or clear the list of current Masks.
            case ["masks"] | ["guesses"] | ["filters"]:
                print([str(mask) for mask in masks])
            case ["reset"]:
                masks = []
                print("Guess list cleared.")

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

                result_words = words.apply_masks(suggest_masks)
                if not result_words:
                    if suggest_type == "info":
                        print("No result words found! You might want to try 'suggest solve' instead.")
                    else:
                        print("No result words found! Make sure you entered everything correctly.")

                else:
                    result_words.frequency_sort()
                    result_words.pprint()

            # Allow the user to tell the script to try to automatically solve Wordles.
            case ["autosolve", "all"]:
                solve_all_wordles(words)
            case ["autosolve", word]:
                solve_wordle(Word(word), words, print_output = True)

            case _:
                print(f"Unknown command: {command}")


if __name__ == "__main__":
    interactive_prompt()
