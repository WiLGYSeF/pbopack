#!/usr/bin/env python3

# https://community.bistudio.com/wiki/PBO_File_Format

import argparse
import os
import stat
import sys

from pbo import Pbo


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
    parser.add_argument('-n', '--dryrun',
        action='store_true', default=False,
        help='dryrun (un)packing PBO'
    )
    argspace, files = parser.parse_known_args(args)

    if len(files) == 0 or len(files) > 2:
        parser.print_help()
        sys.exit(1)

    infname = files[0]
    outfname = files[1] if len(files) >= 2 else None

    pbo = Pbo(
        pbo_prop_fname=argspace.pbo_properties,
        ignore_errors=argspace.ignore_errors,
        dryrun=argspace.dryrun,
        verbose=argspace.verbose,
    )

    infmode = os.stat(infname).st_mode
    if stat.S_ISREG(infmode):
        pbo.unpack(infname, outfname)
    elif stat.S_ISDIR(infmode):
        pbo.pack(infname, outfname)
    else:
        print('error: %s is not a regular file nor a directory' % infname, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])
