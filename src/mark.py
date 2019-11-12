#!/usr/bin/env python
import os.path
import markdown
import jinja2
import argparse
import operator
import fcntl
import json
from functools import lru_cache
from contextlib import contextmanager

from pygments import style, formatters

style.Style.background_color = None

extensions = [
    'mdx_truly_sane_lists',
    'pymdownx.highlight',
    'pymdownx.superfences',
    'full_yaml_metadata',
    'toc',
]

extension_configs = {
    # 'pymdownx.highlight': {
    #     'noclasses': True,
    #     'pygments_style': 'lovelace',
    # }
}


@contextmanager
def lock(file_name):
    with open(file_name, 'wb') as fp:
        opts = fcntl.LOCK_EX
        fcntl.lockf(fp, opts)
        try:
            yield
        finally:
            fcntl.lockf(fp, fcntl.LOCK_UN)


@lru_cache(1)
def get_hl_styles():
    fmt = formatters.find_formatter_class('html')(style='lovelace')
    return fmt.get_style_defs(['.highlight'])


@lru_cache(1)
def get_env():
    env = jinja2.Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
        loader=jinja2.FileSystemLoader([
            os.path.join(os.path.dirname(__file__)),
            os.path.join(os.path.dirname(__file__), '..'),
        ])
    )
    return env


def process(text):
    md = markdown.Markdown(
        extensions=extensions, extension_configs=extension_configs)
    html = md.convert(text)
    return html, md.Meta


def render_one(text, template):
    html, meta = process(text)
    if template:
        tpl = get_env().get_template(template)
        html = tpl.render(
            meta=meta, content=jinja2.Markup(html), hl_styles=get_hl_styles())
    return html, meta


def parse_meta(fname):
    data = json.load(open(fname))
    data = [it for it in data.values() if os.path.exists(it['fname'])]
    result = []
    for meta in data:
        if not meta.get('draft'):
            result.append(meta)
    result.sort(key=operator.itemgetter('date'), reverse=True)
    return result


def render_index(metaname, template, indexname, tagdir):
    entries = parse_meta(metaname)
    tpl = get_env().get_template(template)

    content = tpl.render(hl_styles=get_hl_styles(), entries=entries)
    with open(indexname, 'w') as f:
        f.write(content)

    tentries = {}
    for it in entries:
        for t in it.get('tags', []):
            tentries.setdefault(t, []).append(it)

    for tag in sorted(tentries):
        content = tpl.render(hl_styles=get_hl_styles(), entries=tentries[tag])
        fname = os.path.join(os.path.dirname(indexname), tagdir, tag + '.html')
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        with open(fname, 'w') as f:
            f.write(content)


def update_meta(metaname, fname, meta, start_dir):
    lock_name = metaname + '.lock'
    with lock(lock_name):
        if os.path.exists(metaname):
            data = json.load(open(metaname))
        else:
            data = {}
        meta['date'] = str(meta['date'])
        meta['fname'] = fname
        meta['url'] = '/' + os.path.relpath(fname, start_dir)[:-3] + '.html'
        if data.get(fname) != meta:
            data[fname] = meta
            with open(metaname, 'w') as f:
                json.dump(data, f, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='template')
    parser.add_argument('-o', dest='output')
    parser.add_argument('--start-dir', default='START_DIR')
    parser.add_argument('--meta')
    parser.add_argument('--index', dest='index', action='store_true')
    parser.add_argument('--tags', dest='tags')
    parser.add_argument('input')
    args = parser.parse_args()

    if args.index:
        assert args.output
        render_index(args.input, args.template, args.output, args.tags)
    else:
        text = open(args.input).read()
        content, meta = render_one(text, args.template)
        if args.meta:
            update_meta(args.meta, args.input, meta, args.start_dir)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(content)
        else:
            print(content)

if __name__ == '__main__':
    main()