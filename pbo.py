import hashlib
import os
import sys

from headerentry import (
    HeaderEntry,
    read_str,
    MIMETYPE_VERS,
    MIMETYPE_CPRS,
    MIMETYPE_ENCO
)


FILE_BUFFER_SZ = 1024 * 1024 # 1 MB


class Pbo:
    def __init__(self, **kwargs):
        self.pbo_prop_fname = kwargs.get('pbo_prop_fname', '.pboproperties')
        self.ignore_errors = kwargs.get('ignore_errors', False)
        self.dryrun = kwargs.get('dryrun', False)
        self.verbose = kwargs.get('verbose', 0)

    def unpack(self, pbo_file, dest):
        with open(pbo_file, 'rb') as pbo_fileobj:
            headers, properties = self._get_headers(pbo_fileobj)

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

                total = 0
                with open(path, 'wb') as file:
                    while True:
                        data = pbo_fileobj.read(min(FILE_BUFFER_SZ, filesize - total))
                        if len(data) == 0:
                            break
                        total += len(data)
                        file.write(data)

                if total != filesize:
                    self._error(ValueError, 'expected data, but reached end of file')

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
                self._error(ValueError, 'end of file checksum byte is not zero')

            checksum = pbo_fileobj.read(20)
            if checksum != sha1.digest():
                self._error(ValueError, 'checksums do not match')

    def pack(self, directory, pbo_file):
        headers = []
        header_paths = {}
        prefixlen = len(os.path.abspath(directory)) + 1

        for root, _, files in os.walk(directory):
            for fname in files:
                path = os.path.abspath(os.path.join(root, fname))
                header_fname = Pbo.os_path_to_pbo_path(path[prefixlen:])
                if header_fname == self.pbo_prop_fname:
                    continue

                if self.verbose >= 1:
                    print('  packing: %s ...' % header_fname)

                stat = os.stat(path)
                header = HeaderEntry(
                    header_fname,
                    0,
                    0,
                    0,
                    int(stat.st_mtime),
                    stat.st_size
                )
                header_paths[header] = path
                headers.append(header)

        headers.sort(key=lambda x: x.filename.lower())

        sha1 = hashlib.sha1()

        with open(pbo_file, 'wb') as pbo_fileobj:
            try:
                properties = []
                with open(os.path.join(directory, self.pbo_prop_fname), 'r') as propfile:
                    for line in propfile:
                        line = line.rstrip("\n")
                        if len(line) == 0:
                            continue

                        spl = line.split("=")
                        properties.append([spl[0], "=".join(spl[1:])])

                header = HeaderEntry('', MIMETYPE_VERS, 0, 0, 0, 0)
                buf = bytes(header)

                pbo_fileobj.write(buf)
                sha1.update(buf)

                for prop in properties:
                    buf = Pbo.asciiz(prop[0])
                    pbo_fileobj.write(buf)
                    sha1.update(buf)

                    buf = Pbo.asciiz(prop[1])
                    pbo_fileobj.write(buf)
                    sha1.update(buf)

                pbo_fileobj.write(b'\x00')
                sha1.update(b'\x00')
            except FileNotFoundError:
                pass
            except Exception as exc:
                self._error(Exception, str(exc))

            for header in headers:
                buf = bytes(header)
                pbo_fileobj.write(buf)
                sha1.update(buf)

            # last header
            pbo_fileobj.write(b'\x00' * 21)
            sha1.update(b'\x00' * 21)

            for header in headers:
                with open(header_paths[header], 'rb') as data_file:
                    while True:
                        buf = data_file.read(FILE_BUFFER_SZ)
                        if len(buf) == 0:
                            break

                        pbo_fileobj.write(buf)
                        sha1.update(buf)

            pbo_fileobj.write(b'\x00')
            pbo_fileobj.write(sha1.digest())

    def verify(self, pbo_file):
        statresult = os.stat(pbo_file)

        with open(pbo_file, 'rb') as file:
            sha1 = hashlib.sha1()
            offset = 0

            while offset < statresult.st_size - 21:
                readsz = min(FILE_BUFFER_SZ, statresult.st_size - offset - 21)
                sha1.update(file.read(readsz))
                offset += readsz

            zero = file.read(1)
            if zero[0] != 0:
                self._error(ValueError, 'end of file checksum byte is not zero')

            checksum = file.read(20)

        if checksum == sha1.digest():
            return sha1.hexdigest()
        return False

    def _error(self, exception, message):
        if self.ignore_errors:
            printerr(message)
        else:
            raise exception(message)

    def _get_headers(self, stream):
        headers = []
        properties = []
        first_header = True

        while True:
            header = HeaderEntry.from_stream(stream)
            if header.mimetype == MIMETYPE_VERS:
                if not first_header:
                    self._error(ValueError, 'header with mimetype VERS not the first header found')

                while True:
                    key = read_str(stream)
                    if len(key) == 0:
                        break

                    val = read_str(stream)
                    properties.append([key, val])
                first_header = False
                continue
            if header.mimetype == MIMETYPE_CPRS:
                self._error(NotImplementedError, 'compressed PBO not supported')
                first_header = False
                continue
            if header.mimetype == MIMETYPE_ENCO:
                self._error(NotImplementedError, 'encoded PBO not supported')
                first_header = False
                continue

            if len(header.filename) == 0:
                break
            headers.append(header)
            first_header = False

        return headers, properties

    @staticmethod
    def asciiz(string):
        return string.encode('ascii') + b'\x00'

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


def printerr(message):
    print('error:', message, file=sys.stderr)
