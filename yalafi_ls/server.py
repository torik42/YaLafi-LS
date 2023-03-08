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

import json
import sys
import subprocess
import uuid
from pathlib import Path
from typing import Optional, List

from pygls.server import LanguageServer
from pygls.workspace import utf16_num_units

from lsprotocol.types import (
    INITIALIZED,
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_SAVE,
)
from lsprotocol.types import (
    CodeAction,
    CodeActionKind,
    CodeActionOptions,
    CodeActionParams,
    ConfigurationItem,
    Diagnostic,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidSaveTextDocumentParams,
    InitializedParams,
    MessageType,
    Position,
    Range,
    TextDocumentContentChangeEvent,
    TextDocumentEdit,
    TextEdit,
    VersionedTextDocumentIdentifier,
    WorkDoneProgressBegin,
    WorkDoneProgressEnd,
    WorkDoneProgressReport,
    WorkspaceConfigurationParams,
    WorkspaceEdit,
)

# Extend lsprotocol.types Range:
def range_in(a: Range, b: Range):  # pylint: disable=invalid-name
    """Check whether Range b is included in Range a."""
    if (a.start <= b.start) & (b.end <= a.end):
        return True
    else:
        return False
Range.__contains__ = range_in

# The following mapping table is based on
#    https://github.com/mfbehrens99/linter-yalafi/blob/e69af00/lib/linter-yalafi.js
# All errors were changed to warnings.
# Original work licensed under the MIT license.
# See NOTICE in the project root for license information
LT_SEVERITY_MAPPING = {
    'CASING': DiagnosticSeverity.Warning,  # was error
    'COLLOCATIONS': DiagnosticSeverity.Warning,  # was error
    'COLLOQUIALISMS': DiagnosticSeverity.Information,
    'COMPOUNDING': DiagnosticSeverity.Warning,  # was error
    'CONFUSED_WORDS': DiagnosticSeverity.Information,
    'CORRESPONDENCE': DiagnosticSeverity.Warning,  # was error
    'EINHEIT_LEERZEICHEN': DiagnosticSeverity.Warning,
    'EMPFOHLENE_RECHTSCHREIBUNG': DiagnosticSeverity.Information,
    'FALSE_FRIENDS': DiagnosticSeverity.Information,
    'GENDER_NEUTRALITY': DiagnosticSeverity.Information,
    'GRAMMAR': DiagnosticSeverity.Warning,  # was error
    'HILFESTELLUNG_KOMMASETZUNG': DiagnosticSeverity.Warning,
    'IDIOMS': DiagnosticSeverity.Information,
    'MISC': DiagnosticSeverity.Warning,
    'MISUSED_TERMS_EU_PUBLICATIONS': DiagnosticSeverity.Warning,
    'NONSTANDARD_PHRASES': DiagnosticSeverity.Information,
    'PLAIN_ENGLISH': DiagnosticSeverity.Information,
    'PROPER_NOUNS': DiagnosticSeverity.Warning,  # was error
    'PUNCTUATION': DiagnosticSeverity.Warning,  # was error
    'REDUNDANCY': DiagnosticSeverity.Warning,  # was error
    'REGIONALISMS': DiagnosticSeverity.Information,
    'REPETITIONS': DiagnosticSeverity.Information,
    'SEMANTICS': DiagnosticSeverity.Warning,
    'STYLE': DiagnosticSeverity.Information,
    'TYPOGRAPHY': DiagnosticSeverity.Warning,
    'TYPOS': DiagnosticSeverity.Warning,  # was error
    'WIKIPEDIA': DiagnosticSeverity.Information,
}

PLAIN_TEXT = 'plain_text'
REPLACEMENTS = 'replacements'

json_decoder = json.JSONDecoder()

def json_get(dic, item, typ):
    """
    Return values from a parsed json structure and test the type.

    dic :  parsed json structure
    item : the key of the item of interest
    typ :  the expected Type of the item
    """
    if not isinstance(dic, dict):
        raise TypeError("Expect dic to be of type dict.")
    ret = dic.get(item)
    if not isinstance(ret, typ):
        raise TypeError(f"Expect the parsed item to be of type {typ}.")
    return ret

def full_spellcheck(ls, text_document_uri):
    """
    Run YaLafi and populate diagnostics.

    This is a simple implementation, which runs YaLafi on the full document as
    a subprocess and maps the results to diagnostic entries.
    """
    text_doc = ls.workspace.get_document(text_document_uri)
    ls.show_message_log(
        f"[Info] Spellcheck Document \"{text_doc.path}\""
    )
    if text_doc.path:
        token = str(uuid.uuid4())
        ls.progress.create(token)
        ls.progress.begin(token,
            WorkDoneProgressBegin(title='Spellchecking', message='Run YaLafi')
        )
        success = False
        try:
            result = subprocess.run(
                [sys.executable] +
                ['-m', 'yalafi.shell', '--out', 'json'] +
                ls.yalafi_options +
                [text_doc.path],
                cwd=Path(text_doc.path).parent, capture_output=True,
                encoding='UTF-8', check=True
                )
            ls.progress.report(token,
                WorkDoneProgressReport(message='Parse result'),
            )
            dic = json_decoder.decode(result.stdout)
            success = True
        except subprocess.CalledProcessError as exception:
            ls.show_message_log(
                "[Error] Could not run Yalafi. " +
                "Maybe the command line options are not correctly set."
            )
            ls.show_message_log(
                "[Error] Command was:\n    [\n      " +
                ",\n      ".join(exception.cmd) +
                "\n    ]"
            )
            ls.show_message_log(
                "[Error] Stderr:\n    " +
                "\n    ".join(str(exception.stderr).split('\n'))
            )
        except FileNotFoundError as exception:
            ls.show_message_log(
                "[Error] Could not run Yalafi because " +
                exception.filename +
                " was not found."
            )
        except json.decoder.JSONDecodeError:
            ls.show_message_log('[Error] YaLafi did not returned valid JSON.')
            ls.show_message_log(
                "[Error] YaLafi Stderr:\n    " +
                "\n    ".join(str(result.stderr).split('\n'))
            )
        finally:
            if not success:
                ls.show_message(
                    'Could not run YaLafi. ' +
                    'See YaLafi output for more information.',
                    msg_type=MessageType.Error)
                ls.progress.end(token, WorkDoneProgressEnd(message='Failed'))
        if success:
            ls.progress.report(token,
                WorkDoneProgressReport(message='Create Diagnostics'),
            )
            matches = json_get(dic, 'matches', list)
            diagnostics = []
            for match in matches:
                diagnostics.append(_create_diagnostic_from_match(match, text_doc))
            text_doc.diagnostics = diagnostics
            ls.publish_diagnostics(text_doc.uri, text_doc.diagnostics)
            ls.progress.end(token, WorkDoneProgressEnd(message='Finished'))


def _create_diagnostic_from_match(match, text_doc):
    offset = json_get(match, 'offset', int) -1
    length = json_get(match, 'length', int)
    lt_message = json_get(match, 'message', str)
    lt_short_message = json_get(match, 'shortMessage', str)
    lt_rule = json_get(match, 'rule', dict)
    lt_replacements = json_get(match, 'replacements', list)
    plain_text, context = _mark_context(json_get(match, 'context', dict))
    message = f"{lt_short_message}\n{lt_message}\nContext: {context}"
    if lt_rule['category']['id'] in LT_SEVERITY_MAPPING.keys():
        severity = LT_SEVERITY_MAPPING[lt_rule['category']['id']]
    else:
        severity = DiagnosticSeverity.Error
    return Diagnostic(
        range=Range(
            start=_position_from_offset(text_doc.source,
                                       text_doc.lines, offset),
            end=_position_from_offset(text_doc.source,
                                     text_doc.lines, offset + length)
        ),
        message=message,
        code=lt_rule['id'].lower(),
        severity=severity,
        data={PLAIN_TEXT: plain_text, REPLACEMENTS: lt_replacements[:10]},
        source=SERVER.SOURCE_NAME
    )


def _mark_context(context: dict):
    """
    Highlight problem in context.

    Args:
        context: dictionary with keys `text`, `offset` and `length`.

    Returns:
        A tuple `(plain_text, marked_context)`, where `plain_text` is
        the substring `text[offset:offset+length]` and `marked_context`
        has added markup before and after `offset` and `offset+length`,
        respectively.
    """
    text = context['text']
    offset = context['offset']
    length = context['length']
    plain_text = text[offset:offset+length]
    marked_context = text[:offset] + '>>>' + plain_text + '<<<' \
                     + text[offset+length:]
    return plain_text, marked_context


def _position_from_offset(tex, lines, offset):
    lin = tex.count('\n', 0, offset)
    col = offset - tex.rfind('\n', 0, offset)
    position = Position(line=lin, character=col)
    return position


def shift_diagnostics(diagnostics: List[Diagnostic],
                      change: TextDocumentContentChangeEvent) -> None:
    """Shift all diagnostics according to the changes."""
    if len(diagnostics) == 0:
        return
    change_start = change.range.start
    change_end = change.range.end
    change_rows = change.text.count("\n")
    change_single_line = False
    if (change_start.line == change_end.line) & (change_rows == 0):
        change_single_line = True
    change_length = utf16_num_units(change.text)
    change_line_diff = change_start.line - change_end.line + change_rows
    change_character_diff = change_start.character - change_end.character + change_length
    for d in diagnostics:  # pylint: disable=invalid-name
        if d.range.end < change_start:
            continue
        elif d.range.start.line > change_end.line:
            d.range.start.line += change_line_diff
            d.range.end.line += change_line_diff
        elif (change_start <= d.range.start) & (d.range.end <= change_end):
            diagnostics.remove(d)
        elif change_single_line & (d.range.start.line == change_start.line):
            if change_end.character <= d.range.start.character:
                d.range.start.character += change_character_diff
                d.range.end.character += change_character_diff


class YaLafiLanguageServer(LanguageServer):
    """
    LSP server for spellchecking LaTeX documents with YaLafi.
    """
    CONFIGURATION_SECTION = 'yalafi'
    SOURCE_NAME = 'YaLafi'

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.yalafi_options = []


SERVER = YaLafiLanguageServer(name="yalafi-language-server",
                              version="0.0.1")


def fetch_configuration(ls):
    """
    Fetch configuration from client.
    """
    try:
        ls.show_message_log('[Info] Fetching configuration')
        config = ls.get_configuration(WorkspaceConfigurationParams(items=[
            ConfigurationItem(
                scope_uri='',
                section='yalafi')
        ])).result(3)

        ls.show_message_log('[Info] Fetched configuration')
        ls.yalafi_options = config[0].get('commandLineOptions')
    except Exception as exception:
        ls.show_message_log(
            '[Warning] Could not fetch configuration\n    ' +
            "\n    ".join(str(exception).split('\n'))
        )


@SERVER.thread()
@SERVER.feature(INITIALIZED)
def initiliazed(ls: YaLafiLanguageServer, _params: InitializedParams) -> None:
    """Connection is initialized."""
    ls.show_message_log('[Info] Initialized')


@SERVER.thread()
@SERVER.feature(
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionOptions(
        code_action_kinds=[
            CodeActionKind.QuickFix
        ],
    ),
)
def code_action(ls, params: CodeActionParams) -> Optional[List[CodeAction]]:
    """
    Provide quick fix for spelling mistakes which can be automatically
    fixed.
    """
    ls.show_message_log('[Info] Create code action')
    uri = params.text_document.uri
    document = ls.workspace.get_document(uri)
    version = 0 if document.version is None else document.version
    document_identifier = VersionedTextDocumentIdentifier(uri=uri,
                                                          version=version)

    code_actions = []
    for diag in params.context.diagnostics:
        if ( diag.source == SERVER.SOURCE_NAME
             and diag.data[REPLACEMENTS] is not None
             and len(diag.data[REPLACEMENTS]) > 0 ):
            offset_beg = document.offset_at_position(diag.range.start)
            offset_end = document.offset_at_position(diag.range.end)
            if document.source[offset_beg:offset_end] != diag.data[PLAIN_TEXT]:
                break
            for repl in diag.data[REPLACEMENTS]:
                title = repl['value']
                if 'shortDescription' in repl.keys():
                    title += ' (' + repl['shortDescription'] + ')'
                code_actions.append(
                    CodeAction(
                        title=title,
                        diagnostics=[diag],
                        kind=CodeActionKind.QuickFix,
                        edit=WorkspaceEdit(
                            document_changes=[
                                TextDocumentEdit(
                                    text_document=document_identifier,
                                    edits=[
                                        TextEdit(
                                        range=diag.range,
                                        new_text=repl['value']
                                        )
                                    ]
                                )
                            ]
                        )
                        )
                )
                if len(code_actions)>10:
                    break
    return code_actions


def _update_diagnostics(ls, params):
    ls.show_message_log('[Info] Updating diagnostics')

    text_doc = ls.workspace.get_document(params.text_document.uri)
    for change in params.content_changes:
        shift_diagnostics(text_doc.diagnostics, change)


@SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    """Move diagnostics after changing the document."""
    text_doc = ls.workspace.get_document(params.text_document.uri)
    _update_diagnostics(ls, params)
    ls.publish_diagnostics(text_doc.uri, text_doc.diagnostics)


@SERVER.thread()
@SERVER.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls, params: DidSaveTextDocumentParams):
    """Spellcheck the document after saving the document."""
    fetch_configuration(ls)
    full_spellcheck(ls, params.text_document.uri)


@SERVER.thread()
@SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: YaLafiLanguageServer, params: DidCloseTextDocumentParams):
    """Delete Diagnostics after closing the document."""
    text_doc = ls.workspace.get_document(params.text_document.uri)
    ls.publish_diagnostics(text_doc.uri, [])
