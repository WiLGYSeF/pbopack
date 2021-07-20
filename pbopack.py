#!/usr/bin/env python3

# https://community.bistudio.com/wiki/PBO_File_Format

import argparse
import hashlib
import os
import stat
import struct
import sys


FILE_BUFFER_SZ = 1024 * 1024 # 1 MB


class Pbo:
    def __init__(self, **kwargs):
        self.pbo_prop_fname = kwargs.get('pbo_prop_fname', '.pboproperties')
        self.dryrun = kwargs.get('dryrun', False)
        self.verbose = kwargs.get('verbose', 0)

    def unpack(self, pbo_file, dest):
        with open(pbo_file, 'rb') as pbo_fileobj:
            headers, properties = Pbo.get_headers(pbo_fileobj)

            if not self.dryrun:
                os.makedirs(dest, exist_ok=True)
                if len(properties) != 0:
                    with open(os.path.join(dest, self.pbo_prop_fname), 'w') as file:
                        for prop in properties:
                            file.write('%s=%s\n' % (prop[0], prop[1]))

            for header in headers:
                filesize = header.packed_size

                if self.verbose >= 1:
                    print('  unpacking: %s (%.2f KB%s) ...' % (
                        header.filename,
                        round(filesize / 1024, 2),
                        ', compressed ' if header.is_compressed else ''
                    ))

                if self.dryrun:
                    continue

                path = os.path.join(dest, Pbo.pbo_path_to_os_path(header.filename))
                os.makedirs(os.path.dirname(path), exist_ok=True)

                with open(path, 'wb') as file:
                    data = pbo_fileobj.read(filesize)
                    if len(data) != filesize:
                        raise ValueError('expected data, but reached end of file')
                    file.write(data)

                os.utime(path, (header.timestamp, header.timestamp))

            # get pbo file size
            pbo_fileobj.seek(0, 2)
            pbo_size = pbo_fileobj.tell()
            pbo_fileobj.seek(0, 0)
            offset = 0

            sha1 = hashlib.sha1()

            while offset < pbo_size - 21:
                readsz = min(FILE_BUFFER_SZ, pbo_size - offset - 21)
                sha1.update(pbo_fileobj.read(readsz))
                offset += readsz

            zero = pbo_fileobj.read(1)
            if zero[0] != 0:
                raise ValueError('end of file checksum byte is not zero')

            checksum = pbo_fileobj.read(20)
            if checksum != sha1.digest():
                raise ValueError('checksums do not match')

    def pack(self, directory, pbo_file):
        pass

    @staticmethod
    def get_headers(stream):
        headers = []
        properties = []
        first_header = True

        while True:
            header = HeaderEntry.from_stream(stream)
            if header.mimetype == HEADER_MIMETYPE_VERS:
                if not first_header:
                    raise ValueError('header with mimetype VERS not the first header found')

                while True:
                    key = read_str(stream)
                    if len(key) == 0:
                        break

                    val = read_str(stream)
                    properties.append([key, val])
                first_header = False
                continue
            if header.mimetype == HEADER_MIMETYPE_CPRS:
                raise NotImplementedError('compressed PBO not supported')
            if header.mimetype == HEADER_MIMETYPE_ENCO:
                raise NotImplementedError('encoded PBO not supported')

            if len(header.filename) == 0:
                break
            headers.append(header)
            first_header = False

        return headers, properties

    @staticmethod
    def os_path_to_pbo_path(path):
        if os.sep == '\\':
            return path
        return '\\'.join(path.split(os.sep))

    @staticmethod
    def pbo_path_to_os_path(path):
        if os.sep == '\\':
            return path
        return os.path.join(*path.split('\\'))

HEADER_MIMETYPE_VERS = 0x56657273
HEADER_MIMETYPE_CPRS = 0x43707273
HEADER_MIMETYPE_ENCO = 0x456e6372
HEADER_MIMETYPE_DUMM = 0x00000000

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
    def is_compressed(self):
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
        string += chr(char[0])
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
