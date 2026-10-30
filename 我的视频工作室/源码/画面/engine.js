// 《没事》画面引擎：通用工具、缓动、背景、角色、气泡、字幕。
// 规矩：每一帧都是时间 t 的纯函数——不存任何跨帧状态，任意一帧都能单独渲染。

export const PAL = {
  ink: '#2a2a36', red: '#e53845', yellow: '#fed64f', blue: '#2f6fd0', green: '#3fbf5f',
  skin: '#e4c2a4', hair: '#26293d', pants: '#32354b', shoe: '#26293d',
  ayuan: '#5fae8c', mom: '#d47459', blueShirt: '#5b86c4', ginger: '#d28d38',
  alien: '#b9c8e6', alienDark: '#97a9d0', alienHead: '#c9d6ef', antenna: '#fed64f',
  nightTop: '#121b3d', nightMid: '#1d2a57', nightLow: '#19274e',
  wall: '#f8b67d', wallEdge: '#9d6949', floor: '#643624', paper: '#f4ebda',
};

export const FONT = '"Source Han Sans CN", sans-serif';

// ---------- 数学 / 缓动 ----------
export const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export const lerp = (a, b, u) => a + (b - a) * u;
export const prog = (t, t0, dur) => clamp((t - t0) / dur);
export const easeOutCubic = u => 1 - Math.pow(1 - u, 3);
export const easeInCubic = u => u * u * u;
export const easeInOutCubic = u => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
export const easeOutBack = (u, s = 2.4) => 1 + (s + 1) * Math.pow(u - 1, 3) + s * Math.pow(u - 1, 2);
export const FPS = 30;
export const F = n => n / FPS; // n 帧 → 秒

// 小东西：3 帧弹出带回弹；大东西：12–18 帧缓入
export const popScale = (t, t0, frames = 4) => (t < t0 ? 0 : easeOutBack(prog(t, t0, F(frames))));
export const settle = (t, t0, frames = 15) => easeOutCubic(prog(t, t0, F(frames)));

// 可重复的伪随机（种子 → [0,1)）
export function rand(seed) {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

// ---------- 基本形状 ----------
export function rr(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export function vignette(ctx, W, H, strength = 0.32, color = '0,0,0') {
  const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.hypot(W, H) * 0.62);
  g.addColorStop(0, `rgba(${color},0)`);
  g.addColorStop(1, `rgba(${color},${strength})`);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
}

// 在离屏画布上画一组东西，再整体半透明贴回来（人变透明时身体各部分不会互相透出来）
export function withLayer(ctx, alpha, draw, extra = {}) {
  if (alpha <= 0.001) return;
  const W = ctx.canvas.width, H = ctx.canvas.height;
  const off = new OffscreenCanvas(W, H);
  const o = off.getContext('2d');
  draw(o);
  ctx.save();
  ctx.globalAlpha = alpha;
  if (extra.filter) ctx.filter = extra.filter;
  ctx.drawImage(off, 0, 0);
  ctx.restore();
}

// ---------- 背景：夜·外面 ----------
export function bgNight(ctx, W, H, groundY, opts = {}) {
  const g = ctx.createLinearGradient(0, 0, 0, groundY);
  g.addColorStop(0, PAL.nightTop);
  g.addColorStop(0.7, PAL.nightMid);
  g.addColorStop(1, '#243166');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  // 星星
  for (let i = 0; i < 70; i++) {
    const x = rand(i) * W, y = rand(i + 99) * groundY * 0.55;
    const tw = 0.5 + 0.5 * Math.sin((opts.t || 0) * 2 + i);
    ctx.fillStyle = `rgba(255,255,255,${0.15 + 0.35 * tw * rand(i + 7)})`;
    ctx.fillRect(x, y, 2, 2);
  }
  // 月亮
  const mx = opts.moonX ?? W * 0.8, my = opts.moonY ?? H * 0.15, mr = opts.moonR ?? 48;
  const mg = ctx.createRadialGradient(mx, my, mr * 0.8, mx, my, mr * 3.2);
  mg.addColorStop(0, 'rgba(232,232,240,0.25)');
  mg.addColorStop(1, 'rgba(232,232,240,0)');
  ctx.fillStyle = mg;
  ctx.beginPath(); ctx.arc(mx, my, mr * 3.2, 0, 7); ctx.fill();
  ctx.fillStyle = '#e8e8f0';
  ctx.beginPath(); ctx.arc(mx, my, mr, 0, 7); ctx.fill();
  // 两层楼
  const layers = [{ c: '#1f2b58', hMin: 0.18, hMax: 0.42, seed: 3, win: 0.35 }, { c: '#18224a', hMin: 0.1, hMax: 0.3, seed: 11, win: 0.55 }];
  for (const L of layers) {
    let x = -20, k = 0;
    while (x < W + 20) {
      const bw = 90 + rand(L.seed * 50 + k) * 150;
      const bh = groundY * (L.hMin + rand(L.seed * 70 + k) * (L.hMax - L.hMin));
      ctx.fillStyle = L.c;
      ctx.fillRect(x, groundY - bh, bw - 6, bh);
      for (let wy = groundY - bh + 18; wy < groundY - 20; wy += 34) {
        for (let wx = x + 14; wx < x + bw - 26; wx += 30) {
          const r = rand(wx * 0.37 + wy * 1.31 + L.seed);
          if (r < L.win) {
            ctx.fillStyle = r < L.win * 0.6 ? 'rgba(250,213,89,0.85)' : 'rgba(250,213,89,0.35)';
            ctx.fillRect(wx, wy, 12, 16);
          }
        }
      }
      x += bw; k++;
    }
  }
  // 人行道
  ctx.fillStyle = '#20284c';
  ctx.fillRect(0, groundY, W, H - groundY);
  ctx.fillStyle = '#2d3866';
  ctx.fillRect(0, groundY, W, 6);
  ctx.fillStyle = 'rgba(255,255,255,0.04)';
  for (let x = 0; x < W; x += 160) ctx.fillRect(x, groundY + 6, 3, H - groundY);
}

export function streetLamp(ctx, x, groundY, top, on = 1) {
  // 光锥 + 地上的光斑
  if (on > 0) {
    const cone = ctx.createLinearGradient(0, top + 30, 0, groundY);
    cone.addColorStop(0, `rgba(255,214,120,${0.32 * on})`);
    cone.addColorStop(1, `rgba(255,214,120,${0.05 * on})`);
    ctx.fillStyle = cone;
    ctx.beginPath();
    ctx.moveTo(x + 58, top + 32); ctx.lineTo(x + 108, top + 32);
    ctx.lineTo(x + 330, groundY); ctx.lineTo(x - 160, groundY); ctx.closePath();
    ctx.fill();
    const pool = ctx.createRadialGradient(x + 85, groundY + 10, 10, x + 85, groundY + 10, 300);
    pool.addColorStop(0, `rgba(255,214,120,${0.35 * on})`);
    pool.addColorStop(1, 'rgba(255,214,120,0)');
    ctx.fillStyle = pool;
    ctx.beginPath(); ctx.ellipse(x + 85, groundY + 10, 300, 50, 0, 0, 7); ctx.fill();
  }
  ctx.fillStyle = '#2a2a36';
  ctx.fillRect(x - 7, top, 14, groundY - top);
  ctx.fillRect(x - 7, top, 90, 12);
  rr(ctx, x - 22, groundY - 16, 44, 16, 4); ctx.fill();
  ctx.fillStyle = '#3a3a4a';
  ctx.beginPath(); ctx.moveTo(x + 50, top + 10); ctx.lineTo(x + 116, top + 10); ctx.lineTo(x + 104, top + 34); ctx.lineTo(x + 62, top + 34); ctx.closePath(); ctx.fill();
  ctx.fillStyle = on > 0 ? '#ffe6a6' : '#666';
  rr(ctx, x + 64, top + 32, 38, 8, 4); ctx.fill();
}

// ---------- 背景：暖·家里（空舞台） ----------
export function bgHome(ctx, W, H, floorY) {
  const g = ctx.createRadialGradient(W / 2, floorY * 0.45, 50, W / 2, floorY * 0.45, Math.max(W, H) * 0.75);
  g.addColorStop(0, '#fbc38e');
  g.addColorStop(0.55, PAL.wall);
  g.addColorStop(1, PAL.wallEdge);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, floorY);
  ctx.fillStyle = PAL.floor;
  ctx.fillRect(0, floorY, W, H - floorY);
  ctx.strokeStyle = 'rgba(0,0,0,0.18)';
  ctx.lineWidth = 2;
  for (let x = 0; x < W; x += 150) { ctx.beginPath(); ctx.moveTo(x, floorY); ctx.lineTo(x, H); ctx.stroke(); }
  ctx.fillStyle = 'rgba(0,0,0,0.12)';
  ctx.fillRect(0, floorY, W, 8);
}

// ---------- 角色 ----------
// 阿远：圆头、翘短发、圆眼镜、薄荷绿上衣。(x, y) = 脚底中心，s = 缩放
export function drawAyuan(ctx, x, y, s, o = {}) {
  const face = o.face || 'neutral';
  const look = o.look || 0;            // 头低下的程度 0–1（看手机）
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  // 影子
  ctx.fillStyle = 'rgba(0,0,0,0.22)';
  ctx.beginPath(); ctx.ellipse(0, 4, 78, 13, 0, 0, 7); ctx.fill();
  // 腿 + 鞋
  ctx.fillStyle = PAL.pants;
  rr(ctx, -40, -88, 34, 84, 12); ctx.fill();
  rr(ctx, 6, -88, 34, 84, 12); ctx.fill();
  ctx.fillStyle = PAL.shoe;
  ctx.beginPath(); ctx.ellipse(-24, -4, 26, 11, 0, 0, 7); ctx.fill();
  ctx.beginPath(); ctx.ellipse(24, -4, 26, 11, 0, 0, 7); ctx.fill();
  // 身体
  ctx.fillStyle = o.shirt || PAL.ayuan;
  rr(ctx, -56, -212, 112, 136, 34); ctx.fill();
  ctx.fillStyle = 'rgba(0,0,0,0.08)';
  rr(ctx, 14, -212, 42, 136, 30); ctx.fill();
  // 拿手机的手
  if (o.phone) {
    ctx.fillStyle = o.shirt || PAL.ayuan;
    ctx.save(); ctx.translate(30, -175); ctx.rotate(0.9); rr(ctx, -14, -6, 28, 64, 14); ctx.fill(); ctx.restore();
    ctx.fillStyle = PAL.skin;
    ctx.beginPath(); ctx.arc(-14, -136, 14, 0, 7); ctx.fill();
    ctx.save(); ctx.translate(-4, -160); ctx.rotate(-0.25);
    ctx.fillStyle = '#2a2a36'; rr(ctx, -18, -30, 36, 60, 7); ctx.fill();
    ctx.fillStyle = o.phoneGlow ? '#d8e8ff' : '#9fb6d6'; rr(ctx, -14, -25, 28, 48, 4); ctx.fill();
    ctx.restore();
  }
  // 头
  ctx.save();
  ctx.translate(look * 10, -282 + look * 8);
  ctx.rotate(look * 0.12);
  ctx.fillStyle = PAL.skin;
  ctx.beginPath(); ctx.arc(0, 0, 66, 0, 7); ctx.fill();
  // 头发：盖住上半，头顶一撮翘起来
  ctx.fillStyle = PAL.hair;
  ctx.beginPath();
  ctx.moveTo(-68, 4);
  ctx.bezierCurveTo(-74, -70, 70, -82, 68, -4);
  ctx.bezierCurveTo(50, -26, 20, -36, -4, -30);
  ctx.bezierCurveTo(-30, -26, -52, -14, -68, 4);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(-6, -62); ctx.quadraticCurveTo(4, -100, 26, -96); ctx.quadraticCurveTo(12, -84, 14, -62); ctx.fill();
  ctx.beginPath();
  ctx.moveTo(14, -64); ctx.quadraticCurveTo(34, -92, 50, -80); ctx.quadraticCurveTo(36, -72, 32, -58); ctx.fill();
  // 眼镜 + 眼睛
  const ey = 6 + look * 6;
  ctx.strokeStyle = PAL.hair; ctx.lineWidth = 5;
  ctx.beginPath(); ctx.arc(-26, ey, 19, 0, 7); ctx.stroke();
  ctx.beginPath(); ctx.arc(26, ey, 19, 0, 7); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-7, ey - 2); ctx.lineTo(7, ey - 2); ctx.stroke();
  ctx.fillStyle = PAL.hair;
  if (face === 'surprised') {
    ctx.beginPath(); ctx.arc(-26, ey, 6.5, 0, 7); ctx.arc(26, ey, 6.5, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.ellipse(0, 40, 9, 12, 0, 0, 7); ctx.fill();
  } else if (face === 'confused') {
    ctx.beginPath(); ctx.arc(-26, ey + 1, 5, 0, 7); ctx.arc(26, ey + 1, 5, 0, 7); ctx.fill();
    ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(14, ey - 30); ctx.lineTo(36, ey - 26); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-10, 40); ctx.quadraticCurveTo(0, 34, 12, 42); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(-26, ey + 3 * look, 5, 0, 7); ctx.arc(26, ey + 3 * look, 5, 0, 7); ctx.fill();
    ctx.lineWidth = 4; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(-10, 40); ctx.lineTo(10, 40); ctx.stroke();
  }
  ctx.restore();
  ctx.restore();
}

// 外星人：大圆头、两只大黑眼、发光触角、长袍、飘着。(x, y) = 袍子下摆中心
export function drawAlien(ctx, x, y, s, t, o = {}) {
  const bob = o.noBob ? 0 : Math.sin(t * 2 * Math.PI / 2.623) * 7;
  ctx.save();
  ctx.translate(x, y + bob);
  ctx.scale(s * (o.flip ? -1 : 1), s);
  // 脚下的柔光（不着地）
  ctx.fillStyle = 'rgba(185,200,230,0.18)';
  ctx.beginPath(); ctx.ellipse(0, 46 - bob, 70 - bob, 10, 0, 0, 7); ctx.fill();
  // 袍子
  ctx.fillStyle = PAL.alien;
  ctx.beginPath();
  ctx.moveTo(-50, -230);
  ctx.quadraticCurveTo(-60, -110, -88, -10);
  for (let k = 0; k < 4; k++) ctx.quadraticCurveTo(-66 + k * 44, 10 + (k % 2) * 6, -44 + k * 44, -6);
  ctx.quadraticCurveTo(60, -110, 50, -230);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = PAL.alienDark;
  ctx.beginPath(); ctx.moveTo(20, -228); ctx.quadraticCurveTo(46, -110, 84, -8); ctx.lineTo(48, -6); ctx.quadraticCurveTo(30, -110, 8, -228); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.5)'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(-30, -226); ctx.quadraticCurveTo(0, -205, 30, -226); ctx.stroke();
  // 手
  ctx.fillStyle = PAL.alien;
  const raise = o.raise || 0;     // 右手抬起（响指 / 拿手机）
  ctx.save(); ctx.translate(-48, -190); ctx.rotate(0.35); rr(ctx, -12, 0, 24, 82, 12); ctx.fill(); ctx.restore();
  ctx.save(); ctx.translate(48, -190); ctx.rotate(-0.35 - raise * 2.0); rr(ctx, -12, 0, 24, 82, 12); ctx.fill();
  if (o.holdPhone) {
    ctx.translate(0, 84); ctx.rotate(0.35 + raise * 2.0);
    ctx.fillStyle = '#2a2a36'; rr(ctx, -16, -26, 32, 52, 6); ctx.fill();
    ctx.fillStyle = '#d8e8ff'; rr(ctx, -12, -22, 24, 42, 3); ctx.fill();
  }
  ctx.restore();
  // 头
  ctx.save(); ctx.translate(0, -300);
  // 触角
  ctx.strokeStyle = PAL.alienDark; ctx.lineWidth = 6; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(6, -72); ctx.quadraticCurveTo(18, -110, 2, -132); ctx.stroke();
  const glow = o.glow ?? 1;
  ctx.save(); ctx.shadowColor = PAL.antenna; ctx.shadowBlur = 26 * glow;
  ctx.fillStyle = PAL.antenna; ctx.beginPath(); ctx.arc(2, -138, 13, 0, 7); ctx.fill(); ctx.restore();
  ctx.fillStyle = PAL.alienHead;
  ctx.beginPath(); ctx.ellipse(0, 0, 84, 78, 0, 0, 7); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.beginPath(); ctx.ellipse(-30, -38, 26, 14, -0.5, 0, 7); ctx.fill();
  // 眼睛
  for (const sx of [-1, 1]) {
    ctx.save(); ctx.translate(sx * 32, 8); ctx.rotate(sx * 0.32);
    ctx.fillStyle = '#1b1e2e'; ctx.beginPath(); ctx.ellipse(0, 0, 19, o.blink ? 3 : 30, 0, 0, 7); ctx.fill();
    if (!o.blink) { ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(-6, -12, 6, 0, 7); ctx.fill(); }
    ctx.restore();
  }
  ctx.strokeStyle = '#7d8fb8'; ctx.lineWidth = 4; ctx.lineCap = 'round';
  ctx.beginPath();
  if (o.smile) ctx.arc(0, 44, 12, 0.2, Math.PI - 0.2); else { ctx.moveTo(-8, 52); ctx.lineTo(8, 52); }
  ctx.stroke();
  ctx.restore();
  ctx.restore();
}

// ---------- 气泡 / 字幕 / 标签 ----------
export function textWidth(ctx, txt, font) { ctx.font = font; return ctx.measureText(txt).width; }

// 对白气泡。kind: 'white'（人） | 'alien'（银蓝）。tail: 尾巴指向 (tx, ty)
export function bubble(ctx, cx, cy, txt, o = {}) {
  const size = o.size || 34;
  const font = `700 ${size}px ${FONT}`;
  const padX = size * 0.7, padY = size * 0.45;
  const w = textWidth(ctx, txt, font) + padX * 2, h = size * 1.25 + padY * 2;
  const sc = o.scale ?? 1;
  if (sc <= 0) return;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(sc, sc);
  ctx.globalAlpha *= o.alpha ?? 1;
  const fill = o.kind === 'alien' ? '#dfe7fa' : '#ffffff';
  const stroke = o.kind === 'alien' ? '#8ea3d4' : 'rgba(42,42,54,0.18)';
  ctx.shadowColor = 'rgba(0,0,0,0.18)'; ctx.shadowBlur = 12; ctx.shadowOffsetY = 4;
  ctx.fillStyle = fill;
  rr(ctx, -w / 2, -h / 2, w, h, h / 2); ctx.fill();
  ctx.shadowColor = 'transparent';
  if (o.tail) {
    const [tx, ty] = [(o.tail[0] - cx) / sc, (o.tail[1] - cy) / sc];
    const bx = clamp(tx, -w / 2 + h / 2, w / 2 - h / 2);
    ctx.beginPath(); ctx.moveTo(bx - 14, h / 2 - 4); ctx.lineTo(tx, ty); ctx.lineTo(bx + 14, h / 2 - 4); ctx.closePath(); ctx.fill();
  }
  ctx.lineWidth = 2.5; ctx.strokeStyle = stroke;
  rr(ctx, -w / 2, -h / 2, w, h, h / 2); ctx.stroke();
  if (o.kind === 'alien') {
    ctx.fillStyle = '#8ea3d4'; ctx.font = `700 ${size * 0.5}px ${FONT}`;
    ctx.textAlign = 'left'; ctx.textBaseline = 'top';
  }
  ctx.fillStyle = PAL.ink; ctx.font = font; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  drawRich(ctx, txt, 0, 2, size);
  ctx.restore();
}

// 支持「」里的词标红：传入 '你说的是「没事」' → 「没事」标红
export function drawRich(ctx, txt, x, y, size, color = PAL.ink, hl = PAL.red) {
  const parts = txt.split(/(「[^」]*」)/);
  const total = parts.reduce((a, p) => a + ctx.measureText(p).width, 0);
  let cx = x - total / 2;
  ctx.textAlign = 'left';
  for (const p of parts) {
    ctx.fillStyle = p.startsWith('「') ? hl : color;
    ctx.fillText(p, cx, y);
    cx += ctx.measureText(p).width;
  }
  ctx.textAlign = 'center';
}

// 底部字幕条（静音也看得懂）
export function subtitle(ctx, W, y, txt, alpha = 1, size = 34) {
  if (!txt || alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha = alpha;
  const font = `500 ${size}px ${FONT}`;
  const w = textWidth(ctx, txt, font) + size * 1.4;
  ctx.fillStyle = 'rgba(10,12,24,0.55)';
  rr(ctx, W / 2 - w / 2, y - size * 0.95, w, size * 1.9, size * 0.95); ctx.fill();
  ctx.fillStyle = '#fff'; ctx.font = font; ctx.textBaseline = 'middle';
  drawRich(ctx, txt, W / 2, y + 1, size, '#fff', PAL.yellow);
  ctx.restore();
}

// 胶囊标签（如"思想实验中"）
export function pill(ctx, x, y, txt, o = {}) {
  const size = o.size || 30;
  const font = `700 ${size}px ${FONT}`;
  const w = textWidth(ctx, txt, font) + size * 1.6, h = size * 1.7;
  const sc = o.scale ?? 1;
  if (sc <= 0) return;
  ctx.save(); ctx.translate(x + w / 2, y + h / 2); ctx.scale(sc, sc);
  ctx.fillStyle = o.bg || '#282b3f';
  rr(ctx, -w / 2, -h / 2, w, h, h / 2); ctx.fill();
  if (o.dot) { ctx.fillStyle = o.dot; ctx.beginPath(); ctx.arc(-w / 2 + size * 0.75, 0, size * 0.22, 0, 7); ctx.fill(); }
  ctx.fillStyle = o.color || '#fff'; ctx.font = font; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(txt, o.dot ? size * 0.25 : 0, 2);
  ctx.restore();
}

// 一团"噗"的烟（人消失）
export function puff(ctx, x, y, u, s = 1) {
  if (u <= 0 || u >= 1) return;
  for (let i = 0; i < 16; i++) {
    const a = rand(i) * Math.PI * 2, d = (40 + rand(i + 3) * 120) * easeOutCubic(u) * s;
    const r = (18 + rand(i + 5) * 26) * (1 - u * 0.6) * s;
    ctx.fillStyle = `rgba(230,236,250,${0.85 * (1 - u)})`;
    ctx.beginPath(); ctx.arc(x + Math.cos(a) * d, y + Math.sin(a) * d * 0.8, r, 0, 7); ctx.fill();
  }
}

// 倒带效果：扫描线 + 色偏 + ◀◀
export function rewindFx(ctx, W, H, k, t) {
  if (k <= 0) return;
  ctx.save();
  ctx.globalAlpha = 0.18 * k;
  ctx.fillStyle = '#000';
  for (let y = (t * 900) % 6; y < H; y += 6) ctx.fillRect(0, y, W, 2);
  ctx.globalAlpha = 0.5 * k;
  const by = ((t * 1.7) % 1) * H;
  ctx.fillStyle = 'rgba(255,255,255,0.25)'; ctx.fillRect(0, by, W, 26);
  ctx.globalAlpha = k;
  ctx.fillStyle = '#fff'; ctx.font = `900 ${Math.round(H * 0.06)}px ${FONT}`; ctx.textBaseline = 'top';
  ctx.fillText('◀◀', W * 0.04, H * 0.04);
  ctx.restore();
}
