# -*- coding: utf-8 -*-

import argparse
import sys

_console_mode_header = """from hyperspyui.mainwindow import MainWindow
import numpy as np
from hyperspy.hspy import *
ui = MainWindow()
siglist = [signals.Signal(None), signals.Signal(None)]
"""
_header_num_lines = _console_mode_header.count('\n')

if __name__ == '__main__':
    from pyqode.python.backend.workers import JediCompletionProvider
    import jedi.api
    jedi.api.preload_module(["hyperspyui.mainwindow", "numpy",
                             "hyperspy.hspy"])

    class ConsoleJediCompletionProvider():
        @staticmethod
        def complete(code, line, column, path, encoding, prefix):
            code = _console_mode_header + code
            return JediCompletionProvider.complete(code,
                                                   line + _header_num_lines,
                                                   column, path, encoding,
                                                   prefix)

    """
    Server process' entry point
    """
    # setup argument parser and parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument("port", help="the local tcp port to use to run "
                        "the server")
    parser.add_argument('-s', '--syspath', nargs='*')
    args = parser.parse_args()

    # add user paths to sys.path
    if args.syspath:
        for path in args.syspath:
            print('append path %s to sys.path' % path)
            sys.path.append(path)

    from pyqode.core import backend

    # setup completion providers
    backend.CodeCompletionWorker.providers.append(
            ConsoleJediCompletionProvider())
    backend.CodeCompletionWorker.providers.append(
        backend.DocumentWordsProvider())

    # starts the server
    backend.serve_forever(args)