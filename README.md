# hedera-cli-py
[Hedera](https://hedera.com/) CLI in Python


## Install

    pip install hedera-cli

## How to Use

Just run:

    hedera-cli

Since hedera-cli depends on [hedera-sdk-py](https://github.com/wensheng/hedera-sdk-py), which requires Java >= 11, please make sure your JAVA_HOME environment is set up correctly.

You can run `setup` inside hedera-cli and enter your account ID and private key.  You can also put them in an .env file to be read automatically at hedera-cli startup.  To use a different env file, just use the filename as the argument for hedera-cli.  For example:

    hedera-cli mainnet.env

A sample env file `sample.env` is provided.

## commands

Type ? or `help` for a list of commands.  Type `?command` for help on a specific command, for example `?topic`. 

### setup

Set up the client.

### account

    account create  (create an account, account id and privatekey will be printed)

    account info [accoun_id]  (get account info for current account if no accountId is provided,
                               or for a different account if accountId is provided)

    account balance [account_id]  (get account balance for current account if no accountId,
                                   or for a different account if accountId is provided)

    account delete account_id  (delete the account identified by accountId.
                                    you will be prompted for that account's private key)

### file

    file create [file_path]
    file info file_id
    file contents file_id
    file append file_id [file_path]
    file delete file_id

### send

    send  (no argument, you will prompted for recipient account and amount)

### topic

    topic create [memo]  (create a topic with an optional memo)
    topic info topic_id  (get info about a topic)
    topic send topic_id message [[message]]  (send message to topic_id)

### keygen

Create a key pair.

### network

Switch network

### exit

Exit the CLI
