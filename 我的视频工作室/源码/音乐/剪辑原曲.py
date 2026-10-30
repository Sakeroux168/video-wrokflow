"""第四步（换曲后）：把你提供的原曲（96.1 秒）剪成片长 122.4 秒的配乐。

原曲实测：91.5 BPM，每拍 0.6557 秒，第一拍在 0.552 秒，第一个小节头（重拍）在 1.208 秒，一小节 2.623 秒。
原曲前 18 小节（0–48.4 秒）是同一段"黑暗里紧张"的循环，前后小节几乎一样（相邻小节差异 < 0.05），
所以在这一段里**整小节重复 10 小节**来加长，听不出接缝：

  原曲 0 → 37.93 秒（第 14 小节头） + 原曲 11.70 → 96.12 秒（从第 4 小节头接着放）

第 4 小节和第 14 小节的频谱相似度 0.998（全曲最高的一对）。接缝处做 15 ms 交叉淡化。
接缝落在片中 37.93 秒，正好也是 S05 的切点，画面切换能再盖住一次。

用法：python3 剪辑原曲.py 原曲.mp3 输出.wav
"""
import subprocess, sys, wave
import numpy as np

SR = 48000
SEAM_OUT, SEAM_IN = 37.93, 11.70   # 秒（原曲时间）
FILM_DUR = 122.4
XF = 0.015


def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<i2').reshape(-1, 2).astype(np.float64) / 32768


def main(src, dst):
    x = decode(src)
    a, b, xf = int(SEAM_OUT * SR), int(SEAM_IN * SR), int(XF * SR)
    head, tail = x[:a + xf].copy(), x[b:].copy()
    ramp = np.linspace(0, 1, xf)[:, None]
    seam = head[-xf:] * (1 - ramp) + tail[:xf] * ramp
    out = np.concatenate([head[:-xf], seam, tail[xf:]])
    n = int(FILM_DUR * SR)
    out = np.concatenate([out, np.zeros((max(0, n - len(out)), 2))])[:n]
    with wave.open(dst, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype('<i2').tobytes())
    print(f'写出 {dst}：{len(out) / SR:.2f} 秒（音乐到 {(len(x) - b + a) / SR:.2f} 秒结束）')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
