import os
import sys
import json
import cmd
import math
import base64
from pprint import pprint

import requests
from colorama import init, Fore, Back, Style
from dotenv import load_dotenv
from hedera import (
    Hbar,
    Client,
    PrivateKey,
    AccountId,
    AccountInfoQuery,
    AccountCreateTransaction,
    AccountDeleteTransaction,
    AccountBalanceQuery,
    TransferTransaction,
    TransactionId,
    TopicCreateTransaction,
    TopicId,
    TopicMessageSubmitTransaction,
    TopicInfoQuery,
    TokenId,
    FileId,
    FileInfoQuery,
    FileCreateTransaction,
    FileAppendTransaction,
    FileContentsQuery,
    FileDeleteTransaction,
    TokenCreateTransaction,
    TokenAssociateTransaction,
    TokenInfoQuery,
    TokenGrantKycTransaction,
    ContractId,
    ContractCreateTransaction,
    ContractFunctionParameters,
    ContractInfoQuery,
    ContractCallQuery,
    )
from jnius import autoclass, cast
from hedera_cli._version import version
from hedera_cli.price import get_Hbar_price
if sys.platform == "win32":
    from msvcrt import getch
else:
    from getch import getch


ArrayList = autoclass('java.util.ArrayList')

FILE_CREATE_SIZE = 5000  # don't know exactly the size, 5000 works, 6000 doesn't
CHUNK_SIZE = 1024

mirror_address = {
    "testnet": "https://testnet.mirrornode.hedera.com",
    "mainnet": "https://mainnet-public.mirrornode.hedera.com",
    "previewnet": "https://previewnet.mirrornode.hedera.com",
    }


def getc():
    c = getch()
    if hasattr(c, 'decode'):
        return c.decode()
    return c


def getPrivateKey():
    passwd = ''
    while True:
        c = getc()
        if c == '\r' or c == '\n':
            break
        print('*', end='', flush=True)
        passwd += c
    print()

    return passwd

current_price = get_Hbar_price()


class HederaCli(cmd.Cmd):
    #use_rawinput = False  # if True, colorama prompt will not work on Windows
    intro = """
# =============================================================================
# """ + Fore.WHITE + Back.BLUE + "  __   __            __                     " + Style.RESET_ALL + """
# """ + Fore.WHITE + Back.BLUE + " |  | |  |          |  |                    " + Style.RESET_ALL + """
# """ + Fore.WHITE + Back.BLUE + " |  |_|  | ____  ___|  | ____ __ __ _____   " + Style.RESET_ALL + """
# """ + Fore.WHITE + Back.BLUE + " |   _   |/ __ \/  _`  |/ __ \  '__/  _  `| " + Style.RESET_ALL + """
# """ + Fore.WHITE + Back.BLUE + " |  | |  |  ___/  (_|  |  ___/  | |  (_|  | " + Style.RESET_ALL + """
# """ + Fore.WHITE + Back.BLUE + " \__| |__/\____|\___,__|\____|__|  \___,__| " + Style.RESET_ALL + """
# """ + Fore.WHITE + Back.BLUE + "                                            " + Style.RESET_ALL + """
# :: hedera-cli :: v{}
# current Hbar price: {}
#
# github.com/wensheng/hedera-cli-py
# =============================================================================
Type help or ? to list commands.\n""".format(version, current_price)

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
        self.hbar_price = current_price
        self.set_prompt()

    def emptyline(self):
        "If this is not here, last command will be repeated"
        pass

    def set_prompt(self):
        if self.operator_id:
            self.prompt = Fore.YELLOW + '{}@['.format(self.operator_id.toString()) + Fore.GREEN + self.network + Fore.YELLOW + '] > ' + Style.RESET_ALL
        else:
            self.prompt = Fore.YELLOW + 'null@[' + Fore.GREEN + self.network + Fore.YELLOW + '] > ' + Style.RESET_ALL

    def err_return(self, msg):
        print(Fore.RED + msg)
        self.set_prompt()
        return

    def do_exit(self, arg):
        'exit hedera-cli'
        exit()

    def do_setup(self, arg):
        """Set up hedera client by setting operator id and key.
        setup  (no argument)
        """
        # these doesn't work on Windows
        # acc_id = input(Fore.YELLOW + "Operator Account ID (0.0.xxxx): " + Style.RESET_ALL)
        # acc_key = input(Fore.YELLOW + "Private Key: " + Style.RESET_ALL)
        print(Fore.YELLOW + "Operator Account ID (0.0.xxxx): " + Style.RESET_ALL, end='')
        acc_id = input()
        print(Fore.YELLOW + "Private Key: " + Style.RESET_ALL, end='', flush=True)
        acc_key = getPrivateKey()
        try:
            self.operator_id = AccountId.fromString(acc_id)
            self.operator_key = PrivateKey.fromString(acc_key)
            self.client.setOperator(self.operator_id, self.operator_key)
            print(Fore.GREEN + "operator is set up")
        except Exception:
            print(Fore.RED + "Invalid operator id or key")
        self.set_prompt()

    def one_node(self):   
        node_list = ArrayList()
        # just pick the first node, for java sdk client, there're 5
        node_list.add(self.client.network.nodes.toArray()[0].accountId)
        return node_list

    def setup_network(self, name):
        self.network = name
        if name == "mainnet":
            self.client = Client.forMainnet()
        elif name == "previewnet":
            self.client = Client.forPreviewnet()
        else:
            self.client = Client.forTestnet()

    def do_network(self, arg):
        """Switch network:
        network mainnet
        network testnet
        network previewnet
        """
        if arg == self.network:
            return self.err_return("no change")

        if arg in ("mainnet", "testnet", "previewnet"):
            self.setup_network(arg)
            self.operator_id = None
            print(Fore.GREEN + "you switched to {}, you must do `setup` again!".format(arg))
        else:
            print(Fore.RED + "invalid network")
        self.set_prompt()

    def do_keygen(self, arg):
        """Generate a pair of private and public keys
        keygen  (no argument)
        """
        prikey = PrivateKey.generate()
        print(Fore.YELLOW + "Private Key: " + Fore.GREEN + prikey.toString())
        print(Fore.YELLOW + "Public Key: " + Fore.GREEN + prikey.getPublicKey().toString())
        self.set_prompt()

    def do_topic(self, arg):
        """HCS Topic:
        topic create [memo]              (create a topic with an optional memo) 
        topic info topic_id              (get info about a topic)
        topic send topic_id              (send message to topic_id, you will be prompted for message)
        topic get topic_id [sequence #]  (get topic message(s).  If you specify a sequence_number,
                                          you get one message, otherwise, you get all the messages on the topic)
        """
        args = arg.split()
        if not args or args[0] not in ('create', 'send', 'info', "get"):
            return self.err_return("invalid topic command")

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
        elif args[0] == "info":
            if len(args) < 2:
                return self.err_return("need topicId")

            try:
                topicId = TopicId.fromString(args[1])
                info = TopicInfoQuery().setTopicId(topicId).execute(self.client)
                print("\n{:} info:".format(topicId.toString()))
                print("=========================")
                print("memo :", info.topicMemo)
                print("adminKey :", end="")
                if info.adminKey:
                    print(info.adminKey.toString())
                else:
                    print()
                print("submitKey :", end="")
                if info.submitKey:
                    print(info.submitKey.toString())
                else:
                    print()
                print("sequence# :", info.sequenceNumber)
                print("expires :", info.expirationTime.toString())
                print("autoRenewAccountId :", end="")
                if info.autoRenewAccountId:
                    print(info.autoRenewAccountId.toString())
                else:
                    print()
                print("autoRenewPeriod :", info.autoRenewPeriod.toDays(), "days")
                print("running hash :", end="")
                if info.runningHash:
                    print(info.runningHash.toByteArray().tostring().hex())
                else:
                    print()
                print()

            except Exception as e:
                print(e)

        elif args[0] == "get":
            # this does not use SDK, it use mirror node REST API
            if len(args) < 2:
                return self.err_return("need topicId")

            try:
                TopicId.fromString(args[1])
            except Exception:
                return self.err_return("topicId not valid")


            url = "{}/api/v1/topics/{}/messages".format(mirror_address[self.network], args[1])
            if len(args) > 2:
                if args[2].isnumeric():
                    seq_num = int(args[2])
                    req = requests.get(url, params={"sequenceNumber": seq_num})
                else:
                    return self.err_return("invalid sequence number")
            else:
                req = requests.get(url)
            data = req.json()
            msgs = data['messages']
            msgs.sort(key=lambda x: x['sequence_number'])
            for msg in msgs:
                print("sequence_number:", msg['sequence_number'])
                print("consensus_timestamp:", msg['consensus_timestamp'])
                print("running hash:", base64.b64decode(msg['running_hash']).hex())
                print("message:")
                print(base64.b64decode(msg['message']).decode())
                print()

        elif args[0] == "send":
            if len(args) < 2:
                return self.err_return("need topicId")
            try:
                topicId = TopicId.fromString(args[1])
                msg = input("Type your Message (Entering without message cancels the submission):\n\t> ")
                if msg.strip() == "":
                    return self.err_return("Cancelled sending message")

                txn = (TopicMessageSubmitTransaction()
                       .setTopicId(topicId)
                       .setMessage(msg))
                receipt = txn.execute(self.client).getReceipt(self.client)
                print("message sent, sequence #: ", receipt.topicSequenceNumber)
            except Exception as e:
                print(e)
        self.set_prompt()

    def do_account(self, arg):
        """account:
        account create               (create an account, account id and privatekey will be printed)
        account info [accoun_id]     (get account info for current account if no accountId is provided,
                                      or for a different account if accountId is provided)
        account balance [account_id] (get account balance for current account if no accountId,
                                      or for a different account if accountId is provided)
        account delete account_id    (delete the account identified by accountId.
                                      you will be prompted for that account's private key)
        """
        args = arg.split()
        if not args or args[0] not in ('create', 'balance', 'delete', 'info'):
            return self.err_return("invalid account command")

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
        elif args[0] == "info":
            try:
                if len(args) > 1:
                    accountId = AccountId.fromString(args[1])
                else:
                    accountId = self.operator_id
                info = AccountInfoQuery().setAccountId(accountId).execute(self.client)
                print("\n{:} info:".format(accountId.toString()))
                print("=========================")
                print("hbar balance :", info.balance.toString())
                # info.key is either PublicKey or KeyList
                if info.key.getClass().getName().endswith("KeyList"):
                    print("public key list:")
                    kl = cast("com.hedera.hashgraph.sdk.KeyList", info.key)
                    print("\tthreshold: ", kl.threshold)
                    for k in kl.toArray():
                        print("\t", k.toString())
                else:
                    print("public key :", info.key.toString())
                print("isReceiverSignatureRequired? :", info.isReceiverSignatureRequired)
                print("tokenRelationships :")
                for tokenId in info.tokenRelationships.keySet().toArray():
                    rel = info.tokenRelationships[tokenId]
                    # print("{}.{}.{}".format(tokenId.shard, tokenId.realm, tokenId.num))
                    print("{:20} symbol: {:6}  kycStatus: {}   freezeStatus: {}   balance: {} ".format(
                          tokenId.toString(), rel.symbol, rel.kycStatus, rel.freezeStatus, rel.balance))
                print()
            except Exception as e:
                print(e)

        elif args[0] == "delete":
            if len(args) != 2:
                print(Fore.RED + "need accountId")
            else:
                try:
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
                except Exception as e:
                    print(e)

        self.set_prompt()

    def do_send(self, arg):
        """send Hbars to another account:
        send  (no argument, you will prompted for recipient account and amount)
        """
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

    def get_local_file_content(self, filepath, cur_size=0):
        if not os.path.isfile(filepath):
            self.err_return("file {} does not exist".format(filepath))
            return None, 0
        filesize = os.path.getsize(filepath)
        if (filesize + cur_size) > 1024 * 1000:
            self.err_return("file is too large, the maximum file size is 1024 kB")
            return None, 0

        with open(filepath) as fh:
            return fh.read(), filesize

    def get_content_from_input(self):
        print("Enter your file content line by line, enter EOF to finish:\n") 
        lines = []
        while True:
            line = input()
            if line.strip() == "EOF":
                break
            lines.append(line)
        contents = '\n'.join(lines)
        filesize = len(contents)
        return contents, filesize

    def do_file(self, arg):
        """Hedera File Service:
        file create [file_path]          (create a file, if file_path is provided, file content will be uploaded,
                                          otherwise, you will be prompted to enter the content)
        file info file_id                (get info about a file)
        file contents file_id            (get content of a file)
        file append file_id [file_path]  (append the file with more contents)
        file delete file_id              (delete a file)
        """
        args = arg.split()
        if not args or args[0] not in ('create', 'contents', 'info', 'append', 'delete'):
            return self.err_return("invalid file command")

        if args[0] == "create":
            memo = input("file memo [optional]:")
            if len(args) > 1:
                contents, filesize = self.get_local_file_content(args[1])
                if not contents:
                    return
            else:
                contents, filesize = self.get_content_from_input()
                if filesize == 0:
                    return self.err_return("no content")

            # calculate price
            # single sig only
            # use 0.039 + $0.011 per 1kB
            cost = 0.039 + 0.011 * math.ceil(filesize / 1000.0)
            self.hbar_price = get_Hbar_price()
            cost_in_hbar = cost / self.hbar_price 
            answer = input("It will cost about {:.5f} hbars to create this file, is this OK? type yes or no: ".format(cost_in_hbar))
            if answer.lower() == "yes":
                first_chunk = contents if filesize <= FILE_CREATE_SIZE else contents[:FILE_CREATE_SIZE]
                try:
                    txn = (FileCreateTransaction()
                           .setFileMemo(memo)
                           .setKeys(self.operator_key.getPublicKey())
                           .setContents(first_chunk)
                           .setMaxTransactionFee(Hbar(1))
                           .execute(self.client))
                    receipt = txn.getReceipt(self.client)
                    fileId = receipt.fileId

                    if filesize > FILE_CREATE_SIZE:
                        num_chunks = math.ceil((filesize - FILE_CREATE_SIZE) / CHUNK_SIZE)
                        max_cost = math.ceil(cost_in_hbar)
                        txn = (FileAppendTransaction()
                               .setNodeAccountIds(self.one_node())
                               .setFileId(fileId)
                               .setContents(contents[FILE_CREATE_SIZE:])
                               .setMaxChunks(num_chunks)
                               .setMaxTransactionFee(Hbar(max_cost))
                               .freezeWith(self.client)
                               .execute(self.client))
                        receipt = txn.getReceipt(self.client)

                    print("File created.  FileId =", fileId.toString())

                except Exception as e:
                    print(e)

            else:
                print("canceled")

        elif args[0] == "append":
            if len(args) < 2:
                return self.err_return("fileId is needed")
            
            try:
                fileId = FileId.fromString(args[1])
                info = FileInfoQuery().setFileId(fileId).execute(self.client)
                print("filesize before appending is ", info.size)

                if len(args) > 2:
                    contents, filesize = self.get_local_file_content(args[2], info.size)
                    if not contents:
                        return
                else:
                    contents, filesize = self.get_content_from_input()
                    if filesize == 0:
                        return self.err_return("no content")

                cost = 0.039 + 0.011 * math.ceil(filesize / 1000.0)
                self.hbar_price = get_Hbar_price()
                cost_in_hbar = cost / self.hbar_price
                max_cost = math.ceil(cost_in_hbar + 0.5)  # 0.5 is margin 
                answer = input("It will cost about {:.5f} hbars to append to this file, is this OK? type yes or no: ".format(cost_in_hbar))
                if answer.lower() == "yes":
                    num_chunks = math.ceil(filesize / CHUNK_SIZE)
                    txn = (FileAppendTransaction()
                           .setNodeAccountIds(self.one_node())
                           .setFileId(fileId)
                           .setContents(contents)
                           .setMaxChunks(num_chunks)
                           .setMaxTransactionFee(Hbar(max_cost))
                           .freezeWith(self.client)
                           .execute(self.client))
                    receipt = txn.getReceipt(self.client)
                    print("File appended")
                else:
                    print("canceled")

            except Exception as e:
                print(e.innermessage)

        elif args[0] == "info":
            if len(args) < 2:
                return self.err_return("fileId is needed")
            
            try:
                fileId = FileId.fromString(args[1])
                info = FileInfoQuery().setFileId(fileId).execute(self.client)
                print("file memo:", info.fileMemo)
                print("file size:", info.size)
                print("expires:", info.expirationTime.toString())
            except Exception as e:
                print(e)

        elif args[0] == "contents":
            if len(args) < 2:
                return self.err_return("fileId is needed")
            
            try:
                fileId = FileId.fromString(args[1])
                resp = FileContentsQuery().setFileId(fileId).execute(self.client)
                contents = resp.toStringUtf8()
                with open(args[1], 'w') as fh:
                    fh.write(contents)
                print()
                print(Fore.GREEN + "file is saved as {}.  Here is a preview:".format(args[1]))
                print(Style.RESET_ALL)
                print(contents[:1024])
                print()
            except Exception as e:
                print(e)

        elif args[0] == "delete":
            if len(args) < 2:
                return self.err_return("fileId is needed")
            
            try:
                fileId = FileId.fromString(args[1])
                txn = FileDeleteTransaction().setFileId(fileId).execute(self.client)
                receipt = txn.getReceipt(self.client)
            except Exception as e:
                print(e.innermessage)

    def do_token(self, arg):
        """Hedera Token Service:
        token create                           (create a token, you will be prompted for details)
        token info token_id                    (get info about a token)
        token associate token_id account_id    (associate token with another account)
        token kyc token_id account_id          (grant token kyc to another account)
        token transfer                         (transfer a token, you will be prompted for details)
        """
        args = arg.split()
        if not args or args[0] not in ('create', 'info', 'associate', 'kyc', 'transfer'):
            return self.err_return("invalid file command")

        if args[0] == "create":
            try:
                ttype = int(input("Token type (fungible - 0 or non-fungible - 1, default is 0): "))
            except ValueError:
                ttype = 0
            if ttype > 1:
                ttype = 0
            name = input("Token name: ")
            symbol = input("Token symbol: ")

            if ttype == 0:
                try:
                    # TODO: max decimal?
                    decimals = int(input("Token decimals (0-6 default 0): "))
                except ValueError:
                    decimals = 0
                if decimals > 6:
                    decimals = 0

                try:
                    initialSupply = int(input("initial token supply? (default 0): "))
                except ValueError:
                    initialSupply = 0
            else:
                decimals = 0
                initialSupply = 0
            print("Summary:")
            print("\tToken Type (0:fungible, 1:non-fungible):", ttype)
            print("\tName:", name)
            print("\tSymbol:", symbol)
            print("\tDecimals:", decimals)
            print("\tInitial supply:", initialSupply)
            print("It takes ", 1.0/self.hbar_price, "hbars to create a token.")

            initialSupply *= 10 ** decimals
            
            isitok = input("\ncontinue? (y-yes or n-no): ").lower()
            if isitok == "y" or isitok == "yes":
                pubkey = self.operator_key.getPublicKey()
                try:
                    # TODO: bug? if setTokenType and setDecimals/InitialSupply, core dumps
                    if ttype == 0:
                        txn = (TokenCreateTransaction()
                               .setNodeAccountIds(self.one_node())
                               .setTokenName(name)
                               .setTokenSymbol(symbol)
                               .setDecimals(decimals)
                               .setInitialSupply(initialSupply)
                               .setTreasuryAccountId(self.operator_id)
                               .setAdminKey(pubkey)
                               .setFreezeKey(pubkey)
                               .setWipeKey(pubkey)
                               .setKycKey(pubkey)
                               .setSupplyKey(pubkey)
                               .setFreezeDefault(False)
                               .execute(self.client))
                    else:
                        txn = (TokenCreateTransaction()
                               .setNodeAccountIds(self.one_node())
                               .setTokenName(name)
                               .setTokenSymbol(symbol)
                               .setTreasuryAccountId(self.operator_id)
                               .setTokenType(ttype)
                               .setAdminKey(pubkey)
                               .setFreezeKey(pubkey)
                               .setWipeKey(pubkey)
                               .setKycKey(pubkey)
                               .setSupplyKey(pubkey)
                               .setFreezeDefault(False)
                               .execute(self.client))
                    tokenId = txn.getReceipt(self.client).tokenId
                    print("Token created.  Token_id =", tokenId.toString())
                except Exception as e:
                    print(e)
            else:
                print("cancelled")

        elif args[0] == "info":
            if len(args) < 2:
                return self.err_return("tokenId is needed")
            
            try:
                tokenId = TokenId.fromString(args[1])
                info = TokenInfoQuery().setTokenId(tokenId).execute(self.client)
                print("tokenType:", info.tokenType.toString())
                print("name:", info.name)
                print("symbol:", info.symbol)
                print("decimals:", info.decimals)
                print("totalSupply", info.totalSupply)
                print("maxSupply", info.maxSupply)
                print("defaultKycStatus:", info.defaultKycStatus)
                print("defaultFreezeStatus:", info.defaultFreezeStatus)
                print("expirationTime:", info.expirationTime.toString())
                print("autoRenewAccount:", info.autoRenewAccount.toString())
                print("autoRenewPeriod (days):", info.autoRenewPeriod.toDays())
                print("customFees:", info.customFees.toArray())
                print("feeScheduleKey:", info.feeScheduleKey and info.feeScheduleKey.toString())
                print("kycKey:", info.kycKey and info.kycKey.toString())
                print("supplyKey:", info.supplyKey and info.supplyKey.toString())
                print("wipeKey:", info.wipeKey and info.wipeKey.toString())
            except Exception as e:
                print(e)

        if args[0] == "associate":
            if len(args) < 2:
                return self.err_return("need tokenId")

            try:
                tokenId = TokenId.fromString(args[1])
                listOne = ArrayList()
                listOne.add(tokenId)
                txn = (TokenAssociateTransaction()
                       .setAccountId(self.operator_id)
                       .setTokenIds(listOne)
                       .freezeWith(self.client)
                       .sign(self.operator_key)
                       .execute(self.client))
                receipt = txn.getReceipt(self.client)
                print(receipt.status)
            except Exception as e:
                print(e)

        if args[0] == "kyc":
            if len(args) < 3:
                return self.err_return("need tokenId and accountId")
            try:
                tokenId = TokenId.fromString(args[1])
                accountId = AccountId.fromString(args[2])
                txn = (TokenGrantKycTransaction()
                       .setAccountId(accountId)
                       .setTokenId(tokenId)
                       .execute(self.client))
                receipt = txn.getReceipt(self.client)
                print(receipt.status.toString())
            except Exception as e:
                print(e)

        if args[0] == "transfer":
            try:
                tokenId = TokenId.fromString(input("token id: "))
                accountId = AccountId.fromString(input("account id: "))
                amount = int(input("Enter the amount (number of tokens multiply by 1[0...], number of 0's is the token decimals),\n"
                                   "For example, if you want to transfer 100.55 and token decimals is 2, you enter 10055.\n"
                                   "\tamount: "))
                txn = (TransferTransaction()
                       .addTokenTransfer(tokenId, self.operator_id, -amount)
                       .addTokenTransfer(tokenId, accountId, amount)
                       .execute(self.client))
                receipt = txn.getReceipt(self.client)
                print(receipt.status.toString())
            except Exception as e:
                print(e)

    def do_contract(self, arg):
        """Hedera Smart Contract (HTC & HCS recommended for most use cases):
        contract create            (create a contract, you will be prompted for details)
        contract call contract_id  (call a contract,
                                    you will be prompted for function name and parameter)
        contract info contract_id  (get info about a contract)
        """
        args = arg.split()
        if not args or args[0] not in ('create', 'call', 'info'):
            return self.err_return("invalid contract command")

        if args[0] == "create":
            # try:
            #     initBalance = int(input("initial Hbar balance for this contract?: "))
            # except ValueError:
            #     return self.err_return("number must be integer")
            # if initBalance < 1:
            #    initBalance = 0

            # TODO: will ask to enter gas if it consume large gas
            # gas = input("How much gas")
            # for now just set 1_000_000 gas, around $0.05
            # contract create is $1, file create is 0.05
            # cost = int(1.10/self.hbar_price) + initBalance
            cost = int(1.10/self.hbar_price)
            confirm = input("It cost %d hbars to create a contract, continue? y/n: " % cost)
            if confirm.lower() != "y":
                return self.err_return("cancelled")

            where = input("Enter the contract JSON file path: ")
            if not os.path.isfile(where):
                return self.err_return("no such file")

            contract_file = open(where)
            try:
                contract_json = json.load(contract_file)
                contract_file.close()
            except ValueError:
                return self.err_return("invalid contract JSON file")

            if "abi" not in contract_json or "bytecode" not in contract_json:
                return self.err_return("contract JSON file must have abi and bytecode")

            if "contractName" in contract_json:
                name = contract_json['contractName']
                print("contract name:", name)
            else:
                name = "contract"

            try:
                txn = (FileCreateTransaction()
                       .setKeys(self.operator_key.getPublicKey())
                       .setFileMemo(name)
                       .setContents(contract_json['bytecode'].encode())
                       .execute(self.client))
                receipt = txn.getReceipt(self.client)
                file_id = receipt.fileId
                print("contract file created: ", file_id.toString())
            except Exception as e:
                return self.err_return(e)

            inputs = contract_json["abi"][0]["inputs"]
            params = ContractFunctionParameters() 
            for i in inputs:
                params.add(input("input - name:" + i['name'] + " type:" + i['type'] + " = "))

            try:
                # will CONTRACT_REVERT_EXECUTED if setInitialBalance
                #       .setInitialBalance(Hbar(initBalance))
                txn = (ContractCreateTransaction()
                       .setGas(1000000)
                       .setBytecodeFileId(file_id)
                       .setAdminKey(self.operator_key)
                       .setMaxTransactionFee(Hbar(cost))
                       .execute(self.client))
                receipt = txn.getReceipt(self.client)
                print("contract created : ", receipt.contractId.toString())
            except Exception as e:
                print(e)
 
        elif args[0] == "call":
            if len(args) < 2:
                return self.err_return("need contract_id")
            try:
                contractId = ContractId.fromString(args[1])
            except Exception as e:
                return self.err_return(e)

            # params = ContractFunctionParameters() 
            func_name = input("Enter the function name: ")
            input_params = input("Enter the parameters: ")
            try:
                resp = (ContractCallQuery()
                        .setGas(1000000)
                        .setContractId(contractId)
                        .setFunction(func_name)
                        .execute(self.client))
            except Exception as e:
                return self.err_return(e)

            if resp.errorMessage:
                print(resp.errorMessage)
            else:
                print("result:\n", resp.getString(0))
                print()

        elif args[0] == "info":
            if len(args) < 2:
                return self.err_return("need contract_id")
            try:
                contractId = ContractId.fromString(args[1])
            except Exception as e:
                return self.err_return(e)

            try:
                info = ContractInfoQuery().setContractId(contractId).execute(self.client)
                print("accountId:", info.accountId.toString())
                print("adminKey:", info.adminKey.toString())
                print("expires:", info.expirationTime.toString())
                print("autoRenewPeriod (days):", info.autoRenewPeriod.toDays())
                print("storage:", info.storage)
                print("memo:", info.contractMemo)
                print("balance:", info.balance.toString())
                print("isDeleted:", info.isDeleted)
            except Exception as e:
                print(e)

    def do_txn(self, arg):
        """Transaction info:
        txn info transaction_id    (get info of a transaction,
                                    transaction_id is of format: 0.0.accountId-seconds-nanos)
        """
        args = arg.split()
        if not args or args[0] not in ('info'):
            return self.err_return("invalid txn command")

        if args[0] == "info":
            if len(args) < 2:
                return self.err_return("need transaction_id")

            url = "{}/api/v1/transactions/{}".format(mirror_address[self.network], args[1])
            req = requests.get(url)
            data = req.json()
            if '_status' in data:
                print(data['_status'])
            elif 'transactions' in data:
                d = data['transactions'][0]
                pprint(d)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        dotenv = sys.argv[1]
    else:
        dotenv = ".env"
    load_dotenv(dotenv)
    HederaCli().cmdloop()
