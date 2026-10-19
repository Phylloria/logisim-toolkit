# 样例电路

菲洛手画的，用来验元件端口坐标。只读，别整份打印。

| 文件 | 验的是什么 |
|---|---|
| and2/and3/and4/and5/and6/and7.circ | 与门 inputs=2~7 的输入脚纵向偏移（loc_x-50，间距 20 或 10，偶数跳过 0） |
| facing_south.circ | inputs=3、facing=south：输入在 loc_y-50，正中 0 那格在 |
| facing_ew_pin.circ | east 与 west 两种朝向的门，以及 Pin 的端口就是 loc |
| xor_xnor.circ | XOR 输入在 -60，XNOR 在 -70，差的就是输出圈那 10 |
| mux.circ | 多路选择器的端口（坐标还没核完） |
| mux_4to1.circ | 用门和导线直接搭出来的 4 选 1，可当连线范例 |
| splitter.circ | 分线器的属性写法（Appearance、fanout） |
| button.circ | 按钮和朝北的非门，线太杂，端口偏移还没定 |
| adder.circ | 是用门搭出来的加法器，没有 Adder 元件，不能当组件范例 |
