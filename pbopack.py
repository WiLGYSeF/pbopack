#!/usr/bin/env python3

# https://community.bistudio.com/wiki/PBO_File_Format

import argparse
import sys


def main(args):
    parser = argparse.ArgumentParser(
        description='Arma 3 PBO (un)packer',
        usage='%(prog)s [input] [output]',
        epilog="""
If input is a file, then the input file is unpacked to the output directory.
If input is a directory, then the directory is packed into the output file.
If input is a file and no output is given, verifies the checksum of the file.
"""
    )
    parser.add_argument('-v', '--verbose',
        action='store_true', default=False,
        help='verbose mode'
    )
    parser.add_argument('-i', '--ignore-errors',
        action='store_true', default=False,
        help='try to (un)pack PBO even if errors occur'
    )
    parser.add_argument('-p', '--pbo-properties',
        action='store', default='.pboproperties',
        help='specifies the file that contains the PBO properties (default .pboproperties)'
    )
    argspace, files = parser.parse_known_args(args)

if __name__ == '__main__':
    main(sys.argv[1:])
