import os
import sys
import cmd
import getpass

import colorama as cr
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


class HederaCli(cmd.Cmd):
    intro = """
# =============================================================================
#  __   __            __
# |  | |  |          |  |
# |  |_|  | ____  ___|  | ____ __ __ _____
# |   _   |/ __ \/  _`  |/ __ \  '__/  _  `|
# |  | |  |  ___/  (_|  |  ___/  | |  (_|  |
# \__| |__/\____|\___,__|\____|__|  \___,__|
#
# github.com/wensheng/hedera-cli-py
# =============================================================================
Type help or ? to list commands.\n"""

    def __init__(self, *args, **kwargs):
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
            self.prompt = cr.Fore.YELLOW + '{}@['.format(self.operator_id.toString()) + cr.Fore.GREEN + self.network + cr.Fore.YELLOW + '] > ' + cr.Style.RESET_ALL
        else:
            self.prompt = cr.Fore.YELLOW + 'null@[' + cr.Fore.GREEN + self.network + cr.Fore.YELLOW + '] > ' + cr.Style.RESET_ALL

    def do_exit(self, arg):
        'exit Hedera cli'
        exit()

    def do_setup(self, arg):
        'set operator id and key'
        acc_id = input(cr.Fore.YELLOW + "Operator Account ID (0.0.xxxx): " + cr.Style.RESET_ALL)
        acc_key = input(cr.Fore.YELLOW + "Private Key: " + cr.Style.RESET_ALL)
        try:
            self.operator_id = AccountId.fromString(acc_id)
            self.operator_key = PrivateKey.fromString(acc_key)
            self.client.setOperator(self.operator_id, self.operator_key)
            print(cr.Fore.GREEN + "operator is set up")
        except Exception:
            print(cr.Fore.RED + "Invalid operator id or key")
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
            print(cr.Fore.YELLOW + "no change")
            self.set_prompt()
            return

        if arg in ("mainnet", "testnet", "previewnet"):
            self.setup_network(arg)
            self.operator_id = None
            print(cr.Fore.GREEN + "you switched to {}, you must do `setup` again!".format(arg))
        else:
            print(cr.Fore.RED + "invalid network")
        self.set_prompt()

    def do_keygen(self, arg):
        'Generate a pair of private and public keys'
        prikey = PrivateKey.generate()
        print(cr.Fore.YELLOW + "Private Key: " + cr.Fore.GREEN + prikey.toString())
        print(cr.Fore.YELLOW + "Public Key: " + cr.Fore.GREEN + prikey.getPublicKey().toString())
        self.set_prompt()

    def do_topic(self, arg):
        """HCS Topic: create send
Create Topic:
    topic create [memo]
Send message:
    topic send topic_id message [[messages]]"""
        args = arg.split()
        if args[0] not in ('create', 'send'):
            print(cr.Fore.RED + "invalid topic command")
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
                print(cr.Fore.RED + "need topicId and message")
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
        if args[0] not in ('create', 'balance', 'delete', 'info'):
            print(cr.Fore.RED + "invalid topic command")
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
            print(cr.Fore.YELLOW + "New Private Key: " + cr.Fore.GREEN + prikey.toString())
            txn = (AccountCreateTransaction()
                   .setKey(prikey.getPublicKey())
                   .setInitialBalance(Hbar(initHbars))
                   .execute(self.client))
            receipt = txn.getReceipt(self.client)
            print(cr.Fore.YELLOW + "New AccountId: " + cr.Fore.GREEN + receipt.accountId.toString())
        elif args[0] == "delete":
            if len(args) != 2:
                print(cr.Fore.RED + "need accountId")
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
                print(cr.Fore.YELLOW + "account deleted!" + cr.Fore.GREEN + txn.transactionId.toString())

        self.set_prompt()

    def do_send(self, arg):
        try:
            accountId = AccountId.fromString(input("Receipient account id: > "))
            hbars = input("amount of Hbars(minimum is 0.00000001): > ")
            amount = Hbar.fromTinybars(int(float(hbars) * 100_000_000))
            txn = (TransferTransaction()
                   .addHbarTransfer(self.operator_id, amount.negated())
                   .addHbarTransfer(accountId, amount)
                   .execute(self.client))
            print(cr.Fore.YELLOW + "Hbar sent!" + cr.Fore.GREEN + txn.transactionId.toString())
        except Exception as e:
            print(e)

        self.set_prompt()

            
if __name__ == "__main__":
    if len(sys.argv) > 1:
        dotenv = sys.argv[1]
    else:
        dotenv = ".env"
    load_dotenv(dotenv)
    cr.init()
    HederaCli().cmdloop()
