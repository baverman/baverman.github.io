---
date: 2019-10-01 00:00
draft: true
title: Some long post about very important staf on a planet Earth
tags: ['test', 'python', 'markdown']
...

dome longd testx asdflkjsd sdlkjsdfsdf erouweori werouwerwe
sdfsouf sdfousdoiusd sdousfdoiusdf sodiusdoiuf soduiosiduf sdofdiufss
sifsoiusdf soiusdoiu sdfoiusdofiu sd ofiusfd

[Some link](https://github.com/baverman)

* list item
  boo dsfd

  ```python
  def boo():
      pass
  ```

  para

* boo
  foo

  foo
  goo

  ```bash
  if [ -t "$one" ]; then
    echo boo
  fi
  ```

## Summary

Some para

### Some examples

```python
#!/usr/bin/env python
import sys
import os.path
import markdown
import jinja2
import argparse
from functools import lru_cache

from pygments import style
style.Style.background_color = None

extensions = [
    'mdx_truly_sane_lists',
    'pymdownx.highlight',
    'pymdownx.superfences',
    'full_yaml_metadata',
]

extension_configs = {
    'pymdownx.highlight': {
        'noclasses': True,
        'pygments_style': 'lovelace',
    }
}


@lru_cache(1)
def get_env():
    env = jinja2.Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
        loader=jinja2.FileSystemLoader(
            os.path.join(os.path.dirname(__file__), 'src'))
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
        html = tpl.render(meta=meta, content=jinja2.Markup(html))
    return html


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest='template')
    parser.add_argument('-o', dest='output')
    parser.add_argument('input')
    args = parser.parse_args()

    text = open(args.input).read()

    content = render_one(text, args.template)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(content)
    else:
        print(content)
```
