#!/usr/bin/env python3
"""Repack recovery.img: inject /workspace/prop.default into the ramdisk cpio.

Pure Python 3 stdlib only (gzip, lzma, struct, os, sys, hashlib, subprocess).
No external cpio / mkbootimg / magiskboot required.
"""

import os
import sys
import struct
import gzip
import lzma
import hashlib
import subprocess

WORKSPACE = '/workspace'
RECOVERY = os.path.join(WORKSPACE, 'recovery.img')
PROP_FILE = os.path.join(WORKSPACE, 'prop.default')
BACKUP = os.path.join(WORKSPACE, 'recovery.img.orig')
HEADER_SIZE = 4096


def align_up(x, p):
    return (x + p - 1) // p * p


def parse_header_fields(hdr):
    if hdr[:8] != b'ANDROID!':
        raise ValueError('Not an Android boot image (bad magic: %r)' % hdr[:8])
    return {
        'kernel_size':   struct.unpack('<I', hdr[8:12])[0],
        'kernel_addr':   struct.unpack('<I', hdr[12:16])[0],
        'ramdisk_size':  struct.unpack('<I', hdr[16:20])[0],
        'ramdisk_addr':  struct.unpack('<I', hdr[20:24])[0],
        'second_size':   struct.unpack('<I', hdr[24:28])[0],
        'second_addr':   struct.unpack('<I', hdr[28:32])[0],
        'tags_addr':     struct.unpack('<I', hdr[32:36])[0],
        'page_size':     struct.unpack('<I', hdr[36:40])[0],
        'dt_size':       struct.unpack('<I', hdr[40:44])[0],
    }


def detect_format(data):
    if len(data) >= 2 and data[:2] == b'\x1f\x8b':
        return 'gzip'
    if len(data) >= 6 and data[:6] == b'\xfd7zXZ\x00':
        return 'xz'
    if len(data) >= 1 and data[0] == 0x5d:
        return 'lzma_alone'
    if len(data) >= 4 and data[:4] == b'\x04\x22\x4d\x18':
        return 'lz4'
    if len(data) >= 6 and data[:6] in (b'070701', b'070702'):
        return 'cpio'
    return 'unknown'


def decompress_ramdisk(data, fmt):
    if fmt == 'gzip':
        return gzip.decompress(data)
    if fmt == 'xz':
        return lzma.decompress(data, format=lzma.FORMAT_XZ)
    if fmt == 'lzma_alone':
        return lzma.decompress(data, format=lzma.FORMAT_ALONE)
    if fmt == 'cpio':
        return data
    if fmt == 'lz4':
        sys.stderr.write('ERROR: lz4 compression detected but lz4 is not available.\n')
        sys.stderr.write('First 16 bytes: %s\n' % data[:16].hex())
        sys.exit(2)
    sys.stderr.write('ERROR: unknown ramdisk compression format.\n')
    sys.stderr.write('First 16 bytes: %s\n' % data[:16].hex())
    sys.exit(2)


def recompress_ramdisk(data, fmt):
    if fmt == 'gzip':
        return gzip.compress(data, compresslevel=9, mtime=0)
    if fmt == 'xz':
        return lzma.compress(data, format=lzma.FORMAT_XZ)
    if fmt == 'lzma_alone':
        return lzma.compress(data, format=lzma.FORMAT_ALONE)
    if fmt == 'cpio':
        return data
    raise ValueError('Cannot recompress format: %s' % fmt)


def _hex8(value):
    return ('%08X' % (value & 0xFFFFFFFF)).encode('ascii')


def parse_cpio(data):
    """Parse cpio newc format. Returns (entries, magic).

    Each entry is a dict with all metadata plus 'name' (str, no NUL) and
    'data' (bytes). The TRAILER!!! entry is included as the last entry.
    """
    entries = []
    magic = None
    pos = 0
    n = len(data)
    while pos + 110 <= n:
        header = data[pos:pos + 110]
        magic_field = header[:6]
        if magic_field not in (b'070701', b'070702'):
            break
        if magic is None:
            magic = magic_field.decode('ascii')

        def pf(off):
            return int(header[off:off + 8].decode('ascii'), 16)

        entry = {
            'magic':     magic_field.decode('ascii'),
            'ino':       pf(6),
            'mode':      pf(14),
            'uid':       pf(22),
            'gid':       pf(30),
            'nlink':     pf(38),
            'mtime':     pf(46),
            'filesize':  pf(54),
            'devmajor':  pf(62),
            'devminor':  pf(70),
            'rdevmajor': pf(78),
            'rdevminor': pf(86),
            'namesize':  pf(94),
            'check':     pf(102),
        }

        name_start = pos + 110
        name_raw = data[name_start:name_start + entry['namesize']]
        entry['name'] = name_raw.rstrip(b'\x00').decode('utf-8', errors='replace')

        name_total = 110 + entry['namesize']
        name_pad = (4 - (name_total % 4)) % 4
        data_start = name_start + entry['namesize'] + name_pad
        entry['data'] = data[data_start:data_start + entry['filesize']]

        data_pad = (4 - (entry['filesize'] % 4)) % 4
        pos = data_start + entry['filesize'] + data_pad

        entries.append(entry)
        if entry['name'] == 'TRAILER!!!':
            break

    return entries, magic


def pack_cpio_entry(entry):
    out = bytearray()
    name_bytes = entry['name'].encode('utf-8') + b'\x00'
    namesize = len(name_bytes)

    h = bytearray()
    h += entry['magic'].encode('ascii')
    h += _hex8(entry['ino'])
    h += _hex8(entry['mode'])
    h += _hex8(entry['uid'])
    h += _hex8(entry['gid'])
    h += _hex8(entry['nlink'])
    h += _hex8(entry['mtime'])
    h += _hex8(entry['filesize'])
    h += _hex8(entry['devmajor'])
    h += _hex8(entry['devminor'])
    h += _hex8(entry['rdevmajor'])
    h += _hex8(entry['rdevminor'])
    h += _hex8(namesize)
    h += _hex8(entry['check'])
    out += h
    out += name_bytes
    name_total = 110 + namesize
    name_pad = (4 - (name_total % 4)) % 4
    out += b'\x00' * name_pad
    out += entry['data']
    data_pad = (4 - (entry['filesize'] % 4)) % 4
    out += b'\x00' * data_pad
    return bytes(out)


def pack_cpio(entries, magic):
    out = bytearray()
    for e in entries:
        out += pack_cpio_entry(e)
    trailer = {
        'magic':     magic,
        'ino':       0,
        'mode':      0,
        'uid':       0,
        'gid':       0,
        'nlink':     1,
        'mtime':     0,
        'filesize':  0,
        'devmajor':  0,
        'devminor':  0,
        'rdevmajor': 0,
        'rdevminor': 0,
        'namesize':  len('TRAILER!!!') + 1,
        'check':     0,
        'name':      'TRAILER!!!',
        'data':      b'',
    }
    out += pack_cpio_entry(trailer)
    pad = (512 - (len(out) % 512)) % 512
    out += b'\x00' * pad
    return bytes(out)


def extract_segments(img, info):
    page_size = info['page_size']
    ks = info['kernel_size']
    rs = info['ramdisk_size']
    ss = info['second_size']
    dt_size = info['dt_size']

    kernel_off = 1 * page_size
    ramdisk_off = kernel_off + align_up(ks, page_size)
    second_off = ramdisk_off + align_up(rs, page_size)
    dt_off = second_off + align_up(ss, page_size)

    kernel = img[kernel_off:kernel_off + ks]
    ramdisk = img[ramdisk_off:ramdisk_off + rs]
    second = img[second_off:second_off + ss]
    dt = img[dt_off:dt_off + dt_size]
    return kernel, ramdisk, second, dt


def process_image(img_path, target_prop):
    with open(img_path, 'rb') as f:
        img = f.read()

    header = bytearray(img[:HEADER_SIZE])
    info = parse_header_fields(header)
    page_size = info['page_size']

    kernel, ramdisk, second, dt = extract_segments(img, info)

    fmt = detect_format(ramdisk)
    print('Ramdisk compression format: %s' % fmt)
    if fmt == 'lz4' or fmt == 'unknown':
        decompress_ramdisk(ramdisk, fmt)  # will exit with diagnostic

    cpio = decompress_ramdisk(ramdisk, fmt)
    entries, magic = parse_cpio(cpio)
    print('Parsed %d cpio entries (magic=%s)' % (len(entries), magic))

    # Split out TRAILER!!! so we can insert before it if needed.
    trailer_idx = None
    for i, e in enumerate(entries):
        if e['name'] == 'TRAILER!!!':
            trailer_idx = i
            break
    if trailer_idx is not None:
        non_trailer = entries[:trailer_idx]
    else:
        non_trailer = list(entries)

    # Locate prop.default
    prop_entry = None
    for e in non_trailer:
        if e['name'] == 'prop.default':
            prop_entry = e
            break

    target_sha = hashlib.sha256(target_prop).hexdigest()
    target_size = len(target_prop)

    if prop_entry is not None:
        old_data = prop_entry['data']
        old_sha = hashlib.sha256(old_data).hexdigest()
        old_size = len(old_data)
        old_mode = prop_entry['mode']
        print('prop.default found in ramdisk.')
        print('  Before: %d bytes, sha256=%s, mode=0o%o' % (old_size, old_sha, old_mode))
        print('  After:  %d bytes, sha256=%s' % (target_size, target_sha))
        prop_entry['data'] = target_prop
        prop_entry['filesize'] = target_size
        # Force regular file mode (S_IFREG | 0644). Original ramdisk had
        # prop.default as a symlink (S_IFLNK | 0644), which breaks AIK-based
        # tools (twrpdtgen, unpackbootimg) that cannot handle symlink entries.
        prop_entry['mode'] = 0o100644
        # namesize and all other metadata preserved
        if old_mode != 0o100644:
            print('  mode fixed: 0o%o -> 0o100644 (regular file)' % old_mode)
    else:
        print('prop.default NOT found in ramdisk; inserting new entry.')
        print('  Before: (none - new entry)')
        print('  After:  %d bytes, sha256=%s' % (target_size, target_sha))
        new_entry = {
            'magic':     magic,
            'ino':       0,
            'mode':      0o100644,
            'uid':       0,
            'gid':       0,
            'nlink':     1,
            'mtime':     0,
            'filesize':  target_size,
            'devmajor':  0,
            'devminor':  0,
            'rdevmajor': 0,
            'rdevminor': 0,
            'namesize':  len('prop.default') + 1,
            'check':     0,
            'name':      'prop.default',
            'data':      target_prop,
        }
        non_trailer.append(new_entry)

    new_cpio = pack_cpio(non_trailer, magic)
    new_ramdisk = recompress_ramdisk(new_cpio, fmt)
    new_rs = len(new_ramdisk)

    print('Original ramdisk_size: %d' % info['ramdisk_size'])
    print('New ramdisk_size:      %d' % new_rs)

    # Patch only ramdisk_size (offset 16), keep everything else byte-identical.
    struct.pack_into('<I', header, 16, new_rs)

    out = bytearray()
    out += header  # 4096 bytes (1 page)
    out += kernel
    out += b'\x00' * (align_up(len(kernel), page_size) - len(kernel))
    out += new_ramdisk
    out += b'\x00' * (align_up(new_rs, page_size) - new_rs)
    out += second
    out += b'\x00' * (align_up(len(second), page_size) - len(second))
    out += dt
    out += b'\x00' * (align_up(len(dt), page_size) - len(dt))

    return bytes(out), info['ramdisk_size'], new_rs


def verify_image(img_path, target_prop):
    with open(img_path, 'rb') as f:
        img = f.read()

    header = img[:HEADER_SIZE]
    info = parse_header_fields(header)
    _, ramdisk, _, _ = extract_segments(img, info)
    fmt = detect_format(ramdisk)
    cpio = decompress_ramdisk(ramdisk, fmt)
    entries, _ = parse_cpio(cpio)

    found = None
    for e in entries:
        if e['name'] == 'prop.default':
            found = e
            break

    if found is None:
        print('Verify: prop.default not found in repacked image -> FAIL')
        return False

    prop_sha = hashlib.sha256(found['data']).hexdigest()
    target_sha = hashlib.sha256(target_prop).hexdigest()
    print('Verify: repacked prop.default = %d bytes, sha256=%s'
          % (len(found['data']), prop_sha))
    print('Verify: target   prop.default = %d bytes, sha256=%s'
          % (len(target_prop), target_sha))

    if found['data'] == target_prop:
        print('Verify: content match -> PASS')
        return True
    print('Verify: content mismatch -> FAIL')
    return False


def main():
    if not os.path.exists(RECOVERY):
        sys.stderr.write('ERROR: %s not found\n' % RECOVERY)
        sys.exit(1)
    if not os.path.exists(PROP_FILE):
        sys.stderr.write('ERROR: %s not found\n' % PROP_FILE)
        sys.exit(1)

    with open(PROP_FILE, 'rb') as f:
        target_prop = f.read()

    orig_size = os.path.getsize(RECOVERY)
    print('Original recovery.img size: %d' % orig_size)

    # Backup for rollback during this run only.
    with open(RECOVERY, 'rb') as f:
        orig_bytes = f.read()
    with open(BACKUP, 'wb') as f:
        f.write(orig_bytes)

    try:
        new_img, old_rs, new_rs = process_image(RECOVERY, target_prop)
        with open(RECOVERY, 'wb') as f:
            f.write(new_img)
        new_size = len(new_img)
        print('New recovery.img size:      %d' % new_size)
        print('Size delta: %d bytes' % (new_size - orig_size))

        print('\n--- Verification ---')
        r = subprocess.run(['/usr/bin/file', RECOVERY],
                           capture_output=True, text=True)
        print(r.stdout.strip())

        ok = verify_image(RECOVERY, target_prop)
        if not ok:
            sys.exit(1)
    finally:
        if os.path.exists(BACKUP):
            os.remove(BACKUP)


if __name__ == '__main__':
    main()
