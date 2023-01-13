# YaLafi LSP Server

An [LSP](https://microsoft.github.io/language-server-protocol/) server for proofreading LaTeX documents using [YaLafi (yet another LateX filter)](http://github.com/torik42/YaLafi) and [LanguageTool](https://www.languagetool.org) in different editors.
It serves as a basis for the corresponding [vscode extension](http://github.com/torik42/YaLafi-ls-vscode).

The server is written in Python using [pygls](https://github.com/openlawlibrary/pygls) and [lsprotocol](https://github.com/microsoft/lsprotocol).
The current implementation is very basic and just calls YaLafi on save.

## Installation

YaLafi-LS is available on [PyPI](https://www.pypi.org) and can be installed with `python -m pip install YaLafi-LS`.
This will automatically also install [YaLafi](http://github.com/torik42/YaLafi).
However, you may need to install [LanguageTool](https://www.languagetool.org), see the [installation guide for YaLafi](https://github.com/torik42/YaLafi#installation).
