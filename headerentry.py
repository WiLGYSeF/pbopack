import struct


MIMETYPE_VERS = 0x56657273
MIMETYPE_CPRS = 0x43707273
MIMETYPE_ENCO = 0x456e6372
MIMETYPE_DUMM = 0x00000000


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
            raise ValueError('header too short')

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
