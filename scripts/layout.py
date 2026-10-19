#!/usr/bin/env python3
"""网表 -> .circ：按最长路径分层，一层一列。

四条硬规矩（破一条就短路，Logisim 会画红）：
  1. 门输出脚就是 loc；输入脚 loc-50（非门 loc-30）
  2. 竖线 x 全局唯一，且不落在任何门体 [loc-50-20, loc+20] 内
  3. 横线两端必须落在自己的竖线或端口上
  4. 走廊 y 用 5 结尾，避开所有 10 倍数上的竖线端点
"""
import sys

LIB = '1'
COL0, TOP = 480, 700
COR0, CSTEP = 655, 10
OUT_STEP, PIN_STEP = 50, 40


def offsets(n):
    d = 20 if n <= 3 else 10
    if n % 2:
        k = (n - 1) // 2
        return [i * d for i in range(-k, k + 1)]
    k = n // 2
    return [i * d for i in range(-k, k + 1) if i]


def in_off(kind):
    return 30 if kind == 'NOT' else 50


def out_off(kind):
    return 0


def half(kind, n):
    return 30 if kind == 'NOT' else max(abs(o) for o in offsets(n)) + 16


class Gate:
    def __init__(self, name, kind, inputs):
        self.name, self.kind, self.inputs = name, kind, list(inputs)


class Board:
    def __init__(self, inputs, gates, outputs, gap=12):
        self.inputs, self.gates, self.outputs = list(inputs), list(gates), list(outputs)
        self.gap = gap
        self.allx = set()

    # ---- 分层 ----
    def order(self):
        lv = {s: 0 for s in self.inputs}
        todo, done = list(self.gates), []
        while todo:
            moved = False
            for g in list(todo):
                if all(s in lv for s in g.inputs):
                    lv[g.name] = 1 + max(lv[s] for s in g.inputs)
                    done.append(g); todo.remove(g); moved = True
            if not moved:
                raise ValueError('成环或信号未定义: ' + ', '.join(g.name for g in todo))
        self.level, self.ordered = lv, done
        self.by_layer = {}
        for g in done:
            self.by_layer.setdefault(lv[g.name], []).append(g)
        self.n = max(self.by_layer)
        return self

    # ---- 坐标 ----
    def place(self):
        self.order()
        # 每列宽度：出口槽位 + 入口槽位，各 10 一条
        # 槽位是固定算出来的：每层右侧给出口留 out 个，左侧给入口留 in 个
        self.col_x, x = {}, COL0
        for L in range(1, self.n + 1):
            self.col_x[L] = x
            out = len(self.by_layer[L])
            ins = []
            for g in self.by_layer.get(L + 1, []):
                for s in g.inputs:
                    if s not in self.inputs and s not in ins:
                        ins.append(s)
            x += 100 + 10 * (out + len(ins))
        self.out_x = x - 40

        self.pos, self.in_y = {}, {}
        bottom = TOP
        for L in range(1, self.n + 1):
            # 每层起点错开一点：不同层的输入脚不能落在同一高度，否则横向通道会叠在一起
            y = TOP + (L - 1) * 7
            for g in self.by_layer[L]:
                h = half(g.kind, len(g.inputs))
                cy = y + h
                self.pos[g.name] = (self.col_x[L], cy)
                self.in_y[g.name] = ([cy] if g.kind == 'NOT'
                                     else [cy + o for o in offsets(len(g.inputs))])
                y = cy + h + self.gap
            bottom = max(bottom, y)

        self.pin_y, y = {}, 40
        for nm in self.inputs:
            self.pin_y[nm] = y; y += PIN_STEP
        self.out_y, y = {}, 450
        for label, _ in self.outputs:
            self.out_y[label] = y; y += OUT_STEP

        # 通道 x 按目标 y 升序排：横线往右走只会碰到目标更高的竖线，不会撞端点
        # 引脚通道从上往下 x 递减：横线只会碰到起始更靠下的竖线，不会撞到线的中间
        self.dst_y_map()
        self.pin_x = {}
        n = len(self.inputs)
        for i, s in enumerate(self.inputs):
            self.pin_x[s] = 40 + 40 * (n - 1 - i)

        self.rk, self.lk = {}, {}
        for L in range(1, self.n + 1):
            for i, g in enumerate(self.by_layer[L]):
                self.rk[g.name] = self.col_x[L] + 60 + 10 * i
            ins = []
            for g in self.by_layer.get(L + 1, []):
                for s in g.inputs:
                    if s not in self.inputs and s not in ins:
                        ins.append(s)
            ins.sort(key=lambda s: (min(self.dst_y[s]), s))
            for i, s in enumerate(ins):
                self.lk[(L + 1, s)] = max(200, self.col_x[L + 1] - 60 - 10 * i)
        self.bottom = max(bottom, y) + 80
        return self

    def blocked(self, x):
        for g in self.gates:
            cx = self.pos[g.name][0]
            if cx - in_off(g.kind) - 20 <= x <= cx + 20:
                return True
        return False

    def slot(self, xmin, xmax, limit=40):
        for k in range(limit):
            x = xmin + 10 * k
            if x > xmax:
                break
            if x not in self.allx and not self.blocked(x):
                self.allx.add(x)
                return x
        raise ValueError(f'槽位不足 {xmin}..{xmax}')

    def src(self, sig):
        if sig in self.pos:
            return self.pos[sig]           # 输出脚 = loc
        return self.pin_x[sig], self.pin_y[sig]

    # ---- 走线 ----
    def dst_y_map(self):
        m = {s: [] for s in self.inputs}
        for g in self.ordered:
            for s, py in zip(g.inputs, self.in_y[g.name]):
                m.setdefault(s, []).append(py)
        for label, sig in self.outputs:
            m.setdefault(sig, []).append(self.out_y[label])
        self.dst_y = m
        return self

    def route(self):
        self.allx = set()
        W = []
        fans = {}
        for g in self.ordered:
            ex = self.col_x[self.level[g.name]] - in_off(g.kind)
            for sig, py in zip(g.inputs, self.in_y[g.name]):
                fans.setdefault(sig, []).append((self.level[g.name], ex, py))
        for label, sig in self.outputs:
            fans.setdefault(sig, []).append((self.n + 1, self.out_x, self.out_y[label]))

        plans = []
        jobs = []
        dy_pref = []
        for sig, dsts in fans.items():
            sx, sy = self.src(sig)
            sl = self.level[sig]
            if sl == 0:
                xo = self.pin_x[sig]
            else:
                xo = self.rk[sig]
            near = []
            rest = list(dsts)
            plans.append({'sig': sig, 'sx': sx, 'sy': sy, 'xo': xo,
                          'near': near, 'jobs': []})
            for dl, dx, dy in rest:
                if sig in self.inputs:
                    xl = self.pin_x[sig]
                else:
                    xl = self.lk.get((dl, sig), self.rk[sig])
                idx = len(jobs)
                jobs.append((min(xo, xl), max(xo, xl)))
                dy_pref.append(dy - 25)
                plans[-1]['jobs'].append((idx, xl, dx, dy))

        # 走廊：贴着目标门上方走，x 区间不重叠的可共用；绝不许落在任何门的体上
        body = []
        for g in self.gates:
            cy = self.pos[g.name][1]
            h = half(g.kind, len(g.inputs))
            body.append((cy - h - 34, cy + h + 34))
        bottom_all = max(b for _, b in body)

        def on_gate(y):
            return any(a <= y <= b for a, b in body)

        tracks = []          # (y, [(lo,hi)])
        cor = {}
        def place(lo, hi, y_pref):
            k = 0
            while k < 400:
                for y in (y_pref - 5 - 10 * k, y_pref + 5 + 10 * k):
                    if y < bottom_all + 40 or on_gate(y):
                        continue
                    for tr in tracks:
                        if tr[0] == y and all(hi < a or lo > b for a, b in tr[1]):
                            tr[1].append((lo, hi)); return y
                    if all(tr[0] != y for tr in tracks):
                        tracks.append((y, [(lo, hi)])); return y
                k += 1
            raise ValueError('没地方放走线了')
        for i, (lo, hi) in enumerate(jobs):
            cor[i] = place(lo, hi, dy_pref[i])

        for p in plans:
            sx, sy, xo = p['sx'], p['sy'], p['xo']
            W.append((sx, sy, xo, sy))
            ys = [sy]
            for dl, dx, dy in p['near']:
                W.append((xo, dy, dx, dy)); ys.append(dy)
            for idx, xl, dx, dy in p['jobs']:
                cy = cor[idx]
                W.append((xo, cy, xl, cy))
                if xl != xo:
                    W.append((xl, cy, xl, dy))
                W.append((xl, dy, dx, dy))
                ys += [cy, dy]
            W.append((xo, min(ys), xo, max(ys)))
        self.W = W
        return self

    def emit(self, head):
        C = ['<circuit name="main">', '<a name="circuit" val="main"/>']
        for nm in self.inputs:
            C.append(f'<comp lib="0" loc="({self.pin_x[nm]},{self.pin_y[nm]})" name="Pin">'
                     f'<a name="tristate" val="false"/><a name="label" val="{nm}"/></comp>')
        for g in self.ordered:
            cx, cy = self.pos[g.name]
            if g.kind == 'NOT':
                C.append(f'<comp lib="{LIB}" loc="({cx},{cy})" name="NOT Gate">'
                         f'<a name="facing" val="east"/></comp>')
            else:
                C.append(f'<comp lib="{LIB}" loc="({cx},{cy})" name="{g.kind} Gate">'
                         f'<a name="inputs" val="{len(g.inputs)}"/>'
                         f'<a name="facing" val="east"/></comp>')
        for label in self.out_y:
            C.append(f'<comp lib="0" loc="({self.out_x},{self.out_y[label]})" name="Pin">'
                     f'<a name="output" val="true"/><a name="facing" val="west"/>'
                     f'<a name="label" val="{label}"/></comp>')
        body = [f'<wire from="({a},{b})" to="({c},{d})"/>' for a, b, c, d in self.W
                if not (a == c and b == d)]
        return head + '\n'.join(C + body + ['</circuit></project>'])


def encoder9():
    inputs = [f'I{k}' for k in range(1, 10)]
    gates = [Gate(f'O{k}', 'OR', [f'I{j}' for j in range(k, 10)]) for k in range(2, 9)]
    gates += [Gate(f'H{k}', 'NOT', [f'O{k}']) for k in range(2, 9)]
    gates += [
        Gate('T12', 'AND', ['I1', 'H2']), Gate('T23', 'AND', ['I2', 'H3']),
        Gate('T34', 'AND', ['I3', 'H4']), Gate('T45', 'AND', ['I4', 'H5']),
        Gate('T56', 'AND', ['I5', 'H6']), Gate('T67', 'AND', ['I6', 'H7']),
        Gate('T78', 'AND', ['I7', 'H8']),
        Gate('D2', 'OR', ['T45', 'T56', 'T67', 'T78']),
        Gate('D1', 'OR', ['T23', 'T34', 'T67', 'T78']),
        Gate('D0', 'OR', ['T12', 'T34', 'T56', 'T78', 'I9']),
        Gate('nD3', 'NOT', ['O8']), Gate('nD2', 'NOT', ['D2']),
        Gate('nD1', 'NOT', ['D1']), Gate('nD0', 'NOT', ['D0']),
    ]
    return Board(inputs, gates, [(f'nD{j}', f'nD{j}') for j in (3, 2, 1, 0)])


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out.circ'
    head = open(__file__.replace('scripts/layout.py', 'reference/and3.circ')).read()
    head = head[:head.index('<circuit name="main">')]
    b = encoder9().place().route()
    open(out, 'w').write(b.emit(head))
    print('已生成', out, '层', b.n, '门', len(b.gates), '高', b.bottom, '宽', b.out_x + 60)
