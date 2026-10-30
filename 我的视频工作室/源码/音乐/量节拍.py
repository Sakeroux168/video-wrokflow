"""第四步：分析配乐，量出节拍点，并和 timeline.json 的拍点网格对一遍。

输出：
- 节拍点.json：测出来的速度、每个起音点（onset）的时间和离最近拍点的偏差
- 配乐看板.png：波形 + 小节线 + 分镜段落 + 测到的起音点

用法：python3 量节拍.py 配乐.wav ../时间轴/timeline.json 输出目录
"""
import json, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = __import__('os').path.join(__import__('os').path.dirname(__file__), '../../素材/字体/SourceHanSansCN-Medium.otf')


def load(path):
    with wave.open(path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, w.getnchannels())
    return x.mean(1) / 32768, sr


def onsets(x, sr, hop=480):
    win = 2048
    n = (len(x) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    spec = np.abs(np.fft.rfft(x[idx] * np.hanning(win), axis=1))
    flux = np.maximum(np.diff(np.log1p(spec * 10), axis=0), 0).sum(1)
    flux = np.concatenate([[0], flux])
    # 自适应阈值：局部均值 + 1.5 倍局部标准差
    k = int(0.5 * sr / hop)
    pad = np.pad(flux, k, mode='edge')
    loc = np.lib.stride_tricks.sliding_window_view(pad, 2 * k + 1)[:len(flux)]
    thr = loc.mean(1) + 1.5 * loc.std(1)
    peaks = [i for i in range(1, len(flux) - 1)
             if flux[i] > thr[i] and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1] and flux[i] > 1.0]
    # 合并 60 ms 内的重复峰
    out = []
    for i in peaks:
        t = i * hop / sr + win / 2 / sr
        if not out or t - out[-1][0] > 0.06:
            out.append((t, float(flux[i])))
    return out, flux, hop


def tempo(flux, sr, hop):
    f = flux - flux.mean()
    ac = np.correlate(f, f, 'full')[len(f) - 1:]
    fps = sr / hop
    lags = np.arange(len(ac))
    bpm = np.where(lags > 0, 60 * fps / np.maximum(lags, 1), 0)
    sel = (bpm > 70) & (bpm < 160)
    best = lags[sel][np.argmax(ac[sel])]
    return 60 * fps / best


def main(wav, tl_path, out_dir):
    x, sr = load(wav)
    tl = json.load(open(tl_path, encoding='utf-8'))
    beat = tl['beat_sec']
    ons, flux, hop = onsets(x, sr)
    bpm = tempo(flux, sr, hop)
    res = []
    for t, s in ons:
        g = round(t / (beat / 2)) * (beat / 2)          # 最近的半拍
        res.append({'t': round(t, 3), 'strength': round(s, 1),
                    'nearest_half_beat': round(g, 2), 'beat': round(g / beat, 1),
                    'offset_ms': round((t - g) * 1000, 1)})
    offs = np.array([abs(r['offset_ms']) for r in res])
    strong = [r for r in res if r['strength'] > np.percentile([q['strength'] for q in res], 50)]
    so = np.array([abs(r['offset_ms']) for r in strong])
    summary = {'measured_bpm': round(bpm, 2), 'grid_bpm': tl['bpm'], 'onsets': len(res),
               'median_abs_offset_ms': round(float(np.median(offs)), 1),
               'strong_onsets': len(strong),
               'strong_within_25ms': round(float((so <= 25).mean()) * 100, 1),
               'strong_median_abs_offset_ms': round(float(np.median(so)), 1)}
    json.dump({'summary': summary, 'onsets': res}, open(f'{out_dir}/节拍点.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(summary)

    # ---------- 看板 ----------
    W, H = 2400, 900
    img = Image.new('RGB', (W, H), '#f4ebda')
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT, 34)
    f = ImageFont.truetype(FONT, 20)
    fs = ImageFont.truetype(FONT, 15)
    L, R_, top, mid = 60, W - 40, 150, 470
    dur = tl['duration']
    X = lambda t: L + (R_ - L) * t / dur
    d.text((L, 30), f"《没事》原创配乐 · 实测 {bpm:.1f} BPM（网格 {tl['bpm']} BPM，每拍 {beat} 秒）· 强起音 "
                    f"{summary['strong_within_25ms']}% 落在拍点 ±25 ms 内", fill='#2a2a36', font=f_title)
    # 分镜段落色块
    cols = ['#f8b67d', '#e5eef9', '#fad559', '#c9e7d4', '#d9d0f0', '#f6c6c6']
    for i, sh in enumerate(tl['shots']):
        x0, x1 = X(sh['start']), X(sh['end'])
        d.rectangle([x0, 95, x1, 140], fill=cols[i % len(cols)], outline='#2a2a36')
        d.text((x0 + 4, 98), sh['id'], fill='#2a2a36', font=f)
        d.text((x0 + 4, 120), sh['title'][:7], fill='#2a2a36', font=fs)
    # 波形（RMS 包络）
    seg = int(sr * dur / (R_ - L))
    for px in range(R_ - L):
        a = x[px * seg:(px + 1) * seg]
        if len(a) == 0:
            break
        r = np.sqrt(np.mean(a ** 2))
        h = min(300, r * 900)
        d.line([L + px, mid - h, L + px, mid + h], fill='#5b86c4')
    # 小节线 + 拍点
    for b in range(0, int(dur / beat) + 1):
        t = b * beat
        if b % 4 == 0:
            d.line([X(t), top, X(t), mid + 310], fill='#2a2a36', width=1)
            if b % 8 == 0:
                d.text((X(t) + 2, mid + 312), f"{int(t // 60)}:{t % 60:04.1f}", fill='#2a2a36', font=fs)
        else:
            d.line([X(t), mid + 290, X(t), mid + 305], fill='#9d6949')
    # 起音点
    for r in res:
        c = '#3fbf5f' if abs(r['offset_ms']) <= 25 else '#e53845'
        d.ellipse([X(r['t']) - 3, top - 2, X(r['t']) + 3, top + 4], fill=c)
    d.text((L, H - 50), "上：分镜段落 · 中：配乐响度 · 竖线：小节线（每 4 拍）· 顶部圆点：测到的起音点（绿 = 在拍点 ±25 ms 内，红 = 不在）",
           fill='#2a2a36', font=f)
    img.save(f'{out_dir}/配乐看板.png')


if __name__ == '__main__':
    main(*sys.argv[1:4])
