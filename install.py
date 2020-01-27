import sys
import os
import shutil

DEST_PATH = "\"/Users/bbr/Library/Application Support/Sublime Text 3/Packages/PerlIde/\""


def main():
    os.system("rm -rf {}".format(DEST_PATH))
    os.system("mkdir {}".format(DEST_PATH))
    os.system("cp -r lib {}".format(DEST_PATH))
    os.system("cp -r lib {}".format(DEST_PATH))
    os.system("cp *.py {}".format(DEST_PATH))
    os.system("rm {}install.py".format(DEST_PATH))



if __name__ == '__main__':
    main()