"""第四步：原创配乐《没事》。全部用代码合成，不用任何采样或现成曲子。

- 100 BPM，4/4 拍，每拍 0.6 秒，120 秒 = 200 拍 = 50 小节
- 段落和分镜表一一对应（timeline.json 里的 bounds）
- 输出：没事_配乐.wav（48 kHz 立体声，未做响度标准化）

用法：python3 作曲.py 输出.wav
"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
BPM = 100
BEAT = 60 / BPM
DUR = 120.0
N = int(SR * DUR)
rng = np.random.default_rng(20261030)


def b2s(beat):
    return beat * BEAT


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, 'low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


class Track:
    def __init__(self, name, pan=0.0, gain=1.0, reverb=0.0):
        self.name, self.pan, self.gain, self.reverb = name, pan, gain, reverb
        self.buf = np.zeros(N)

    def add(self, t, sig, vel=1.0):
        i = int(t * SR)
        if i >= N:
            return
        j = min(N, i + len(sig))
        self.buf[i:j] += sig[:j - i] * vel


def env_ad(n, att, tau):
    t = np.arange(n) / SR
    e = np.exp(-t / tau)
    a = max(1, int(att * SR))
    e[:a] *= np.linspace(0, 1, a)
    return e


# ---------- 乐器 ----------
def mallet(f, dur=0.9, bright=1.0):
    """木琴/马林巴：主音 + 两个不和谐泛音，敲击感干脆"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * env_ad(n, 0.002, 0.32)
         + 0.25 * bright * np.sin(2 * np.pi * f * 3.93 * t) * env_ad(n, 0.001, 0.06)
         + 0.08 * bright * np.sin(2 * np.pi * f * 9.2 * t) * env_ad(n, 0.001, 0.02))
    return s


def pizz(f, dur=0.5):
    """拨弦：三角波 + 快衰减 + 低通"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = (f * t) % 1.0
    tri = 2 * np.abs(2 * ph - 1) - 1
    return lp(tri * env_ad(n, 0.003, 0.12), 2500)


def piano(f, dur=2.4, vel=1.0):
    """钢琴质感：带轻微不谐和的泛音，高泛音衰减更快"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k, amp in enumerate([1, 0.55, 0.32, 0.2, 0.12, 0.07, 0.04], start=1):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        if fk > SR / 2.2:
            break
        s += amp * np.sin(2 * np.pi * fk * t) * env_ad(n, 0.004, 1.6 / (1 + 0.6 * k) * (1 + 220 / f) ** 0.3)
    s += 0.04 * lp(rng.standard_normal(n), 3000) * env_ad(n, 0.001, 0.015)  # 琴槌
    rel = int(0.08 * SR)
    s[-rel:] *= np.linspace(1, 0, rel)
    return s * vel


def pad_chord(notes, dur, att=0.8, rel=1.2, cutoff=1800):
    """柔和铺底：每个音三根略微失谐的锯齿（加法合成），再低通"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for m in notes:
        for det in (-0.08, 0.0, 0.07):
            f = midi(m + det)
            for k in range(1, 14):
                if f * k > cutoff * 2.5:
                    break
                s += np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6.28)) / k
    s = lp(s, cutoff)
    e = np.ones(n)
    a, r = int(att * SR), int(rel * SR)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[-r:] *= np.linspace(1, 0, r) ** 2
    return s * e / (len(notes) * 6)


def bass(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    s = np.tanh(1.5 * s) * env_ad(n, 0.006, dur * 0.7)
    r = int(0.04 * SR)
    s[-r:] *= np.linspace(1, 0, r)
    return s


def kick(vel=1.0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 85 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.001, 0.12) * vel


def snap(vel=1.0):
    """响指 / 轻拍手"""
    n = int(0.18 * SR)
    s = bp(rng.standard_normal(n), 1200, 4500) * env_ad(n, 0.0005, 0.035)
    return s * vel * 0.8


def hat(vel=1.0, open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    s = hp(rng.standard_normal(n), 7000) * env_ad(n, 0.0005, 0.08 if open_ else 0.015)
    return s * vel * 0.35


def tick(f=1800):
    """木鱼嗒嗒（倒计时用）"""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * env_ad(n, 0.0005, 0.018)


def bell(f, dur=2.5):
    """钟琴 / 星星音"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) * env_ad(n, 0.001, 0.9)
         + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * env_ad(n, 0.001, 0.35)
         + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * env_ad(n, 0.001, 0.12))
    return s


def boom(dur=3.0):
    """低沉的"咚"：真正可怕的才刚开始"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 38 + 30 * np.exp(-t / 0.15)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.003, 0.9)
    s += 0.25 * lp(rng.standard_normal(n), 200) * env_ad(n, 0.01, 0.6)
    return s


def riser(dur):
    """越来越快、越来越亮的噪声上升（刷屏）"""
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    seg = n // 16
    for k in range(16):
        fc = 400 * (12 ** (k / 15))
        a, b = k * seg, (k + 1) * seg if k < 15 else n
        out[a:b] = bp(x[a:b], fc * 0.7, min(fc * 1.4, SR / 2.3))
    return out * np.linspace(0.05, 1.0, n) ** 2


def swell(dur, up=True):
    n = int(dur * SR)
    s = lp(rng.standard_normal(n), 1200)
    e = np.linspace(0, 1, n) ** 2 if up else np.linspace(1, 0, n) ** 2
    return s * e


# ---------- 和声 ----------
# 和弦：(低音 MIDI, 铺底音)
CH = {
    'C': (36, [60, 64, 67]), 'G': (43, [59, 62, 67]), 'Am': (45, [60, 64, 69]),
    'F': (41, [60, 65, 69]), 'Dm': (38, [62, 65, 69]), 'E': (40, [59, 64, 68]),
    'Em': (40, [59, 64, 67]), 'Fmaj7': (41, [60, 64, 69]), 'Gsus': (43, [60, 62, 67]),
    'Cadd9': (36, [55, 60, 62, 64, 67, 72]),
}

# 主旋律（马林巴）：拍内位置, 音高, 时值（拍）。两小节一句
MOTIF_A = [(0, 76, 0.5), (0.5, 79, 0.5), (1, 81, 1), (2, 79, 0.5), (2.5, 76, 0.5), (3, 74, 1),
           (4, 72, 0.5), (4.5, 74, 0.5), (5, 76, 1), (6, 74, 1.5)]
MOTIF_B = [(0, 76, 0.5), (0.5, 79, 0.5), (1, 81, 1), (2, 84, 0.5), (2.5, 83, 0.5), (3, 81, 1),
           (4, 79, 0.5), (4.5, 76, 0.5), (5, 74, 1), (6, 72, 1.5)]


def main(out_path):
    T = {k: Track(k, *v) for k, v in {
        'mallet': (0.2, 0.55, 0.25), 'pizz': (-0.3, 0.35, 0.2), 'piano': (0.0, 0.5, 0.35),
        'pad': (0.0, 0.32, 0.4), 'bass': (0.0, 0.55, 0.05), 'kick': (0.0, 0.8, 0.0),
        'snap': (0.15, 0.45, 0.2), 'hat': (-0.2, 0.5, 0.1), 'fx': (0.0, 0.5, 0.3),
        'bell': (0.25, 0.3, 0.5), 'tick': (0.0, 0.45, 0.1)}.items()}

    def chord_bar(name, beat, beats=4, pad=True, bass_line=True, pad_cut=1800):
        lo, notes = CH[name]
        if pad:
            T['pad'].add(b2s(beat), pad_chord(notes, b2s(beats) + 0.6, cutoff=pad_cut))
        if bass_line:
            T['bass'].add(b2s(beat), bass(midi(lo), b2s(1.8)))
            T['bass'].add(b2s(beat + 2.5), bass(midi(lo), b2s(1.3)), 0.8)

    def groove(b0, b1, kick_v=1.0, hats=True):
        for b in np.arange(b0, b1):
            if b % 2 == 0:
                T['kick'].add(b2s(b), kick(kick_v))
            else:
                T['snap'].add(b2s(b), snap())
            if hats:
                T['hat'].add(b2s(b + 0.5), hat(0.8))

    def melody(motif, b0, oct_shift=0, inst='mallet', vel=1.0):
        for pos, m, d in motif:
            f = midi(m + oct_shift)
            if inst == 'mallet':
                T['mallet'].add(b2s(b0 + pos), mallet(f), vel)
            elif inst == 'piano':
                T['piano'].add(b2s(b0 + pos), piano(f, b2s(d) + 1.2), vel)
            else:
                T['bell'].add(b2s(b0 + pos), bell(f), vel)

    # ===== S01 0–6 s（拍 0–10）：刷屏，越来越快，第 6 拍（3.6 s）硬停 =====
    T['fx'].add(0, riser(b2s(6)), 0.12)
    # 越来越密，但每个音都在网格细分上：0–2 拍八分、2–4 拍十六分、4–6 拍三十二分
    times = list(np.arange(0, 2, 0.5)) + list(np.arange(2, 4, 0.25)) + list(np.arange(4, 6, 0.125))
    scale = [72, 74, 76, 79, 81]
    for i, bt in enumerate(times):
        m = scale[i % 5] + 12 * (i // 10)
        T['mallet'].add(b2s(bt), mallet(midi(min(m, 96)), 0.4), 0.6 + 0.4 * i / len(times))
    for bt in range(0, 6):
        T['kick'].add(b2s(bt), kick(0.5 + 0.1 * bt))
    # 第 7 拍（4.2 s）外星人飘下来：一声星星音
    T['bell'].add(b2s(7), bell(midi(88), 2.4), 0.6)
    T['bell'].add(b2s(7.5), bell(midi(83), 2.0), 0.4)

    # ===== S02 6–12 s（拍 10–20）：倒带 → 好奇的拨弦 → 响指进实验 =====
    T['fx'].add(b2s(10), swell(b2s(2), up=False)[::-1] * 0.5)        # 倒带"嗖"的底
    for k, (bt, m) in enumerate([(12, 67), (12.5, 72), (13, 76), (14, 74), (14.5, 72), (15, 67),
                                 (16, 69), (16.5, 72), (17, 76)]):
        T['pizz'].add(b2s(bt), pizz(midi(m)))
    T['pad'].add(b2s(12), pad_chord(CH['Fmaj7'][1], b2s(5), att=1.0, rel=0.8, cutoff=1200))
    T['fx'].add(b2s(18), swell(b2s(2)), 0.35)                        # 进实验前的吸气

    # ===== S03+S04 12–37.8 s（拍 20–63）：轻快主题 =====
    prog = ['C', 'G', 'Am', 'F']
    for i, bar_b in enumerate(range(20, 44, 4)):                     # 拍 20–44：6 小节
        chord_bar(prog[i % 4], bar_b)
    groove(20, 44)
    melody(MOTIF_A, 20)
    melody(MOTIF_B, 28)
    melody(MOTIF_A, 36, vel=0.8)
    # 倒计时 3/2/1：拍 44 / 46 / 48，揭晓拍 50（30.0 s）
    T['pad'].add(b2s(44), pad_chord([62, 67, 71], b2s(6) + 0.3, att=2.5, rel=0.2, cutoff=2400))
    for bt in range(44, 50):
        T['tick'].add(b2s(bt), tick(2200 if bt % 2 == 0 else 1500), 1.0 if bt % 2 == 0 else 0.5)
    T['fx'].add(b2s(48), swell(b2s(2)), 0.4)
    # 揭晓：一记重拍 + 钟琴
    T['kick'].add(b2s(50), kick(1.1))
    T['hat'].add(b2s(50), hat(1.0, open_=True))
    T['bell'].add(b2s(50), bell(midi(84)), 0.6)
    for i, bar_b in enumerate(range(50, 62, 4)):                     # 拍 50–62
        chord_bar(['C', 'G', 'F'][i], bar_b)
    groove(50, 62, kick_v=0.85)
    melody(MOTIF_B, 54, vel=0.7)
    # 拍 62–64：收一下，"现在是 0"
    T['pad'].add(b2s(62), pad_chord(CH['Gsus'][1], b2s(2) + 0.4, att=0.2, rel=0.5))

    # ===== S05 37.8–52.2 s（拍 63–87）：第 100 次 → "我知道" =====
    prog5 = ['Am', 'F', 'C', 'G']
    for i, bar_b in enumerate(range(64, 72, 4)):                     # 拍 64–72 还有一点律动
        chord_bar(prog5[i], bar_b)
    for b in range(64, 72):
        if b % 2 == 0:
            T['kick'].add(b2s(b), kick(0.6))
    T['fx'].add(b2s(68), boom(1.5), 0.25)                            # "我不想说"翻面
    # 拍 74（44.4 s）"我知道"：律动全撤，只剩钢琴
    for i, bar_b in enumerate(range(72, 88, 4)):
        lo, notes = CH[['Am', 'F', 'C', 'G'][i % 4]]
        T['pad'].add(b2s(bar_b), pad_chord(notes, b2s(4) + 0.6, cutoff=1100), 0.8)
        T['bass'].add(b2s(bar_b), bass(midi(lo), b2s(3.5)), 0.6)
        for k, m in enumerate(notes):
            T['piano'].add(b2s(bar_b + k * 0.5 + 0.0), piano(midi(m), 2.2, 0.55))
    melody([(2, 76, 1), (3, 74, 1), (4, 72, 2), (6, 71, 2), (8, 72, 1), (9, 74, 1), (10, 76, 3)],
           74, inst='piano', vel=0.7)

    # ===== S06 52.2–70.2 s（拍 87–117）：真正可怕的才刚开始 =====
    T['fx'].add(b2s(87), boom(3.5), 0.9)
    for i, bar_b in enumerate(range(88, 108, 4)):
        lo, notes = CH[['Am', 'Dm', 'Am', 'E', 'Am'][i]]
        T['pad'].add(b2s(bar_b), pad_chord([n - 12 for n in notes], b2s(4) + 0.8, cutoff=700), 0.9)
        T['bass'].add(b2s(bar_b), bass(midi(lo - 12 if lo > 40 else lo), b2s(3.8)), 0.7)
        for hb in (0, 2):                                            # 心跳：咚-咚
            T['kick'].add(b2s(bar_b + hb), kick(0.45))
            T['kick'].add(b2s(bar_b + hb + 0.5), kick(0.3))
    # 拍 108（64.8 s）起：收成一个长音，到拍 117 前淡出
    T['pad'].add(b2s(108), pad_chord([57, 64], b2s(9), att=0.4, rel=4.0, cutoff=600), 0.9)

    # ===== S07 70.2–76.2 s（拍 117–127）：留白，只在拍 122 点一个音 =====
    T['piano'].add(b2s(122), piano(midi(64), 3.5, 0.35))

    # ===== S08 76.2–91.8 s（拍 127–153）：反转，暖起来 =====
    T['fx'].add(b2s(125), swell(b2s(2)), 0.25)
    prog8 = ['F', 'G', 'Em', 'Am', 'F', 'G']
    for i, bar_b in enumerate(range(128, 152, 4)):
        lo, notes = CH[prog8[i]]
        T['pad'].add(b2s(bar_b), pad_chord(notes, b2s(4) + 0.8, cutoff=1500 + 150 * i), 0.9)
        T['bass'].add(b2s(bar_b), bass(midi(lo), b2s(3.6)), 0.7)
        for k in range(8):                                           # 钢琴分解和弦
            m = notes[k % 3] + (12 if k >= 4 else 0)
            T['piano'].add(b2s(bar_b + k * 0.5), piano(midi(m), 1.8, 0.4 + 0.03 * i))
    # 拍 133（79.8 s）"我爱你"重合：钟琴
    T['bell'].add(b2s(133), bell(midi(84)), 0.7)
    T['bell'].add(b2s(133.5), bell(midi(88)), 0.5)
    # 拍 135（81.0 s）爷爷变亮：铺底上扬
    T['fx'].add(b2s(133), swell(b2s(2)), 0.2)
    melody([(0, 72, 1), (1, 74, 1), (2, 76, 2), (4, 79, 1), (5, 77, 1), (6, 76, 2),
            (8, 74, 1), (9, 76, 1), (10, 77, 2), (12, 76, 4)], 136, inst='piano', vel=0.6)

    # ===== S09 + S10 91.8–106.2 s（拍 153–177）：两种 0 → 说「有事」 =====
    prog9 = ['C', 'G', 'Am', 'F', 'Dm', 'Gsus']
    for i, bar_b in enumerate(range(152, 176, 4)):
        chord_bar(prog9[i], bar_b, pad_cut=1700)
        for k in range(8):
            m = CH[prog9[i]][1][k % 3] + 12
            T['pizz'].add(b2s(bar_b + k * 0.5), pizz(midi(m)), 0.5)
    for b in range(152, 176):
        if b % 4 == 0:
            T['kick'].add(b2s(b), kick(0.55))
    T['bell'].add(b2s(155), bell(midi(91)), 0.4)                    # 左边亮"叮～"
    T['fx'].add(b2s(158), boom(1.0), 0.3)                            # 右边关门
    T['fx'].add(b2s(174), swell(b2s(3)), 0.35)

    # ===== S11 106.2–115.2 s（拍 177–192）：回到现实，主题回来、更亮 =====
    for i, bar_b in enumerate(range(176, 192, 4)):
        chord_bar(['C', 'G', 'Am', 'F'][i], bar_b, pad_cut=2400)
    groove(178, 192, kick_v=0.9)
    melody(MOTIF_A, 178, vel=0.85)
    melody(MOTIF_B, 186, vel=0.85)
    melody(MOTIF_B, 186, oct_shift=-12, inst='bell', vel=0.25)
    T['bell'].add(b2s(188), bell(midi(91)), 0.4)                     # 来电

    # ===== S12 115.2–120 s（拍 192–200）：最后一个和弦，119.7 s 前干净收住 =====
    lo, notes = CH['Cadd9']
    T['pad'].add(b2s(192), pad_chord(notes, 4.4, att=0.05, rel=3.0, cutoff=2200), 1.0)
    T['bass'].add(b2s(192), bass(midi(lo), 4.2), 0.8)
    for k, m in enumerate([60, 64, 67, 72, 76]):
        T['piano'].add(b2s(192 + k * 0.5), piano(midi(m), 4.3 - k * 0.3, 0.55))
    T['bell'].add(b2s(192), bell(midi(84), 4.0), 0.4)
    T['kick'].add(b2s(192), kick(0.9))

    # ---------- 混音 ----------
    ir_n = int(2.2 * SR)
    ir_t = np.arange(ir_n) / SR
    irL = lp(rng.standard_normal(ir_n), 6000) * np.exp(-ir_t / 0.55)
    irR = lp(rng.standard_normal(ir_n), 6000) * np.exp(-ir_t / 0.55)
    irL /= np.sqrt(np.sum(irL ** 2))
    irR /= np.sqrt(np.sum(irR ** 2))
    L = np.zeros(N)
    R = np.zeros(N)
    send = np.zeros(N)
    for tr in T.values():
        x = tr.buf * tr.gain
        gl, gr = np.sqrt(0.5 * (1 - tr.pan)), np.sqrt(0.5 * (1 + tr.pan))
        L += x * gl
        R += x * gr
        send += x * tr.reverb
    L += fftconvolve(send, irL)[:N] * 0.9
    R += fftconvolve(send, irR)[:N] * 0.9
    out = np.stack([L, R], 1)
    # 硬停：S01 第 6 拍（3.6 s）到第 7 拍之间完全静音（只保留第 7 拍的星星音）；S07 留白
    for a, b in [(b2s(6), b2s(7) - 0.01), (b2s(117), b2s(122) - 0.01), (119.7, DUR)]:
        i, j = int(a * SR), int(b * SR)
        fade = min(int(0.03 * SR), j - i)
        out[i:i + fade] *= np.linspace(1, 0, fade)[:, None]
        out[i + fade:j] = 0
    out /= np.max(np.abs(out)) / 0.89
    import wave
    with wave.open(out_path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype('<i2').tobytes())
    print('写出', out_path)


if __name__ == '__main__':
    main(sys.argv[1])
