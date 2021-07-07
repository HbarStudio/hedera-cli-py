import os
import sys
import subprocess

if "JAVA_HOME" not in os.environ:
    exit("JAVA_HOME environment variable must be set before running `hedera-cli`")

cwd = os.getcwd()

bindir = os.path.join(os.environ["JAVA_HOME"], "bin")
if sys.platform == "win32":
    bindir = bindir.replace('"', '')
    os.chdir(bindir)
    proc = subprocess.Popen("java -version", stderr=subprocess.PIPE, shell=True)
else:
    proc = subprocess.Popen("{}/java -version".format(bindir), stderr=subprocess.PIPE, shell=True)

version = proc.stderr.read().split(b'"')[1]
major = int(version.split(b'.')[0])
if major < 11:
    exit("""
your java version {} from your JAVA_HOME is too low.
The minimal required version is 11.
Make sure to point your JAVA_HOME to java >= 11.
         """.format(version.decode()))

if sys.platform == "win32":
    # probably not neccessary
    os.chdir(cwd)
