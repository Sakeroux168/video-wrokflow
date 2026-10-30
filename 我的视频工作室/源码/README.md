# 源码

| 目录 | 内容 |
|---|---|
| `时间轴/` | `对齐节拍.py`：把分镜表时间对齐到配乐拍点；`timeline.json`：全片时间表 |
| `音乐/` | `剪辑原曲.py`：原曲剪辑加长；`量节拍.py`：量节拍、出看板；`作曲.py`：备用合成配乐 |
| `画面/` | `engine.js` 通用绘图和角色；`scenes.js` 各镜头；`layout.js` 16:9 / 9:16 两套排版；`render.mjs` 逐帧渲染；`index.html` 浏览器里预览（`?ar=9x16&t=3.5` 看单帧） |
| `音效/` | `音效与混音.py`：合成音效 + 混音 + 响度；`cues.json`：从画面代码导出的音效时间表 |

## 常用命令

```bash
# 导出音效时间表
node 源码/画面/render.mjs --ar 16x9 --cues 源码/音效/cues.json
# 只渲染某几帧（检查用）
node 源码/画面/render.mjs --ar 9x16 --at 3.83,5.4 --frames 输出目录
# 只渲染一段
node 源码/画面/render.mjs --ar 16x9 --from 0 --to 11.7 --out 片段.mp4
# 混音（起止秒可选）
python3 源码/音效/音效与混音.py 源码/音效/cues.json 素材/音乐/没事_配乐.wav 混音.wav 0 11.7
```
