#!/usr/bin/env python3
import sys
import os.path
import glob
import re
import shlex
import subprocess
import errno

DEPS = {}
MAKED_DIRS = set()


def patsub(frompat, topat, items):
    frompat = frompat.replace('%', '(.+?)')
    topat = topat.replace('%', r'\1')
    return [re.sub(frompat, topat, it) for it in items]


def allfiles(root):
    result = []
    for r, _, files in os.walk(root):
        result.extend(os.path.join(r, it) for it in files)
    return result


def get_mtime(fname):
    try:
        return os.path.getmtime(fname)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        return 0


class fset(dict):
    def __init__(self, match, frompat, topat):
        self.src = glob.glob(match, recursive=True)
        self.dest = patsub(frompat, topat, self.src)
        dict.__init__(self, zip(self.dest, self.src))
        assert not (set(self.src) & set(self.dest)), 'Source and dest files have similar items'


class Dep(object):
    def __init__(self):
        self.reqs = []
        self.deps = []
        self.order = []
        self.rule = None
        self.phony = False

    def iter_reqs(self):
        for r in self.reqs:
            yield r
        for r in self.deps:
            yield r
        for r in self.order:
            yield r


class Rule(object):
    def __init__(self, cmd, params, calldepth=1):
        if type(cmd) == str:
            cmd = [cmd]
        self.cmd = cmd
        self.params = params or {}
        self.globals = sys._getframe(calldepth).f_globals

    def parse(self):
        try:
            return self._parts
        except AttributeError:
            pass
        result = self._parts = [shlex.split(it) for it in self.cmd]
        return result

    def execute(self, target, reqs):
        if callable(self.cmd):
            self.cmd(self, target, reqs)
        else:
            l = {'target': target, 'reqs': reqs,
                 'req': reqs and reqs[0]}
            l.update(self.params)
            for parts in self.parse():
                cmd = []
                for p in parts:
                    if p and p[0] == '{' and p[-1] == '}' and p != '{}':
                        cmd.extend(flatten(eval(p[1:-1], self.globals, l)))
                    else:
                        cmd.append(p)
                print('Exec', cmd)
                subprocess.check_call(cmd)


class RuleHolder(object):
    def __init__(self, tmap, params, calldepth):
        self.tmap = tmap
        self.params = params
        self.calldepth = calldepth

    def __call__(self, fn):
        rule = Rule(fn, self.params, self.calldepth)
        for t in self.tmap:
            assert not DEPS[t].rule
            DEPS[t].rule = rule
        return fn


def flatten(items):
    if type(items) not in (list, tuple):
        return [items]
    result = []
    for it in items:
        if type(it) in (list, tuple):
            result.extend(flatten(it))
        else:
            result.append(it)
    return result


def map_targets(targets):
    if type(targets) is str:
        targets = [targets]

    if type(targets) is list:
        targets = {it: [] for it in flatten(targets)}

    return {target: flatten(treqs) for target, treqs in targets.items()}


def get_dep(target):
    try:
        return DEPS[target]
    except KeyError:
        pass
    result = DEPS[target] = Dep()
    return result


def make(targets, reqs=None, cmd=None, deps=None, order=None,
         phony=None, calldepth=1, **params):
    rule = cmd and Rule(cmd, params, calldepth=calldepth+1)
    tmap = map_targets(targets)

    areqs = []
    adeps = []
    aorder = []

    if reqs and reqs is not True:
        areqs = flatten(reqs)
    if deps and deps is not True:
        adeps = flatten(deps)
    if order and order is not True:
        aorder = flatten(order)

    for t, r in tmap.items():
        d = get_dep(t)
        if phony is not None:
            d.phony = phony

        # Select list to extend for target map reqs
        if deps is True:
            d.deps.extend(r)
        elif order is True:
            d.order.extend(r)
        else:
            d.reqs.extend(r)

        areqs and d.reqs.extend(areqs)
        adeps and d.deps.extend(adeps)
        aorder and d.order.extend(aorder)

        if rule:
            if d.rule:
                raise Exception('Duplicate rule for {}'.format(t))
            d.rule = rule

    return RuleHolder(tmap, params, calldepth)


def iter_stale_leaves(nodes, seen, state):
    for node in nodes:
        if node in seen or node in state:
            return

        seen[node] = True
        dep = DEPS.get(node)
        if dep:
            possible_targets = []
            for r in dep.iter_reqs():
                if r in DEPS and r not in state:
                    possible_targets.append(r)

            # print(node, possible_targets)
            if possible_targets:
                yield from iter_stale_leaves(possible_targets, seen, state)
            else:
                yield node
        else:
            state[node] = 'src'


def process_target(target, state):
    state[target] = 'processing'

    do = False
    dep = DEPS[target]
    direct = dep.reqs + dep.deps
    sub = [it for it in direct if it in DEPS]
    files = [it for it in direct if it not in DEPS or not DEPS[it].phony]

    if dep.phony:
        do = True

    if not do:
        do = any(state[it] == 'new' for it in sub)

    if not do:
        tstamp = get_mtime(target)
        do = not tstamp or any(get_mtime(it) > tstamp for it in files)
        if not tstamp:
            dname = os.path.dirname(target)
            if dname not in MAKED_DIRS:
                os.makedirs(dname, exist_ok=True)
                MAKED_DIRS.add(dname)

    if not do:
        if not direct:  # order only deps
            state[target] = 'unknown'
        else:
            state[target] = 'uptodate'
        return

    dep.rule and dep.rule.execute(target, dep.reqs)
    state[target] = 'new'


def main():
    import sys
    import runpy
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-f', dest='rules', metavar='file',
                        default='rules.py', help='File with rules')
    parser.add_argument('target', nargs='*')

    args = parser.parse_args()

    state = {}

    sys.modules['build'] = sys.modules['__main__']
    runpy.run_path(args.rules)

    build_targets = args.target or ['all']

    while True:
        targets = list(iter_stale_leaves(build_targets, {}, state))
        if not targets:
            break
        for t in targets:
            process_target(t, state)


if __name__ == '__main__':
    main()
