// 16:9 和 9:16 分开排版（不拿横屏硬裁）。所有坐标都是像素。
export const LAYOUTS = {
  '16x9': {
    W: 1920, H: 1080, vertical: false, groundY: 905,
    moon: [1560, 150], lamp: [330, 250],
    ayuan: [560, 0, 1.12],                 // [x, -, 缩放]
    panel: { x: 1050, y: 70, w: 700, h: 950, ui: 1.0, badge: 1.0 },
    alienLand: [560, 1.0], alienTalk: [1040],
    bubbleSize: 36, bubbleDx: 120, bubbleMargin: 260,
    subY: 1028, subSize: 34,
    pillPos: [60, 48], pillSize: 32,
  },
  '9x16': {
    W: 1080, H: 1920, vertical: true, groundY: 1560,
    moon: [880, 170], lamp: [120, 960],
    ayuan: [360, 0, 1.2],
    panel: { x: 110, y: 130, w: 860, h: 780, ui: 1.15, badge: 1.15 },
    alienLand: [300, 1.0], alienTalk: [760],
    bubbleSize: 40, bubbleDx: 300, bubbleMargin: 250,
    subY: 1690, subSize: 38,                // 底部 10% 留给小红书的按钮
    pillPos: [60, 60], pillSize: 36,
  },
};
