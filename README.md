
## nodebot

### architecture

nodebot enables the communication between your own Lighter node and your telegram account. With nodebot you can use your Lightning Network node as mobile wallet.

moreover, it shows the gRPC output in a human readable format.

the backend of nodebot will connect to Lighter. You will need to deploy nodebot on a server, for example it could share the host of Lighter.

your deploy of nodebot is personal, and your Teleram bot too.

for this reason you have to register your own telegram bot through [@BotFather](https://telegram.me/BotFather).

### use the bot

go to [INSTALL.md](INSTALL.md) to get information about installation and configuration.

### features

* pay an invoice
* get the walletbalance and the channelbalance
* 1ml and lightblock exlorer links are provided
* check a payment status
* get information about the node
* list the channels
* create an invoice
* get the node uri
* generate a new bech32 bitcoin address
* decode a payment request
