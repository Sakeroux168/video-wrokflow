// 逐帧渲染：每一帧单独调用 renderAt(t) 截图，送进 ffmpeg。
// 用法：node render.mjs --ar 16x9 --from 0 --to 11.7 --out 输出.mp4 [--frames 目录（只出 PNG）] [--at 3.5,5.2（只出这几帧）]
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? [...a, [v.slice(2), arr[i + 1]]] : a), []));
const ar = args.ar || '16x9', FPS = 30;
const from = parseFloat(args.from ?? 0), to = parseFloat(args.to ?? 122.4);
const here = path.dirname(fileURLToPath(import.meta.url));
const url = pathToFileURL(path.join(here, 'index.html')).href + `?ar=${ar}`;
const [W, H] = ar === '16x9' ? [1920, 1080] : [1080, 1920];

const browser = await chromium.launch({ args: ['--allow-file-access-from-files', '--disable-web-security'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on('pageerror', e => { console.error('页面错误', e); process.exit(1); });
await page.goto(url);
await page.evaluate(() => window.ready);

if (args.cues) {                                  // 导出音效提示点
  const c = await page.evaluate(() => ({ cues: window.cues(), music: window.MUSIC_AUTOMATION, duration: window.DURATION }));
  writeFileSync(args.cues, JSON.stringify(c, null, 1));
  console.log('写出', args.cues, c.cues.length, '个提示点');
  await browser.close(); process.exit(0);
}

const grabAt = async t => {
  const data = await page.evaluate(t => { window.renderAt(t); return window.grab(); }, t);
  return Buffer.from(data.split(',')[1], 'base64');
};

if (args.at || args.frames) {                     // 只出 PNG（看板 / 单帧检查）
  const dir = args.frames || '.'; mkdirSync(dir, { recursive: true });
  const times = args.at ? args.at.split(',').map(Number) : [];
  for (const t of times) writeFileSync(path.join(dir, `${ar}_${t.toFixed(2)}.png`), await grabAt(t));
  console.log('写出', times.length, '帧到', dir);
  await browser.close(); process.exit(0);
}

const n0 = Math.round(from * FPS), n1 = Math.round(to * FPS);
const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', args.out], { stdio: ['pipe', 'inherit', 'inherit'] });
const t0 = Date.now();
for (let n = n0; n < n1; n++) {
  const buf = await grabAt(n / FPS);
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if ((n - n0) % 60 === 0) process.stdout.write(`\r${ar} 帧 ${n - n0}/${n1 - n0}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
console.log(`\n写出 ${args.out}（${n1 - n0} 帧，${((Date.now() - t0) / 1000).toFixed(0)} 秒）`);
await browser.close();
