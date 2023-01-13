#
#   YaLafi LSP server
#   Copyright (C) 2023 torik42 (at GitHub)
#
#   This file is part of YaLafi-LS.
#
#   YaLafi-LS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see https://www.gnu.org/licenses.
#
#
#   This file is based on
#
#       https://github.com/openlawlibrary/pygls/blob/b7e6e5c/examples/json-extension/server/__main__.py
#
#   Original work Copyright(c) Open Law Library. All rights reserved.
#   Original work licensed under the Apache License, Version 2.0.
#   See NOTICE in the project root for additional notices.
#

import argparse
import logging

from .server import SERVER

logging.basicConfig(filename="pygls.log", level=logging.DEBUG, filemode="w")


def add_arguments(parser):
    parser.description = "Simple YaLafi LSP server"

    parser.add_argument(
        "--tcp", action="store_true",
        help="Use TCP server"
    )
    parser.add_argument(
        "--ws", action="store_true",
        help="Use WebSocket server"
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Bind to this address"
    )
    parser.add_argument(
        "--port", type=int, default=2087,
        help="Bind to this port"
    )


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    if args.tcp:
        SERVER.start_tcp(args.host, args.port)
    elif args.ws:
        SERVER.start_ws(args.host, args.port)
    else:
        SERVER.start_io()


if __name__ == '__main__':
    main()
