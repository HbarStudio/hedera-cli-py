import os
import sys
import cmd

from colorama import init, Fore, Back, Style
from dotenv import load_dotenv
from hedera import (
    Hbar,
    Client,
    PrivateKey,
    AccountId,
    AccountCreateTransaction,
    AccountDeleteTransaction,
    AccountBalanceQuery,
    TransferTransaction,
    TransactionId,
    TopicCreateTransaction,
    TopicId,
    TopicMessageSubmitTransaction,
    )
from ._version import version


class HederaCli(cmd.Cmd):
    use_rawinput = False  # if True, colorama prompt will not work on Windows
    intro = """
# =============================================================================
#  __   __            __
# |  | |  |          |  |
# |  |_|  | ____  ___|  | ____ __ __ _____
# |   _   |/ __ \/  _`  |/ __ \  '__/  _  `|
# |  | |  |  ___/  (_|  |  ___/  | |  (_|  |
# \__| |__/\____|\___,__|\____|__|  \___,__|
#
# :: hedera-cli :: v{}
# github.com/wensheng/hedera-cli-py
# =============================================================================
Type help or ? to list commands.\n""".format(version)

    def __init__(self, *args, **kwargs):
        init()  # colorama
        super().__init__(*args, **kwargs)
        if "HEDERA_OPERATOR_ID" in os.environ:
            self.operator_id = AccountId.fromString(os.environ["HEDERA_OPERATOR_ID"])
        else:
            self.operator_id = None
        if "HEDERA_OPERATOR_KEY" in os.environ:
            self.operator_key = PrivateKey.fromString(os.environ["HEDERA_OPERATOR_KEY"])
        else:
            self.operator_key = ""
        self.network = os.environ.get("HEDERA_NETWORK", "testnet")
        self.setup_network(self.network)
        if self.operator_id and self.operator_key:
            self.client.setOperator(self.operator_id, self.operator_key)
        self.set_prompt()

    def emptyline(self):
        "If this is not here, last command will be repeated"
        pass

    def set_prompt(self):
        if self.operator_id:
            self.prompt = Fore.YELLOW + '{}@['.format(self.operator_id.toString()) + Fore.GREEN + self.network + Fore.YELLOW + '] > ' + Style.RESET_ALL
        else:
            self.prompt = Fore.YELLOW + 'null@[' + Fore.GREEN + self.network + Fore.YELLOW + '] > ' + Style.RESET_ALL

    def do_exit(self, arg):
        'exit Hedera cli'
        exit()

    def do_setup(self, arg):
        'set operator id and key'
        # these doesn't work on Windows
        # acc_id = input(Fore.YELLOW + "Operator Account ID (0.0.xxxx): " + Style.RESET_ALL)
        # acc_key = input(Fore.YELLOW + "Private Key: " + Style.RESET_ALL)
        print(Fore.YELLOW + "Operator Account ID (0.0.xxxx): " + Style.RESET_ALL, end='')
        acc_id = input()
        print(Fore.YELLOW + "Private Key: " + Style.RESET_ALL, end='')
        acc_key = input()
        try:
            self.operator_id = AccountId.fromString(acc_id)
            self.operator_key = PrivateKey.fromString(acc_key)
            self.client.setOperator(self.operator_id, self.operator_key)
            print(Fore.GREEN + "operator is set up")
        except Exception:
            print(Fore.RED + "Invalid operator id or key")
        self.set_prompt()

    def setup_network(self, name):
        self.network = name
        if name == "mainnet":
            self.client = Client.forMainnet()
        elif name == "previewnet":
            self.client = Client.forPreviewnet()
        else:
            self.client = Client.forTestnet()


    def do_network(self, arg):
        'Switch network: available mainnet, testnet, previewnet'
        if arg == self.network:
            print(Fore.YELLOW + "no change")
            self.set_prompt()
            return

        if arg in ("mainnet", "testnet", "previewnet"):
            self.setup_network(arg)
            self.operator_id = None
            print(Fore.GREEN + "you switched to {}, you must do `setup` again!".format(arg))
        else:
            print(Fore.RED + "invalid network")
        self.set_prompt()

    def do_keygen(self, arg):
        'Generate a pair of private and public keys'
        prikey = PrivateKey.generate()
        print(Fore.YELLOW + "Private Key: " + Fore.GREEN + prikey.toString())
        print(Fore.YELLOW + "Public Key: " + Fore.GREEN + prikey.getPublicKey().toString())
        self.set_prompt()

    def do_topic(self, arg):
        """HCS Topic: create send
Create Topic:
    topic create [memo]
Send message:
    topic send topic_id message [[messages]]"""
        args = arg.split()
        if not args or args[0] not in ('create', 'send'):
            print(Fore.RED + "invalid topic command")
            self.set_prompt()
            return

        if args[0] == "create":
            txn = TopicCreateTransaction()
            if len(args) > 1:
                memo = " ".join(args[1:])
                txn.setTopicMemo(memo)
            try:
                receipt = txn.execute(self.client).getReceipt(self.client)
                print("New topic created: ", receipt.topicId.toString())
            except Exception as e:
                print(e)
        else:
            if len(args) < 3:
                print(Fore.RED + "need topicId and message")
            else:
                try:
                    topicId = TopicId.fromString(args[1])
                    txn = (TopicMessageSubmitTransaction()
                           .setTopicId(topicId)
                           .setMessage(" ".join(args[2:])))
                    receipt = txn.execute(self.client).getReceipt(self.client)
                    print("message sent, sequence #: ", receipt.topicSequenceNumber)
                except Exception as e:
                    print(e)
        self.set_prompt()

    def do_account(self, arg):
        """account: create | balance | delete | info
Create account:
    account create
account balance:
    account balance [accountid]"""
        args = arg.split()
        if not args or args[0] not in ('create', 'balance', 'delete', 'info'):
            print(Fore.RED + "invalid account command")
            self.set_prompt()
            return

        if args[0] == "balance":
            try:
                if len(args) > 1:
                    accountId = AccountId.fromString(args[1])
                else:
                    accountId = self.operator_id
                balance = AccountBalanceQuery().setAccountId(accountId).execute(self.client)
                print("Hbar balance for {}: {}".format(accountId.toString(), balance.hbars.toString()))
                tokens = balance.tokens
                for tokenId in tokens.keySet().toArray():
                    print("Token {} = {}".format(tokenId.toString(), tokens[tokenId]))
            except Exception as e:
                print(e)
        elif args[0] == "create":
            initHbars = int(input("Set initial Hbars > "))
            prikey = PrivateKey.generate()
            print(Fore.YELLOW + "New Private Key: " + Fore.GREEN + prikey.toString())
            txn = (AccountCreateTransaction()
                   .setKey(prikey.getPublicKey())
                   .setInitialBalance(Hbar(initHbars))
                   .execute(self.client))
            receipt = txn.getReceipt(self.client)
            print(Fore.YELLOW + "New AccountId: " + Fore.GREEN + receipt.accountId.toString())
        elif args[0] == "delete":
            if len(args) != 2:
                print(Fore.RED + "need accountId")
            else:
                accountId = AccountId.fromString(args[1])
                prikey = PrivateKey.fromString(input("Enter this account's private key > "))
                txn = (AccountDeleteTransaction()
                       .setAccountId(accountId)
                       .setTransferAccountId(self.operator_id)
                       .setTransactionId(TransactionId.generate(accountId))
                       .freezeWith(self.client)
                       .sign(prikey)
                       .execute(self.client))
                txn.getReceipt(self.client)
                print(Fore.YELLOW + "account deleted!" + Fore.GREEN + txn.transactionId.toString())

        self.set_prompt()

    def do_send(self, arg):
        """send Hbars to another account:
send 0.0.12345 10
(send 10 hbars to account 0.0.12345)"""
        try:
            accountId = AccountId.fromString(input("Receipient account id: > "))
            hbars = input("amount of Hbars(minimum is 0.00000001): > ")
            amount = Hbar.fromTinybars(int(float(hbars) * 100_000_000))
            txn = (TransferTransaction()
                   .addHbarTransfer(self.operator_id, amount.negated())
                   .addHbarTransfer(accountId, amount)
                   .execute(self.client))
            print(Fore.YELLOW + "Hbar sent!" + Fore.GREEN + txn.transactionId.toString())
        except Exception as e:
            print(e)

        self.set_prompt()

            
if __name__ == "__main__":
    if len(sys.argv) > 1:
        dotenv = sys.argv[1]
    else:
        dotenv = ".env"
    load_dotenv(dotenv)
    HederaCli().cmdloop()
