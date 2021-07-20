#!/usr/bin/env python3

# https://community.bistudio.com/wiki/PBO_File_Format

import argparse
import os
import stat
import struct
import sys


class Pbo:
    def __init__(self):
        self.fileobj = None
        self.filename = None
        self.headers = []

        self.properties = []

    def unpack(self, pbo_file, dest):
        pass

    def pack(self, directory, pbo_file):
        pass

    def open(self, fname, write=False):
        self.fileobj = open(fname, 'wb' if write else 'rb')

    def close(self):
        self.fileobj.close()
        self.fileobj = None

class HeaderEntry:
    def __init__(self, filename, mimetype, original_size, offset, timestamp, data_size):
        self.filename = filename
        self.mimetype = mimetype
        self.original_size = original_size
        self.offset = offset
        self.timestamp = timestamp
        self.data_size = data_size

    @property
    def mimetype_string(self):
        mime = ''
        for i in range(24, -1, -8):
            mime += chr((self.mimetype >> i) & 255)
        return mime

    @property
    def packed_size(self):
        return self.data_size

    @property
    def unpacked_size(self):
        if self.original_size == 0:
            return self.data_size
        return self.original_size

    @property
    def compressed(self):
        # return self.mimetype_string == "Cprs"
        return self.packed_size != self.unpacked_size

    @staticmethod
    def from_stream(stream):
        filename = read_str(stream)
        contents = stream.read(20)
        if len(contents) != 20:
            raise ValueError()

        mimetype, original_size, offset, timestamp, data_size = struct.unpack('<LLLLL', contents)

        return HeaderEntry(
            filename,
            mimetype,
            original_size,
            offset,
            timestamp,
            data_size
        )

    def __bytes__(self):
        return self.filename.encode('ascii') + struct.pack('<BLLLLL',
            0,
            self.mimetype,
            self.original_size,
            self.offset,
            self.timestamp,
            self.data_size
        )

def read_str(stream):
    string = ''
    while True:
        char = stream.read(1)
        if len(char) == 0 or ord(char) == 0:
            break
        string += chr(char)
    return string

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

    if len(files) == 0 or len(files) > 2:
        parser.print_help()
        sys.exit(1)

    infname = files[0]
    outfname = files[1] if len(files) >= 2 else None

    infmode = os.stat(infname).st_mode
    if stat.S_ISREG(infmode):
        pbo = Pbo()
        pbo.unpack(infname, outfname)
    elif stat.S_ISDIR(infmode):
        pbo = Pbo()
        pbo.pack(infname, outfname)
    else:
        print('error: %s is not a regular file nor a directory' % infname, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])
