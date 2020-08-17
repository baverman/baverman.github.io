import sys
from os.path import dirname
from build import make, fset, allfiles

sys.path.insert(0, './src')
import mark

dest = 'public'
mark_cmd = './src/mark.py --start-dir src -o {target} -t {reqs[1]} {req}'
index = f'{dest}/index.html'
projects = f'{dest}/projects.html'
blog = fset('src/blog/**/*.md', 'src/%.md', f'{dest}/%.html')
blog_meta = 'src/blog/meta.json'

image_dirs = fset('src/**/img', 'src/%', f'{dest}/%')
image_files = {t: allfiles(r) for t, r in image_dirs.items()}


make(image_files, deps=True)
make(image_dirs,
     cmd='cp -r {reqs} {dirname(target)}')

@make(blog, 'src/blog/post.html.j2')
def section_blog(rule, target, dep):
    render_markdown(target, dep.reqs[0], dep.reqs[1], meta=blog_meta)

@make(projects, ['src/projects.md', 'src/page.html.j2'])
def section_projects(rule, target, dep):
    render_markdown(target, dep.reqs[0], dep.reqs[1])

@make(index, [blog_meta, 'src/index.html.j2'])
def section_index(rule, target, dep):
    mark.render_index(dep.reqs[0], dep.reqs[1], target, 'blog/tags')

make(blog_meta, order=blog.dest)

make([index, projects, blog.dest], deps=['src/mark.py','src/base.html.j2'])

make('all', [index, projects, image_dirs.dest], phony=True)

make('push', 'all', phony=True,
     cmd='rsync -zPr {dest}/. bvrmn.com:~/sites/bvrmn.com/')


def render_markdown(target, infile, template, meta=None):
    text = open(infile).read()
    content, metadata = mark.render_one(text, template)

    if meta:
        mark.update_meta(meta, infile, metadata, 'src')

    with open(target, 'w') as f:
        f.write(content)
