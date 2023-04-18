# wordle_helper.py

This script lets you get suggestions for Wordle guesses.

Run it from the command line with `python wordle_helper.py`, which will start an interactive prompt.

To display help information, use the `h` or `help` commands. To exit, use the `q` or `quit` commands. All other commands are detailed below.

## Getting suggestions

To get suggestions, use the `suggest` command.

For suggestions that try to solve the Wordle with this guess, use the command `suggest solve`. For suggestions that try to get more information (so you can try to solve the Wordle with a later guess), use the command `suggest info`.

`info` suggestions ignore words that contain any "green" letters (because we already know what's in those positions), and attempt to find the positions for any yellow letters, while trying as many new high-valued letters as possible.

## Adding guesses

To tell the script about words you've guessed, use the `add` command.

You can either use the simple command `add`, in which case the script will ask you for more information about what word you guessed, and what Wordle told you about your guess, or you can use the command `add [guessed_word] [results]` to do everything in one command.

To enter information about the results of your guess, enter a five-letter 'word', made up of the letters `G`, `Y`, or `B` - one letter for each colored square in the result of your guess, in the correct order. `G` for green, `Y` for yellow, `B` for black.

For example, if you guessed "slate", and Wordle showed you "green, green, black, black, yellow", you could input information about this guess by using the command `add slate ggbby`. You can then use `suggest` with `info` or `solve` to get suggestions that incorporate the results of your guess of "slate"; for example, you wouldn't be suggested the word "plane" anymore, because that word isn't possible.

## Resetting the guess list

If you've completed a Wordle and want to try a new one, or if you made a mistake when adding a guess, you can clear out the script's list of guesses with the `reset` command.