# pbopack

Packs and unpacks PBO files used in Arma 3.
Written in Python to be cross-platform.

[PBO format reference](https://community.bistudio.com/wiki/PBO_File_Format).

# Usage

Unpack a PBO to `dest/`:
```bash
./pbopack.py file.pbo dest/
```

Pack a directory to a PBO file:
```bash
./pbopack.py files-dir/ file.pbo
```

Verify the PBO checksum:
```bash
./pbopack.py file.pbo
```

# To Do

- Handle compressed/encoded PBO files
