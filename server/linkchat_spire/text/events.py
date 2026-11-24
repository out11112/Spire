"""Official event option wording (extracted_localization, v0.111.0).

``official_event_options.json`` maps each event to ``PAGE.OPTION`` entries with
the official title and description templates. ``label`` fills the templates
with the values the simulation already knows and joins them as ``标题：说明``.
"""
import re
from ..content.data import load as load_data

OPTIONS = load_data('official_event_options.json', encoding='utf-8')
MARKUP = re.compile(r'\[/?[a-z_]+(?:=[^\]]*)?\]')
CONDITION = re.compile(r'^(<=|>=|==|<|>)(-?\d+(?:\.\d+)?)$')


def _split(text, separator):
    parts, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        elif char == separator and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return parts


def _token(body, values):
    name, _, form = body.partition(':')
    if name == 'energyPrefix':
        return '能量'
    if name not in values:
        raise KeyError(f'Missing event text value: {name}')
    value = values[name]
    branch = lambda text: fill(text.replace('{}', str(value)), values)
    if not form:
        return str(value)
    if form == 'energyIcons()':
        return f'{value}能量'
    if form.startswith('plural:'):
        one, _, many = form[7:].partition('|')
        return fill(one if value == 1 else many or one, values)
    if form.startswith('cond:'):
        for part in _split(form[5:], '|'):
            test, found, text = part.partition('?')
            if not found:
                return branch(part)
            match = CONDITION.match(test)
            if match and eval_condition(match, value):
                return branch(text)
        return ''
    # IsMultiplayer-style flags: `yes|no`.
    yes, _, no = form.partition('|')
    return fill(yes if value else no, values)


def eval_condition(match, value):
    number = float(match.group(2))
    return {'<': value < number, '>': value > number, '<=': value <= number,
            '>=': value >= number, '==': value == number}[match.group(1)]


def fill(template, values):
    text = MARKUP.sub('', template)
    out, depth, start = '', 0, 0
    for index, char in enumerate(text):
        if char == '{':
            if depth == 0:
                start = index
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                out += _token(text[start + 1:index], values)
        elif depth == 0:
            out += char
    return re.sub(r'\s*\n\s*', '', out).strip()


def label(event, option, **values):
    """``event`` is the official UPPER_SNAKE id, ``option`` is ``PAGE.OPTION``."""
    entry = OPTIONS[event][option]
    title = fill(entry.get('title', ''), values)
    description = fill(entry.get('description', ''), values)
    return '：'.join(part for part in (title, description) if part)


# card_selection.json: the prompt above a deck selection screen.
SELECTION = {'discard': '选择{Amount}张牌来丢弃。', 'enchant': '选择{Amount}张牌来附魔。', 'exhaust': '选择{Amount}张牌来消耗。',
             'remove': '选择{Amount}张牌来移除。', 'transform': '选择{Amount}张牌来变化。', 'upgrade': '选择{Amount}张牌来升级。'}


def prompt(kind, amount=1):
    return fill(SELECTION[kind], {'Amount': amount})
