import inspect
import tokenize
from textwrap import dedent
from typing import List
from vaa._internal import Simple


def get_validator_source(validator) -> str:
    if isinstance(validator, Simple):
        validator = validator.validator
    if not hasattr(validator, '__code__'):
        return ''
    try:
        lines, _ = inspect.getsourcelines(validator.__code__)
    except OSError:
        return ''
    lines = dedent('\n'.join(lines)).split('\n')

    try:
        _get_tokens(lines)
    except tokenize.TokenError:
        lines = _clear_lines(lines)

    lines = _drop_comments(lines)
    lines = _extract_decorator_args(lines)
    lines = _extract_assignment(lines)
    lines = _extract_lambda(lines)
    lines = _extract_lambda_body(lines)

    # drop trailing spaces and empty lines
    lines = '\n'.join(lines).rstrip().split('\n')
    # drop trailing comma
    if lines[-1] and lines[-1][-1] == ',':
        lines[-1] = lines[-1][:-1]

    if len(lines) > 1:
        return ''
    return ' '.join(lines).replace('_.', '')


def _clear_lines(lines: List[str]) -> List[str]:
    lines = [line.rstrip() for line in lines]
    lines = [line for line in lines if line]
    return lines


def _cut_lines(lines: List[str], first_token, last_token):
    lines = lines.copy()
    # drop unrelated lines
    first_line = first_token.start[0] - 1
    last_line = last_token.end[0]
    lines = lines[first_line:last_line]

    # drop unrelated symbols
    first_col = first_token.start[-1]
    last_col = last_token.end[-1]
    lines[-1] = lines[-1][:last_col]
    lines[0] = lines[0][first_col:]

    return lines


def _get_tokens(lines: List[str]) -> List[tokenize.TokenInfo]:
    tokens = tokenize.generate_tokens(iter(lines).__next__)
    exclude = {tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
    return [token for token in tokens if token.type not in exclude]


def _drop_comments(lines: List[str]):
    tokens = _get_tokens(lines)
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        row, col = token.start
        lines[row - 1] = lines[row - 1][:col].rstrip()
    return lines


def _extract_decorator_args(lines: List[str]):
    tokens = _get_tokens(lines)

    # drop decorator symbol
    if tokens[0].string == '@':
        tokens = tokens[1:]

    # proceed only if is call of a deal decorator
    if tokens[0].string != 'deal' or tokens[1].string != '.':
        return lines

    # find where decorator starts
    start = 0
    for index, token in enumerate(tokens):
        if token.string == '(':
            start = index
            break
    else:
        return lines
    first_token = tokens[start + 1]

    end = 0
    for index, token in enumerate(tokens):
        if token.string == ')':
            end = index
    last_token = tokens[end - 1]
    return _cut_lines(lines, first_token, last_token)


def _extract_assignment(lines: List[str]):
    tokens = _get_tokens(lines)

    # find where body starts
    start = 0
    for index, token in enumerate(tokens):
        if token.type == tokenize.OP and '=' in token.string:
            start = index
            break
        if token.type not in (tokenize.NAME, tokenize.DOT, tokenize.NEWLINE):
            return lines
    else:
        return lines
    first_token = tokens[start + 1]
    last_token = tokens[-1]
    return _cut_lines(lines, first_token, last_token)


def _extract_lambda(lines: List[str]):
    tokens = _get_tokens(lines)
    if tokens[0].string != '(':
        return lines
    if tokens[1].string != 'lambda':
        return lines

    end = 0
    for index, token in enumerate(tokens):
        if token.string == ')':
            end = index
    last_token = tokens[end - 1]

    return _cut_lines(lines, tokens[1], last_token)


def _extract_lambda_body(lines: List[str]):
    tokens = _get_tokens(lines)

    if tokens[0].string != 'lambda':
        return lines

    # find where body starts
    start = 0
    for index, token in enumerate(tokens):
        if token.type == tokenize.OP and ':' in token.string:
            start = index
            break
    else:
        return lines
    first_token = tokens[start + 1]
    last_token = tokens[-1]
    return _cut_lines(lines, first_token, last_token)
