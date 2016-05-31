class LineParseError(Exception):
    def __init__(self, index, msg=None):
        Exception.__init__(self, msg)
        self.index = index



class Token(object):
    def __init__(self, val, prefix=' '):
        self.prefix = prefix
        self.value  = val


# returns (Token, i), or a string at the end
def _get_token(line, i):

    # find the start of the token (after whitespace prefix)
    i0 = i
    while True:
        if i == len(line):
            return (Token('', line), i)
        if not str.isspace(line[i]):
            break
        i = i + 1
    i1 = i

    quote  = ' '
    escape = None
    token = ''
    while True:
        if i == len(line):
            if quote:
                raise LineParseError(i, "unclosed quote")
            if escape:
                raise LineParseError(i, "unclosed escape")
            else:
                return (Token(token, line[i0:i1]), i)

        if quote == ' ': # consuming whitespace prefix
            if not str.isspace(line[i]):
                quote = None
            else:
                i1 = i = i + 1
            continue

        if escape:
            token = token + line[i]
            escape = None
        elif line[i] == quote:
            quote = None
        elif line[i] == '#' and not quote:
            if token == '':
                return (line[i0:], len(line))
            break
        elif str.isspace(line[i]) and not quote:
            break
        elif line[i] in '"\'' and not quote:
            quote = line[i]
        elif line[i] == '\\' and not quote:
            escape = '\\'
        else:
            token = token + line[i]
        i = i + 1
    return (Token(token, line[i0:i1]), i)



class Line(object):
    def __init__(self, rawline):
        self.raw_line = rawline
        self.tokens = []
        self.suffix = ''
        i = 0
        while True:
            (tok, i) = _get_token(rawline, i)
            if isinstance(tok, str):
                self.suffix = tok
                break
            if tok.value == '':
                self.suffix = tok.prefix + tok.value
                break
            self.tokens.append(tok)
            if i == len(rawline):
                break

    def token_values(self):
        return [tok.value for tok in self.tokens]
