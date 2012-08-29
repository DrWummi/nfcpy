#!/usr/bin/python
# -*- coding: latin-1 -*-
# -----------------------------------------------------------------------------
# Copyright 2012 Stephen Tiedemann <stephen.tiedemann@googlemail.com>
#
# Licensed under the EUPL, Version 1.1 or - as soon they 
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
#
# http://www.osor.eu/eupl
#
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# -----------------------------------------------------------------------------

import logging
log = logging.getLogger()

import sys, os
import mimetypes

sys.path.insert(1, os.path.split(sys.path[0])[0])
import nfc
import nfc.ndef

def apps_parser(parser):
    parser.description = """The make command creates ndef
    messages."""
    
    subparsers = parser.add_subparsers()
    make_smartposter_parser(subparsers.add_parser(
            'smartposter',
            help='create a smartposter message'))
    make_wifipassword_parser(subparsers.add_parser(
            'wifipassword',
            help='create a wifi password token'))
    
def make_smartposter_parser(parser):
    parser.description = """The pack command creates an NDEF record
    for FILE. The record type is determined by the file type if
    possible, it may be explicitely set with the -t option. The record
    name (payload identifier) is set to the file name."""    
    
    parser.set_defaults(func=make_smartposter)
    parser.add_argument(
        "resource",
        help="record data file (or '-' for stdin)")
    parser.add_argument(
        "outfile", default="-", nargs="?", type=argparse.FileType('w'),
        help="output file (default: stdout)")
    parser.add_argument(
        "-T", metavar="TITLE", dest="titles", action="append", default=list(),
        help="smartposter title as '[language:]titlestring'")
    parser.add_argument(
        "-I", metavar="ICON", dest="icons", action="append", default=list(),
        type=argparse.FileType('r'),
        help="smartposter icon file")
    parser.add_argument(
        "-A", dest="action", default="default",
        help="smartposter action 'exec', 'save' or 'open'")
    
def make_smartposter(args):
    record = nfc.ndef.SmartPosterRecord(args.resource)
    for title in args.titles:
        lang, text = title.split(':', 1) if ':' in title else ('en', title)
        record.title[lang] = text
    for icon in args.icons:
        mimetype = mimetypes.guess_type(icon.name, strict=False)[0]
        if mimetype is None:
            log.error("file '%s' is not a recognized mime type" % icon.name)
            return
        mimetype, subtype = mimetype.split('/')
        if not mimetype == "image":
            log.error("file '%s' is not an image mime type" % icon.name)
            return
        record.icon[subtype] = icon.read()
    if not args.action in ('default', 'exec', 'save', 'open'):
        log.error("action must be one of 'default', 'exec', 'save', 'open'")
        return
    record.action = args.action

    message = nfc.ndef.Message(record)
    if args.outfile.name == "<stdout>":
        args.outfile.write(str(message).encode("hex"))
    else:
        args.outfile.write(str(message))

def make_wifipassword_parser(parser):
    parser.description = """The pack command creates an NDEF record
    for FILE. The record type is determined by the file type if
    possible, it may be explicitely set with the -t option. The record
    name (payload identifier) is set to the file name."""    
    
    parser.set_defaults(func=make_wifipassword)
    parser.add_argument(
        "pubkey", type=argparse.FileType('r'),
        help="enrollee's public key file ('-' reads from stdin)")
    parser.add_argument(
        "outfile", default="-", nargs="?", type=argparse.FileType('w'),
        help="output file (default: stdout)")
    parser.add_argument(
        "password", nargs="?",
        help="device password (default: 32 octet random string)")
    parser.add_argument(
        "--password-id", metavar="INT", default=None,
        help="password identifier (default: random number)")
    
def make_wifipassword(args):
    import random, string, hashlib
    if args.password is None:
        printable = string.digits + string.letters + string.punctuation
        args.password = ''.join([random.choice(printable) for i in xrange(32)])
    if args.password_id is None:
        args.password_id = random.randint(0x0010, 0xFFFF)
    pkhash = hashlib.sha256(args.pubkey.read()).digest()[0:20]
        
    record = nfc.ndef.WifiPasswordRecord()
    record.password['public-key-hash'] = pkhash
    record.password['password-id'] = args.password_id
    record.password['password'] = args.password
    
    message = nfc.ndef.Message(record)
    if args.outfile.name == "<stdout>":
        args.outfile.write(str(message).encode("hex"))
    else:
        args.outfile.write(str(message))
    

def pack_parser(parser):
    parser.description = """The pack command creates an NDEF record
    for FILE. The record type is determined by the file type if
    possible, it may be explicitely set with the -t option. The record
    name (payload identifier) is set to the file name."""

    parser.set_defaults(func=pack)
    parser.add_argument(
        "-t", metavar="type", dest="type", default="unknown",
        help="record type (default: %(default)s)")
    parser.add_argument(
        "-n", metavar="name", dest="name", default=None,
        help="record name (default: file name)")
    parser.add_argument(
        "file", metavar="FILE", type=argparse.FileType('r'),
        help="record data file ('-' for stdin)")
    parser.add_argument(
        "outfile", default="-", nargs="?", type=argparse.FileType('w'),
        help="output file (default: stdout)")
    
def pack(args):
    if args.type == 'unknown':
        mimetype = mimetypes.guess_type(args.file.name, strict=False)[0]
        if mimetype is not None: args.type = mimetype
    if args.name is None:
        args.name = args.file.name if args.file.name != "<stdin>" else ""
    record = nfc.ndef.Record(args.type, args.name, args.file.read())
    if args.outfile.name == "<stdout>":
        args.outfile.write(str(record).encode("hex"))
    else:
        args.outfile.write(str(record))

def split_parser(parser):
    parser.description = """The split command separates an an NDEF
    message into individual records. If data is read from a file,
    records are written as binary data into individual files with file
    names constructed from the input file base name, a hyphen followed
    by a three digit number and the input file name extension. If data
    is read from stdin, records are written to stdout as individual
    lines of hexadecimal strings."""
    
    parser.set_defaults(func=split)
    parser.add_argument(
        "input", metavar="message", type=argparse.FileType('r'),
        help="message file ('-' to read stdin)")
    parser.add_argument(
        "--keep-message-flags", dest="keepmf", action="store_true",
        help="do not reset message begin and end flags")
    
def split(args):
    log.info("reading message data from '{0}'".format(args.input.name))
    
    data = args.input.read()
    try: data = data.decode("hex")
    except TypeError: pass
        
    message = nfc.ndef.Message(data)
    for index, record in enumerate(message):
        if not args.keepmf:
            record._message_begin = record._message_end = False
        if args.input.name == "<stdin>":
            print str(record).encode("hex")
        else:
            fn = os.path.splitext(os.path.split(args.input.name)[1])
            fn = fn[0] + "-{0:03d}".format(index+1) + fn[1]
            log.info("writing {fn}".format(fn=fn))
            file(fn, "w").write(str(record))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog="ndeftool")
    parser.add_argument(
        "-v", dest="verbose", action="store_true",
        help="print info messages to stderr")
    parser.add_argument(
        "-d", dest="debug", action="store_true",
        help="print debug messages to stderr")

    subparsers = parser.add_subparsers(title="commands")
    apps_parser(subparsers.add_parser(
            'make', help='create an ndef message'))
    pack_parser(subparsers.add_parser(
            'pack', help='pack data into an ndef record'))
    split_parser(subparsers.add_parser(
            'split', help='split a message into records'))

    args = parser.parse_args()

    verbosity = logging.INFO if args.verbose else logging.ERROR
    verbosity = logging.DEBUG if args.debug else verbosity
    logging.basicConfig(level=verbosity, format='%(message)s')

    log.debug(args)
    args.func(args)

