.SUFFIXES:
.PHONY: all push

MAKEFLAGS += -r

dest := public

blog.src := $(shell find src -name '*.md')
blog.dest := $(patsubst src/%.md, $(dest)/%.html, $(blog.src))
blog.dirs := $(dir $(blog.dest))

img.src := $(shell find src -type d -name img)
img.dest := $(patsubst src/%, $(dest)/%, $(img.src))

html.dest := $(dest)/projects.html $(blog.dest) $(dest)/index.html

make.markdown = ./src/mark.py --start-dir src -o $@ -t $(word 2,$^) $<

all: $(html.dest) $(img.dest)

$(blog.dirs) $(dest):
	mkdir -p $@

$(dest)/%/img: src/%/img
	cp -r $< $(@D)

$(html.dest): src/mark.py src/base.html.j2 | $(dest)

$(dest)/projects.html: src/projects.md src/page.html.j2
	$(make.markdown)

$(dest)/blog/%.html: src/blog/%.md src/blog/post.html.j2 | $(blog.dirs)
	$(make.markdown) --meta src/blog/meta.json

$(dest)/index.html: src/index.html.j2 src/blog/meta.json
	./src/mark.py --index -o $@ -t $< src/blog/meta.json

push: all
	rsync -zPr public/. bvrmn.com:~/sites/bvrmn.com/
