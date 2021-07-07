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
