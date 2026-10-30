"""第四步：把分镜表里的所有时间对齐到 100 BPM 的拍点（每拍 0.6 秒），
并导出 timeline.json —— 画面、音效、音乐共用这一套时间点。

用法：python3 对齐节拍.py ../../分镜表.md timeline.json
"""
import json, re, sys

BPM = 100
BEAT = 60 / BPM          # 0.6 秒
HALF = BEAT / 2          # 0.3 秒

# 段落边界（秒）：手工选在离草稿时间最近的拍点上
BOUNDS = [0, 6.0, 12.0, 24.0, 37.8, 52.2, 70.2, 76.2, 91.8, 100.2, 106.2, 115.2, 120.0]

# S04 倒计时按"每两拍一跳"重排（3/2/1 = 26.4/27.6/28.8，揭晓 30.0）
S04_MANUAL = {24.3: 24.6, 25.0: 25.2, 26.5: 26.4, 29.5: 30.0, 30.5: 31.2,
              31.5: 32.4, 33.0: 33.6, 33.8: 34.2, 35.5: 35.4, 36.3: 36.6}

TOK = re.compile(r'(?<![\d:])(\d):(\d\d(?:\.\d)?)(?![\d])')


def fmt(t):
    m, s = divmod(round(t, 1), 60)
    s = round(s, 1)
    return f"{int(m)}:{s:04.1f}" if s != int(s) else f"{int(m)}:{int(s):02d}"


def snap(t):
    return round(int(t / BEAT + 0.5) * BEAT, 1)


def snap_in_shot(t, start, manual):
    if t in manual:
        return manual[t]
    v = snap(t)
    if v <= start and t > start:   # 段内事件不能压在切点上，挪半拍
        v = round(start + HALF, 1)
    return v


def main(md_path, out_path):
    s = open(md_path, encoding='utf-8').read()
    a, b = s.index('## 分镜'), s.index('## 时长核对')
    parts = re.split(r'(?=### S\d\d)', s[a:b])
    out_parts, shots = [parts[0]], []
    for i, sh in enumerate(parts[1:]):
        start, end = BOUNDS[i], BOUNDS[i + 1]
        manual = S04_MANUAL if i == 3 else {}
        lines = sh.split('\n')
        head = re.sub(r'(\d):(\d\d)–(\d):(\d\d)', f'{fmt(start)}–{fmt(end)}', lines[0], count=1)
        head = re.sub(r'（[\d.]+ 秒）', f'（{round(end - start, 1):g} 秒）', head)
        events, new_lines = [], [head]
        for ln in lines[1:]:
            def rep(m):
                if m.group(0) == '9:16':
                    return m.group(0)
                t = int(m.group(1)) * 60 + float(m.group(2))
                return fmt(snap_in_shot(t, start, manual))
            nl = TOK.sub(rep, ln)
            new_lines.append(nl)
            m = TOK.search(nl)
            if m and m.group(0) != '9:16' and nl.lstrip().startswith('- '):
                t = int(m.group(1)) * 60 + float(m.group(2))
                events.append({'t': t, 'beat': round(t / BEAT, 2), 'text': nl.strip()[2:]})
        out_parts.append('\n'.join(new_lines))
        shots.append({'id': f'S{i + 1:02d}', 'title': head.split('·')[-1].strip(),
                      'start': start, 'end': end,
                      'start_beat': round(start / BEAT, 2), 'end_beat': round(end / BEAT, 2),
                      'events': events})
    rest = s[b:]
    # 表格里的时间（一问一答、自查）直接对齐到最近的拍
    rest = TOK.sub(lambda m: m.group(0) if m.group(0) == '9:16'
                   else fmt(snap(int(m.group(1)) * 60 + float(m.group(2)))), rest)
    open(md_path, 'w', encoding='utf-8').write(s[:a] + ''.join(out_parts) + rest)
    json.dump({'bpm': BPM, 'beat_sec': BEAT, 'fps': 30, 'duration': 120.0,
               'bounds': BOUNDS, 'shots': shots},
              open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('shots', len(shots), 'events', sum(len(x['events']) for x in shots))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
