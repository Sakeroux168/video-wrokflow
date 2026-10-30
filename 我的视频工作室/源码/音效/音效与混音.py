"""第五步：音效 + 混音。

1. 读画面导出的音效提示点（cues.json，和画面同一份时间表）
2. 每种音效用代码合成（无采样），放到对应时间点
3. 配乐按 MUSIC_AUTOMATION 静音 / 压低
4. 混在一起，整体响度做到 −14 LUFS，峰值 ≤ −1 dBFS

用法：python3 音效与混音.py cues.json 配乐.wav 输出.wav [起 秒] [止 秒]
"""
import json, subprocess, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(7)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)


def lp(x, fc):
    return sosfilt(butter(2, fc, 'low', fs=SR, output='sos'), x)


def env(n, att, tau):
    t = np.arange(n) / SR
    e = np.exp(-t / tau)
    a = max(1, int(att * SR))
    e[:a] *= np.linspace(0, 1, a)
    return e


def tone(f0, f1, dur, tau, att=0.002):
    n = int(dur * SR)
    f = np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, att, tau)


def noise(dur):
    return rng.standard_normal(int(dur * SR))


def sweep_noise(dur, f0, f1, steps=24):
    n = int(dur * SR)
    x = noise(dur)
    out = np.zeros(n)
    seg = n // steps
    for k in range(steps):
        fc = f0 * (f1 / f0) ** (k / (steps - 1))
        a, b = k * seg, n if k == steps - 1 else (k + 1) * seg
        out[a:b] = bp(x[a:b], fc * 0.6, min(fc * 1.6, SR / 2.3))
    return out


def add(*xs):
    n = max(len(x) for x in xs)
    out = np.zeros(n)
    for x in xs:
        out[:len(x)] += x
    return out


def sfx(c):
    k = c['type']
    if k == 'msg_in':
        return 0.30 * np.concatenate([tone(880, 880, 0.06, 0.03), tone(1320, 1320, 0.09, 0.04)])
    if k == 'msg_out':
        return 0.45 * add(tone(700 + 40 * c.get('i', 0), 420, 0.09, 0.035), 0.3 * tone(1800, 1800, 0.02, 0.004))
    if k == 'flood_tick':
        return 0.16 * tone(900 + 9 * c['i'], 700 + 9 * c['i'], 0.04, 0.012)
    if k == 'poof':
        n = noise(0.45)
        body = sweep_noise(0.45, 2400, 250) * env(len(n), 0.004, 0.12)
        return 0.9 * add(body / np.max(np.abs(body)), 0.6 * tone(140, 60, 0.3, 0.08))
    if k == 'drop':
        click = lambda: bp(noise(0.03), 2000, 5000) * env(int(0.03 * SR), 0.0005, 0.006)
        out = np.zeros(int(0.3 * SR))
        out[:len(click())] += click()
        i = int(0.13 * SR)
        c2 = click() * 0.6
        out[i:i + len(c2)] += c2
        out[:int(0.15 * SR)] += 0.5 * tone(220, 120, 0.15, 0.04)
        return 0.6 * out / np.max(np.abs(out))
    if k == 'descend':
        w = sweep_noise(0.55, 3000, 500) * np.sin(np.linspace(0, np.pi, int(0.55 * SR)))
        bell = add(tone(1568, 1568, 0.8, 0.3), 0.5 * tone(2349, 2349, 0.6, 0.2))
        out = np.zeros(int(0.9 * SR))
        out[:len(w)] += 0.5 * w / np.max(np.abs(w))
        i = int(0.25 * SR); m = min(len(bell), len(out) - i); out[i:i + m] += 0.25 * bell[:m]
        return 0.4 * out
    if k == 'bubble':
        b = tone(560, 300, 0.08, 0.03)
        if c.get('who') == 'alien':
            b = add(b, 0.35 * tone(1200, 1500, 0.12, 0.05))
        return 0.32 * b
    if k == 'rewind':
        d = 0.8
        n = int(d * SR)
        t = np.arange(n) / SR
        f = 300 + 900 * (t / d) ** 1.5 + 60 * np.sin(2 * np.pi * 14 * t)
        warble = np.sin(2 * np.pi * np.cumsum(f) / SR)
        hiss = bp(noise(d), 1500, 6000) * 0.4
        return 0.35 * (warble + hiss) * np.sin(np.pi * t / d) ** 0.5
    if k == 'reappear':
        out = np.zeros(int(1.0 * SR))
        for j, f in enumerate([1047, 1319, 1568, 2093]):
            s = tone(f, f, 0.6, 0.2)
            i = int(j * 0.06 * SR)
            out[i:i + len(s)] += s[:len(out) - i]
        return 0.22 * out
    if k == 'snap':
        s = bp(noise(0.05), 1800, 7000) * env(int(0.05 * SR), 0.0003, 0.008)
        return 0.9 * s / np.max(np.abs(s))
    if k == 'roll':
        w = sweep_noise(0.65, 400, 3500) * np.sin(np.linspace(0, np.pi, int(0.65 * SR)))
        return 0.4 * w / np.max(np.abs(w))
    if k == 'pill':
        return 0.28 * tone(900, 1100, 0.05, 0.02)
    raise ValueError(k)


def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<i2').reshape(-1, 2).astype(np.float64) / 32768


def lufs(x):
    p = subprocess.run(['ffmpeg', '-nostats', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                        '-af', 'ebur128', '-f', 'null', '-'], input=x.astype('<f4').tobytes(), capture_output=True)
    for line in p.stderr.decode().splitlines()[::-1]:
        if line.strip().startswith('I:'):
            return float(line.split()[1])
    raise RuntimeError('响度测量失败')


def main(cues_path, music_path, out_path, t0=0.0, t1=None):
    C = json.load(open(cues_path, encoding='utf-8'))
    dur = C['duration']
    n = int(dur * SR)
    music = decode(music_path)[:n]
    music = np.concatenate([music, np.zeros((n - len(music), 2))])
    # 配乐自动化：静音 / 压低，带短淡入淡出
    g = np.ones(n)
    for a in C['music']:
        i, j, f = int(a['from'] * SR), int(a['to'] * SR), int(a['fade'] * SR)
        g[i:j] = a['gain']
        g[i:i + f] = np.linspace(1, a['gain'], f)
        g[j:j + f] = np.linspace(a['gain'], 1, f)
    music *= g[:, None]
    fx = np.zeros(n)
    for c in C['cues']:
        s = sfx(c)
        i = int(round(c['t'] * SR))
        if i < 0:
            s, i = s[-i:], 0
        fx[i:i + len(s)] += s[:n - i]
    mix = music * 1.0 + fx[:, None] * 0.55
    a, b = int(t0 * SR), int((t1 or dur) * SR)
    mix = mix[a:b]
    gain = 10 ** ((-14 - lufs(mix)) / 20)
    mix *= gain
    # 限幅到 −1 dBFS（ffmpeg alimiter，只压峰值，不改整体响度）
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                        '-af', 'alimiter=limit=0.85:level=false:attack=2:release=60', '-f', 'f32le', '-'],
                       input=mix.astype('<f4').tobytes(), capture_output=True, check=True)
    mix = np.frombuffer(p.stdout, '<f4').reshape(-1, 2).astype(np.float64)
    with wave.open(out_path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    print(f'写出 {out_path}：{len(mix) / SR:.2f} 秒，响度 {lufs(mix):.1f} LUFS，峰值 {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS')


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], float(a[3]) if len(a) > 3 else 0.0, float(a[4]) if len(a) > 4 else None)
