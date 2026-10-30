"""第四步：把分镜表里的所有时间对齐到配乐的拍点上，并导出 timeline.json。
画面、音效、音乐共用这一套时间点。

配乐 = 你提供的原曲，剪辑后 122.4 秒（见 ../音乐/剪辑原曲.py）。
网格：91.5 BPM，每拍 0.6557 秒，第 0 拍在 0.552 秒；小节头（重拍）= 第 1、5、9……拍。

做法：
1. 每个分镜段落的切点放在一个小节头上，并按音乐的情绪段落挑（见 NEW_BOUNDS 注释）
2. 段内事件按比例从旧段落搬到新段落，再对齐到最近的拍点；压在切点上的挪半拍
3. S04 倒计时手动排成每两拍一跳

用法：python3 对齐节拍.py ../../分镜表.md timeline.json
"""
import json, re, sys

BPM = 91.5
BEAT = 60 / BPM                  # 0.6557 秒
OFFSET = 0.552                   # 第 0 拍的时间
BAR0 = OFFSET + BEAT             # 第一个小节头 1.208 秒
BAR = 4 * BEAT                   # 2.623 秒
DURATION = 122.4


def bar(k):
    return round(BAR0 + k * BAR, 2)


# 上一版（100 BPM）的段落边界
OLD_BOUNDS = [0, 6.0, 12.0, 24.0, 37.8, 52.2, 70.2, 76.2, 91.8, 100.2, 106.2, 115.2, 120.0]
# 新的段落边界：全部在小节头上
NEW_BOUNDS = [0,
              bar(2),    # S02  6.45
              bar(4),    # S03 11.70
              bar(9),    # S04 24.81
              bar(14),   # S05 37.93  也是原曲的剪辑接缝
              bar(19),   # S06 51.04
              bar(26),   # S07 69.40  原曲"微光"一段
              bar(28),   # S08 74.65  原曲第 18 小节：从黑暗走向黎明
              bar(34),   # S09 90.39  原曲 65 秒附近：光越来越强
              bar(37),   # S10 98.26
              bar(40),   # S11 106.12
              bar(43),   # S12 114.00 原曲 87.8 秒：太阳升起
              DURATION]
COUNTDOWN = None   # S04 倒计时位置，运行时算

TOK = re.compile(r'(?<![\d:])(\d):(\d\d(?:\.\d+)?)(?![\d])')


def fmt(t):
    t = round(t, 2)
    m = int(t // 60)
    sec = round(t - 60 * m, 2)
    whole = int(sec)
    frac = round(sec - whole, 2)
    txt = f"{whole:02d}" + (f"{frac:.2f}"[1:].rstrip('0') if frac > 0 else '')
    return f"{m}:{txt}"


def snap(t, half=False):
    step = BEAT / 2 if half else BEAT
    k = round((t - OFFSET) / step)
    return round(OFFSET + k * step, 2)


def remap(t, i):
    o0, o1 = OLD_BOUNDS[i], OLD_BOUNDS[i + 1]
    n0, n1 = NEW_BOUNDS[i], NEW_BOUNDS[i + 1]
    return n0 + (t - o0) * (n1 - n0) / (o1 - o0)


def place(t, i):
    n0, n1 = NEW_BOUNDS[i], NEW_BOUNDS[i + 1]
    v = snap(remap(t, i))
    if v <= n0 + 0.05:
        v = snap(n0 + BEAT / 2 + 0.01, half=True)
    if v >= n1 - 0.05:
        v = snap(n1 - BEAT / 2 - 0.01, half=True)
    return v


def main(md_path, out_path):
    s = open(md_path, encoding='utf-8').read()
    a, b = s.index('## 分镜'), s.index('## 时长核对')
    parts = re.split(r'(?=### S\d\d)', s[a:b])
    out_parts, shots = [parts[0]], []
    for i, sh in enumerate(parts[1:]):
        start, end = NEW_BOUNDS[i], NEW_BOUNDS[i + 1]
        lines = sh.split('\n')
        head = re.sub(r'(\d):(\d\d(?:\.\d+)?)–(\d):(\d\d(?:\.\d+)?)', f'{fmt(start)}–{fmt(end)}', lines[0], count=1)
        head = re.sub(r'（[\d.]+ 秒）', f'（{round(end - start, 2):g} 秒）', head)
        new_lines, events = [head], []
        for ln in lines[1:]:
            if i == 3 and '倒计时 3' in ln:
                c = [snap(remap(26.4, 3))]
                c += [round(c[0] + 2 * BEAT, 2), round(c[0] + 4 * BEAT, 2)]
                lead = ln[:len(ln) - len(ln.lstrip())]
                nl = (f"{lead}- {fmt(c[0])} 倒计时 3 → 2 → 1，每两拍跳一下：3 在 {fmt(c[0])}、2 在 {fmt(c[1])}、"
                      f"1 在 {fmt(c[2])}（嘀、嘀、嘀）")
                global COUNTDOWN
                COUNTDOWN = c
            else:
                nl = TOK.sub(lambda m: m.group(0) if m.group(0) == '9:16'
                             else fmt(place(int(m.group(1)) * 60 + float(m.group(2)), i)), ln)
            new_lines.append(nl)
            m = TOK.search(nl)
            if m and m.group(0) != '9:16' and nl.lstrip().startswith('- '):
                t = int(m.group(1)) * 60 + float(m.group(2))
                events.append({'t': round(t, 2), 'beat': round((t - OFFSET) / BEAT, 2), 'text': nl.strip()[2:]})
        out_parts.append('\n'.join(new_lines))
        shots.append({'id': f'S{i + 1:02d}', 'title': head.split('·')[-1].strip(),
                      'start': start, 'end': end,
                      'start_beat': round((start - OFFSET) / BEAT, 2), 'end_beat': round((end - OFFSET) / BEAT, 2),
                      'events': events})
    rest = s[b:]

    def table_time(m):
        if m.group(0) == '9:16':
            return m.group(0)
        t = int(m.group(1)) * 60 + float(m.group(2))
        for i in range(len(OLD_BOUNDS) - 1):
            if abs(t - OLD_BOUNDS[i]) < 0.05:
                return fmt(NEW_BOUNDS[i])
        if abs(t - OLD_BOUNDS[-1]) < 0.05:
            return fmt(NEW_BOUNDS[-1])
        i = max(k for k in range(len(OLD_BOUNDS) - 1) if OLD_BOUNDS[k] <= t)
        return fmt(snap(remap(t, i)))
    rest = TOK.sub(table_time, rest)
    open(md_path, 'w', encoding='utf-8').write(s[:a] + ''.join(out_parts) + rest)
    json.dump({'bpm': BPM, 'beat_sec': round(BEAT, 5), 'beat_offset': OFFSET, 'bar_sec': round(BAR, 4),
               'first_downbeat': round(BAR0, 3), 'fps': 30, 'duration': DURATION,
               'music': {'file': '素材/音乐/没事_配乐.wav', 'source': '素材/音乐/原曲.mp3',
                         'edit': '原曲 0–37.93 秒 + 原曲 11.70–96.12 秒（重复第 4–13 小节）'},
               'bounds': NEW_BOUNDS, 'countdown': COUNTDOWN, 'shots': shots},
              open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('shots', len(shots), 'events', sum(len(x['events']) for x in shots), 'bounds', NEW_BOUNDS)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
