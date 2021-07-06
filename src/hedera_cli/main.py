import hedera_cli.check_java
import sys
from typing import List, Optional
import colorama
from dotenv import load_dotenv
from hedera_cli.hedera_cli import HederaCli


def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]
    if len(args) > 0:
        dotenv = args[0]
    else:
        dotenv = ".env"
    load_dotenv(dotenv)
    colorama.init()
    HederaCli().cmdloop()
