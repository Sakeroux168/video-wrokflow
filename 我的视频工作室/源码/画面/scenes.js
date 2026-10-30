// 《没事》各镜头。时间全部来自 分镜表.md / timeline.json（91.5 BPM 网格），这里写死成常量方便读。
// renderFrame(t) 只依赖 t，任意一帧都能单独渲染。

import {
  PAL, FONT, clamp, lerp, prog, easeOutCubic, easeInOutCubic, easeInCubic, popScale, settle, F, rand, rr,
  vignette, withLayer, bgNight, streetLamp, bgHome, drawAyuan, drawAlien, bubble, subtitle, pill, puff, rewindFx,
} from './engine.js';

export const BEAT = 60 / 91.5;
export const DURATION = 122.4;

// ---------- S01 刷屏：100 条消息的时间表（画面和音效共用） ----------
const ASK = [
  ['妈妈', '怎么了？', '#d47459'], ['对象', '你还好吗？', '#f17ea8'], ['朋友', '咋啦？', '#5b86c4'],
  ['同事', '没事吧？', '#d28d38'], ['老板', '状态不对啊？', '#7d6bd0'], ['室友', '吃饭没？', '#3fbf5f'],
  ['姐姐', '心情不好？', '#e99945'], ['爸爸', '最近怎么样？', '#9d6949'], ['群聊', '人呢？', '#8ea3d4'],
];
export const FLOOD_END = 3.83;   // 第 100 个「没事」= 第 1 小节第 1 拍（重拍）
export const MSGS = (() => {
  const out = [];
  const qs = [-0.3, 0.88, 1.536, 2.191], rs = [0.552, 1.208, 1.863, 2.519];
  for (let i = 0; i < 4; i++) out.push({ i, q: qs[i], r: rs[i], ask: ASK[i] });
  for (let i = 4; i < 100; i++) {
    const u = (i - 3) / 96;
    const r = 2.519 + (FLOOD_END - 2.519) * Math.sqrt(u);
    const prevR = out[i - 1].r;
    out.push({ i, q: lerp(prevR, r, 0.45), r, ask: ASK[i % ASK.length] });
  }
  out[99].r = FLOOD_END;
  return out;
})();

function floodState(tf) {
  let count = 0;
  for (const m of MSGS) if (m.r <= tf) count++;
  return count;
}

// 手机大屏：消息列表 + 计数徽章
function phonePanel(ctx, P, tf, o = {}) {
  const { x, y, w, h } = P;
  const sc = P.ui;                        // 屏幕里元素的缩放
  ctx.save();
  if (o.alpha !== undefined) ctx.globalAlpha = o.alpha;
  // 外框
  ctx.shadowColor = 'rgba(0,0,0,0.35)'; ctx.shadowBlur = 40; ctx.shadowOffsetY = 12;
  ctx.fillStyle = '#1b1d2b'; rr(ctx, x, y, w, h, 56 * sc); ctx.fill();
  ctx.shadowColor = 'transparent';
  const bz = 16 * sc, sx = x + bz, sy = y + bz, sw = w - 2 * bz, sh = h - 2 * bz;
  ctx.fillStyle = '#eef1f6'; rr(ctx, sx, sy, sw, sh, 42 * sc); ctx.fill();
  // 状态栏（通用样式，不仿任何 App）
  ctx.fillStyle = '#2a2a36'; ctx.font = `600 ${22 * sc}px ${FONT}`; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
  ctx.fillText('23:47', sx + 34 * sc, sy + 34 * sc);
  rr(ctx, sx + sw - 74 * sc, sy + 24 * sc, 40 * sc, 20 * sc, 5 * sc); ctx.stroke();
  ctx.fillRect(sx + sw - 70 * sc, sy + 28 * sc, 18 * sc, 12 * sc);
  ctx.fillStyle = '#1b1d2b'; rr(ctx, sx + sw / 2 - 60 * sc, sy + 18 * sc, 120 * sc, 30 * sc, 15 * sc); ctx.fill();
  // 列表区域
  const top = sy + 70 * sc, viewH = sh - 90 * sc;
  ctx.save();
  rr(ctx, sx, top, sw, viewH, 0); ctx.clip();
  const PAIR = 170 * sc, IN_H = 96 * sc;
  // 当前内容的底边（最后一条正在弹出时平滑地往上推）
  let bottom = 0;
  for (const m of MSGS) {
    if (m.q <= tf) bottom = Math.max(bottom, m.i * PAIR + IN_H * easeOutCubic(prog(tf, m.q, F(4))));
    if (m.r <= tf) bottom = Math.max(bottom, m.i * PAIR + PAIR * easeOutCubic(prog(tf, m.r, F(4))));
  }
  const scroll = Math.max(0, bottom - viewH + 20 * sc);
  const speed = o.blur || 0;
  if (speed > 0) ctx.filter = `blur(${speed}px)`;
  const first = Math.max(0, Math.floor(scroll / PAIR) - 1);
  for (let k = first; k < MSGS.length; k++) {
    const m = MSGS[k];
    const yy = top + m.i * PAIR - scroll + 14 * sc;
    if (yy > top + viewH) break;
    if (m.q <= tf) {
      const s = popScale(tf, m.q, 4);
      ctx.save(); ctx.translate(sx + 40 * sc, yy + 50 * sc); ctx.scale(s, s);
      ctx.fillStyle = m.ask[2]; ctx.beginPath(); ctx.arc(0, 0, 26 * sc, 0, 7); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = `700 ${22 * sc}px ${FONT}`; ctx.textAlign = 'center'; ctx.fillText(m.ask[0][0], 0, 1);
      ctx.fillStyle = '#7a7f93'; ctx.font = `500 ${18 * sc}px ${FONT}`; ctx.textAlign = 'left';
      ctx.fillText(m.ask[0], 42 * sc, -30 * sc);
      ctx.font = `600 ${28 * sc}px ${FONT}`;
      const bw = ctx.measureText(m.ask[1]).width + 40 * sc;
      ctx.fillStyle = '#fff'; rr(ctx, 40 * sc, -18 * sc, bw, 52 * sc, 20 * sc); ctx.fill();
      ctx.fillStyle = PAL.ink; ctx.fillText(m.ask[1], 60 * sc, 9 * sc);
      ctx.restore();
    }
    if (m.r <= tf) {
      const s = popScale(tf, m.r, 4);
      ctx.save(); ctx.translate(sx + sw - 36 * sc, yy + IN_H + 30 * sc); ctx.scale(s, s);
      ctx.font = `700 ${28 * sc}px ${FONT}`;
      const bw = ctx.measureText('没事。').width + 44 * sc;
      ctx.fillStyle = PAL.ayuan; rr(ctx, -bw, -26 * sc, bw, 52 * sc, 20 * sc); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle'; ctx.fillText('没事。', -22 * sc, 1);
      ctx.restore();
    }
  }
  ctx.filter = 'none';
  ctx.restore();
  ctx.restore();
  // 计数徽章（挂在手机右上角）
  const count = floodState(tf);
  if (o.badge !== false) {
    const lastR = MSGS[Math.max(0, count - 1)].r;
    const pulse = count > 0 ? 1 + 0.18 * (1 - prog(tf, lastR, F(5))) : 1;
    const txt = `「没事」× ${count}`;
    const size = 46 * P.badge;
    ctx.save();
    ctx.font = `900 ${size}px ${FONT}`;
    const bw = ctx.measureText(txt).width + size * 1.1, bh = size * 1.6;
    ctx.translate(x + w - bw * 0.35, y - bh * 0.1);
    ctx.scale(pulse, pulse); ctx.rotate(0.06);
    ctx.shadowColor = 'rgba(0,0,0,0.3)'; ctx.shadowBlur = 16;
    ctx.fillStyle = count >= 100 ? '#b3121f' : PAL.red; rr(ctx, -bw / 2, -bh / 2, bw, bh, bh / 2); ctx.fill();
    ctx.shadowColor = 'transparent';
    ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(txt, 0, 3);
    ctx.restore();
  }
  return count;
}

// ---------- 对白（气泡 + 底部字幕都从这里读） ----------
const LINES = [
  { t: 5.14, who: 'alien', txt: '第 100 个「没事」。', until: 5.8 },
  { t: 5.8, who: 'alien', txt: '他不见了。', until: 7.0 },
  { t: 7.11, who: 'alien', txt: '倒回去看看。', until: 7.7 },
  { t: 8.1, who: 'ayuan', txt: '我……刚才怎么了？', until: 9.0 },
  { t: 9.08, who: 'alien', txt: '你说了 100 次「没事」。', until: 9.7 },
  { t: 9.73, who: 'ayuan', txt: '说「没事」也会出事？', until: 10.35 },
  { t: 10.39, who: 'alien', txt: '来，做个思想实验。', until: 11.7 },
];

// ---------- 音效提示点（音效脚本读这一份，和画面同源） ----------
export function cues() {
  const c = [];
  for (const m of MSGS) {
    if (m.q >= 0 && m.i < 4) c.push({ t: m.q, type: 'msg_in' });
    c.push({ t: m.r, type: m.i < 4 ? 'msg_out' : 'flood_tick', i: m.i });
  }
  c.push({ t: FLOOD_END, type: 'poof' }, { t: 4.1, type: 'drop' }, { t: 4.49, type: 'descend' });
  for (const L of LINES) c.push({ t: L.t, type: 'bubble', who: L.who });
  c.push({ t: 7.11, type: 'rewind' }, { t: 7.77, type: 'reappear' }, { t: 11.04, type: 'snap' },
         { t: 11.04, type: 'roll' }, { t: 11.37, type: 'pill' });
  return c.sort((a, b) => a.t - b.t);
}

// 音乐静音 / 压低（混音脚本读）
export const MUSIC_AUTOMATION = [
  { from: FLOOD_END, to: 6.45, gain: 0, fade: 0.03 },
  { from: 69.4, to: 74.65, gain: 0.3, fade: 0.3 },
];

// ---------- S01 + S02 ----------
function sceneS01S02(ctx, t, L) {
  const { W, H, groundY } = L;
  // 舞台卷开（11.04 起）：先画后面的家，再把夜街两半往外推
  const roll = easeInOutCubic(prog(t, 11.04, 0.6));
  if (roll > 0) bgHome(ctx, W, H, groundY);
  const drawStreet = c => {
    bgNight(c, W, H, groundY, { t, moonX: L.moon[0], moonY: L.moon[1] });
    streetLamp(c, L.lamp[0], groundY, L.lamp[1], 1);
  };
  if (roll <= 0) drawStreet(ctx);
  else if (roll < 1) {
    for (const side of [-1, 1]) {
      ctx.save();
      const d = roll * (L.vertical ? H / 2 : W / 2) * 1.05;
      if (L.vertical) ctx.translate(0, side * d); else ctx.translate(side * d, 0);
      ctx.beginPath();                       // 先平移再裁：裁剪框跟着这半边一起走
      if (L.vertical) ctx.rect(0, side < 0 ? 0 : H / 2, W, H / 2); else ctx.rect(side < 0 ? 0 : W / 2, 0, W / 2, H);
      ctx.clip();
      drawStreet(ctx);
      ctx.fillStyle = 'rgba(0,0,0,0.25)';    // 卷开的边缘压一道暗
      if (L.vertical) ctx.fillRect(0, side < 0 ? H / 2 - 18 : H / 2, W, 18); else ctx.fillRect(side < 0 ? W / 2 - 18 : W / 2, 0, 18, H);
      ctx.restore();
    }
  }
  vignette(ctx, W, H, roll > 0.5 ? 0.25 : 0.35);

  // ---- 刷屏时间：S02 的倒带把时间倒着放 ----
  let tf = t;
  const rw = prog(t, 7.11, 0.79);                  // 7.11–7.90 倒带
  if (t >= 7.11) tf = lerp(FLOOD_END, -0.31, easeInOutCubic(rw));
  const count = floodState(Math.min(tf, FLOOD_END));
  const vanished = t >= FLOOD_END && t < 7.77;

  // ---- 手机大屏 ----
  // 7.77 起缩回阿远手里
  const shrink = easeInOutCubic(prog(t, 7.77, 0.5));
  if (shrink < 1) {
    const P0 = L.panel;
    const P = { ...P0, ui: P0.ui * (1 - shrink * 0.85), badge: P0.badge * (1 - shrink) };
    const tx = L.ayuan[0] - 10, ty = groundY - 160 * L.ayuan[2];
    P.w = lerp(P0.w, 40, shrink); P.h = lerp(P0.h, 60, shrink);
    P.x = lerp(P0.x, tx - P.w / 2, shrink); P.y = lerp(P0.y, ty - P.h / 2, shrink);
    const speed = t < FLOOD_END ? clamp((t - 2.6) / 1.2) * 6 : (t >= 7.11 && t < 7.9 ? 5 * Math.sin(Math.PI * rw) : 0);
    const dim = t >= FLOOD_END && t < 7.11 ? 0.92 : 1;
    phonePanel(ctx, P, Math.min(tf, FLOOD_END + 1), { blur: speed, alpha: dim * (1 - shrink * 0.6), badge: shrink < 0.7 });
  }

  // ---- 阿远 ----
  const [ax, , as] = L.ayuan;
  let aAlpha = 1 - 0.8 * Math.pow(clamp(tf / FLOOD_END), 1.4);   // 一边回一边变淡：100% → 20%
  if (vanished) aAlpha = 0;
  if (t >= 7.77) aAlpha = easeOutCubic(prog(t, 7.77, 0.45));
  const face = t >= 9.73 && t < 10.4 ? 'surprised' : t >= 7.77 ? 'confused' : 'neutral';
  withLayer(ctx, aAlpha, c => drawAyuan(c, ax, groundY, as, {
    phone: t < FLOOD_END || t >= 7.95, phoneGlow: true, look: t < FLOOD_END ? 1 : (t > 8.3 ? 0 : 0.4), face,
  }));
  if (t >= 7.77 && t < 9.0) {                         // 头上冒"？"
    const s = popScale(t, 7.9, 4);
    ctx.save(); ctx.translate(ax + 70 * as, groundY - 430 * as); ctx.scale(s, s);
    ctx.fillStyle = PAL.yellow; ctx.font = `900 ${70 * as}px ${FONT}`; ctx.textAlign = 'center'; ctx.fillText('？', 0, 0);
    ctx.restore();
  }
  // 重新出现时的一圈亮光
  if (t >= 7.77 && t < 8.4) {
    const u = prog(t, 7.77, 0.6);
    ctx.save(); ctx.globalAlpha = 1 - u; ctx.strokeStyle = '#fff'; ctx.lineWidth = 6 * as;
    ctx.beginPath(); ctx.ellipse(ax, groundY - 180 * as, (120 + 160 * u) * as, (200 + 160 * u) * as, 0, 0, 7); ctx.stroke();
    ctx.restore();
  }
  // "噗"
  puff(ctx, ax, groundY - 190 * as, prog(t, FLOOD_END, 0.5), as * 1.2);
  // 手机掉地上（3.83–4.25），之后躺着，外星人 4.9 捡起
  if (t >= FLOOD_END && t < 4.95) {
    const u = prog(t, FLOOD_END, 0.27);
    const y0 = groundY - 160 * as, y1 = groundY - 8 * as;
    let py = lerp(y0, y1, easeInCubic(u)), rot = u * 1.6;
    if (t > FLOOD_END + 0.27) { const b = prog(t, FLOOD_END + 0.27, 0.15); py = y1 - Math.sin(Math.PI * b) * 18 * as; rot = 1.57; }
    ctx.save(); ctx.translate(ax - 4, py); ctx.rotate(rot);
    ctx.fillStyle = '#2a2a36'; rr(ctx, -18 * as, -30 * as, 36 * as, 60 * as, 7 * as); ctx.fill();
    ctx.fillStyle = '#d8e8ff'; rr(ctx, -14 * as, -25 * as, 28 * as, 48 * as, 4 * as); ctx.fill();
    ctx.restore();
  }

  // ---- 外星人 ----
  if (t >= 4.49) {
    const land = settle(t, 4.49, 16);                     // 大东西：16 帧沉稳落下
    const [lx, ls] = [L.alienLand[0], L.alienLand[1]];
    const toSide = easeInOutCubic(prog(t, 7.11, 0.6));    // 倒带时让到一边
    const axn = lerp(lx, L.alienTalk[0], toSide);
    const ay = lerp(-200, groundY - 40 * ls, land);
    const raise = t >= 10.85 && t < 11.5 ? Math.sin(Math.PI * prog(t, 10.85, 0.65)) : (t >= 4.85 && t < 5.2 ? 0.3 : 0);
    drawAlien(ctx, axn, ay, ls, t, { holdPhone: t >= 4.95 && t < 7.11, raise, smile: t >= 10.39, glow: t >= 11.0 && t < 11.3 ? 2 : 1 });
    // 响指的小星星
    if (t >= 11.04 && t < 11.4) {
      const u = prog(t, 11.04, 0.36);
      ctx.save(); ctx.translate(axn + 120 * ls, ay - 330 * ls); ctx.rotate(u); ctx.scale(1 - u * 0.5, 1 - u * 0.5);
      ctx.globalAlpha = 1 - u; ctx.fillStyle = PAL.yellow;
      ctx.beginPath();
      for (let k = 0; k < 8; k++) { const r = k % 2 ? 10 : 34; ctx.lineTo(Math.cos(k * Math.PI / 4) * r * ls, Math.sin(k * Math.PI / 4) * r * ls); }
      ctx.fill(); ctx.restore();
    }
  }

  // ---- 对白气泡 + 字幕 ----
  const alienX = t >= 7.11 ? lerp(L.alienLand[0], L.alienTalk[0], easeInOutCubic(prog(t, 7.11, 0.6))) : L.alienLand[0];
  const ls = L.alienLand[1];
  let sub = null;
  for (const Ln of LINES) {
    if (t < Ln.t || t >= Ln.until) continue;
    sub = Ln;
    const s = popScale(t, Ln.t, 4);
    const isAlien = Ln.who === 'alien';
    const hx = isAlien ? alienX : ax, hy = isAlien ? groundY - 560 * ls : groundY - 470 * as;
    const bx = clamp(hx + (isAlien ? L.bubbleDx : -L.bubbleDx * 0.4), L.bubbleMargin, W - L.bubbleMargin);
    let by = hy - 40;
    if (L.vertical && t < 8.27) by = Math.max(by, L.panel.y + L.panel.h + L.bubbleSize * 1.6);  // 竖版：别压到手机大屏
    bubble(ctx, bx, by, Ln.txt, { kind: isAlien ? 'alien' : 'white', scale: s, size: L.bubbleSize, tail: [hx, Math.max(hy + 40, by + L.bubbleSize * 1.8)] });
  }
  if (sub) subtitle(ctx, W, L.subY, sub.txt, 1, L.subSize);

  // ---- 倒带效果 + "思想实验中" ----
  rewindFx(ctx, W, H, t >= 7.11 && t < 7.95 ? Math.sin(Math.PI * prog(t, 7.11, 0.84)) : 0, t);
  if (t >= 11.37) pill(ctx, L.pillPos[0], L.pillPos[1], '思想实验中', { scale: popScale(t, 11.37, 4), size: L.pillSize, dot: PAL.yellow });
}

// 片长内尚未做的镜头先给一个占位
function placeholder(ctx, t, L) {
  ctx.fillStyle = PAL.paper; ctx.fillRect(0, 0, L.W, L.H);
  ctx.fillStyle = PAL.ink; ctx.font = `700 60px ${FONT}`; ctx.textAlign = 'center';
  ctx.fillText(`未制作 ${t.toFixed(2)}s`, L.W / 2, L.H / 2);
}

export function renderFrame(ctx, t, L) {
  ctx.save();
  ctx.clearRect(0, 0, L.W, L.H);
  if (t < 11.7) sceneS01S02(ctx, t, L);
  else placeholder(ctx, t, L);
  ctx.restore();
}
