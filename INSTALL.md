## system requirements

* a running Lighter node.
* we use Zbar to work with qr codes. The Debian package is `libzbar0`, and the Arch Linux one is `zbar`
* other requirements are specified into the `requirements.txt` file

## bot setup

### register on Telegram

contact the [@BotFather](https://telegram.me/BotFather) on Telegram.

use the command

→ /newbot

set a name

→ a name

set a username (must match /^[\w_]*(B|b)(O|o)(T|t)$/)

→ a_username_for_the_bot

copy the provided API token (e.g. `1136891621:AABLkgdThOneiNwfBNX95_X5x3vXUVF0KnJ`)

### nodebot

configure the lighter section of config file. An example can be found in `config.sample`.

save the file as `config`.

start nodebot

→ $ ./bot.py

provide the API token

→ \> 1136891621:AABLkgdThOneiNwfBNX95_X5x3vXUVF0KnJ

contact the registered telegram bot, it will answer a message with a five digits number. Copy the nuber into the shell to complete the pairing.

start with the command `help`.