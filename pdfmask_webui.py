# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 项目创作时为初中生
#
# This file is part of PDF 隐私打码工具 (PDF Privacy Masker) and is distributed
# under the GNU Affero General Public License v3.0 or later. See LICENSE.

"""首页 UI：一整页 HTML（含 CSS 与前端 JS），与后端逻辑分开维护。

这个字符串里出现的 __TOKEN__ / __VERSION__ / __URL__ / __URLGITEE__ /
__CREDIT__ / __URLSHORT__ / __URLSHORT_GITEE__ / __THANKS__ 占位符
由 pdfmask.Handler 在返回页面时替换。
"""

HTML_UI = r"""<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDF 隐私打码工具</title>
<style>
:root{
  --bg:#f4f5f7; --panel:#fff; --ink:#15181d; --ink2:#5b6472; --ink3:#8b94a3;
  --line:#e4e7ec; --line2:#eef0f3; --accent:#2f6bff; --accent-d:#1f4fd8;
  --danger:#e5484d; --ok:#12a150; --radius:14px;
}
*{box-sizing:border-box}
[hidden]{display:none !important}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;overflow:hidden}
button{font-family:inherit}
.app{height:100%;display:flex;flex-direction:column}
header{height:66px;flex:0 0 66px;display:flex;align-items:center;justify-content:space-between;
  padding:0 22px;background:#fff;border-bottom:1px solid var(--line);position:relative;z-index:5}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#2f6bff,#6a4cff);
  display:grid;place-items:center;color:#fff;box-shadow:0 4px 12px rgba(47,107,255,.28)}
.brand h1{font-size:15.5px;margin:0;line-height:1.3;letter-spacing:.2px}
.brand p{margin:2px 0 0;font-size:11.5px;color:var(--ink3);line-height:1.2}
.top-right{display:flex;align-items:center;gap:12px}
.quit{font-size:12px;color:var(--ink3);cursor:pointer;padding:5px 9px;border-radius:8px;border:1px solid transparent}
.quit:hover{background:#f5f6f8;color:var(--danger);border-color:var(--line)}
.about-link{font-size:12px;color:var(--ink3);cursor:pointer;padding:5px 9px;border-radius:8px;border:1px solid transparent}
.about-link:hover{background:#f5f6f8;color:var(--ink);border-color:var(--line)}
/* ---------- 关于 ---------- */
.about-mask{position:fixed;inset:0;background:rgba(20,24,32,.42);backdrop-filter:blur(2px);
  display:grid;place-items:center;z-index:400;padding:24px}
.about-box{width:min(520px,100%);max-height:88vh;overflow:auto;background:#fff;border-radius:16px;
  padding:26px 28px 22px;box-shadow:0 30px 70px -30px rgba(15,24,40,.5)}
.about-box h3{margin:0 0 3px;font-size:17px;letter-spacing:.2px}
.about-box .ver{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--ink3)}
.about-box dl{margin:16px 0 0;display:grid;grid-template-columns:88px 1fr;gap:9px 12px;font-size:12.5px}
.about-box dt{color:var(--ink3)}
.about-box dd{margin:0;color:var(--ink);word-break:break-word}
.about-note{margin:16px 0 0;padding:12px 14px;background:#f7f9fc;border-left:2px solid var(--accent);
  font-size:12px;line-height:1.75;color:var(--ink2);border-radius:0 8px 8px 0}
.about-note b{color:var(--ink)}
.about-box dd.url{cursor:pointer;color:var(--accent);border-bottom:1px dashed rgba(47,107,255,.4);
  display:inline-block;max-width:100%}
.about-box dd.url:hover{color:#1a4fd6}
.about-thanks{margin:14px 0 0;padding:14px;border:1px solid var(--line);border-radius:12px}
.about-thanks b{display:block;font-size:12.5px;color:var(--ink);margin-bottom:6px}
.about-thanks p{margin:0 0 10px;font-size:11.5px;line-height:1.65;color:var(--ink3)}
.about-thanks img{display:block;width:236px;max-width:100%;height:auto;margin:0 auto;border-radius:8px}
.about-star{display:flex;align-items:center;gap:10px;margin:10px 0 14px;padding:10px 12px;
  background:#f7f9fc;border:1px solid var(--line2);border-radius:10px}
.about-star-txt{flex:1;font-size:11.5px;color:var(--ink3);line-height:1.6}
.about-star-txt b{display:block;color:var(--ink);font-size:12.5px;margin-bottom:2px}
.about-star .btn{flex:none;padding:6px 14px;font-size:12px}
.thanks-cap{margin-top:8px;font-size:10.5px;color:var(--ink3);text-align:center}
.thanks-save-row{display:flex;justify-content:center;margin-top:9px}
.thanks-save-row .btn{padding:5px 16px;font-size:11.5px}
.about-rule{margin:14px 0 0;padding:12px 14px 10px;background:#fff8f0;border:1px solid #f3dfc4;
  border-radius:10px;font-size:12px;line-height:1.7;color:#7a5320}
.about-rule b{color:#8a4f00;font-size:12.5px}
.about-rule ol{margin:7px 0 0;padding-left:18px}
.about-rule li{margin:3px 0}
.about-rule em{font-style:normal;color:#8a4f00;font-weight:600;word-break:break-all}
.about-rule .rule-foot{margin:8px 0 0;color:#96703c;font-size:11.5px}
.about-rule code{font-family:ui-monospace,Consolas,monospace;font-size:11px;
  background:#fdf3e5;padding:1px 4px;border-radius:4px}
.about-actions{margin-top:18px;display:flex;justify-content:flex-end;gap:8px}
.badge-local{display:flex;align-items:center;gap:7px;font-size:12px;color:#0f7b45;
  background:#e9f8f0;border:1px solid #c9eddb;padding:6px 12px;border-radius:99px}
.dot{width:6px;height:6px;border-radius:50%;background:#12a150;box-shadow:0 0 0 3px rgba(18,161,80,.15)}

main{flex:1;min-height:0;display:flex;overflow:hidden}
/* ---------- 上传态 ---------- */
.drop-view{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:30px}
.drop-card{width:min(620px,92%);background:#fff;border:2px dashed #d6dbe4;border-radius:22px;
  padding:48px 32px;text-align:center;transition:.18s;cursor:pointer}
.drop-card:hover,.drop-card.over{border-color:var(--accent);background:#f7faff;
  box-shadow:0 18px 40px -22px rgba(47,107,255,.45)}
.drop-card h2{font-size:19px;margin:16px 0 6px}
.drop-card p{color:var(--ink2);margin:0 0 20px;font-size:13px}
.ico{width:64px;height:64px;margin:0 auto;border-radius:18px;background:#eef3ff;display:grid;place-items:center}
.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 16px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:13px;cursor:pointer;transition:.15s;white-space:nowrap}
.btn:hover{background:#f7f8fa;border-color:#d3d8e0}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;box-shadow:0 6px 16px -6px rgba(47,107,255,.6)}
.btn.primary:hover{background:var(--accent-d)}
.btn.ghost{background:transparent}
.btn:disabled{opacity:.5;cursor:not-allowed}
.tips{display:flex;gap:26px;color:var(--ink3);font-size:12px;flex-wrap:wrap;justify-content:center}
.tips span{display:flex;align-items:center;gap:6px}
.credit{font-size:11.5px;color:#a2aab8;text-align:center;line-height:1.7;max-width:620px}
.credit span{display:block}
.credit .credit-url{color:#8b93a3;font-size:11px;margin-top:2px;cursor:pointer;
  word-break:break-all;transition:color .15s}
.credit .credit-url:hover{color:#2f6bff}
/* ---------- 工作态 ---------- */
.work-view{flex:1;min-height:0;display:flex}
.side{width:352px;flex:0 0 352px;background:#fff;border-right:1px solid var(--line);
  display:flex;flex-direction:column;min-height:0}
.file-card{padding:14px 16px;border-bottom:1px solid var(--line2);display:flex;gap:11px;align-items:flex-start}
.file-ico{width:36px;height:36px;border-radius:9px;background:#fff1f1;color:var(--danger);
  display:grid;place-items:center;font-size:10px;font-weight:700;flex:0 0 36px}
.file-meta{min-width:0;flex:1}
.file-name{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file-sub{font-size:11.5px;color:var(--ink3);margin-top:2px}
.stats{padding:12px 16px;display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid var(--line2)}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;padding:3px 9px;border-radius:99px;
  background:#f4f6f9;color:#3d4655;border:1px solid var(--line)}
.chip b{font-weight:700}
.chip i{width:6px;height:6px;border-radius:50%;display:inline-block}
.list-head{display:flex;align-items:center;justify-content:space-between;padding:10px 16px 8px;
  font-size:12px;color:var(--ink2)}
.link{color:var(--accent);cursor:pointer;font-size:12px;background:none;border:0;padding:2px 4px}
.link:hover{text-decoration:underline}
.list{flex:1;overflow:auto;padding:0 8px 14px}
.grp{font-size:11px;color:var(--ink3);padding:10px 8px 4px;letter-spacing:.3px}
.row{display:flex;align-items:center;gap:9px;padding:8px 9px;border-radius:9px;cursor:pointer;
  border:1px solid transparent}
.row:hover{background:#f7f9fc}
.row.on{background:#f2f6ff;border-color:#dbe6ff}
.row input{accent-color:var(--accent);width:15px;height:15px;margin:0;cursor:pointer;flex:0 0 15px}
.badge{font-size:11px;padding:2px 7px;border-radius:6px;background:#f1f3f7;color:#4a5361;
  flex:0 0 auto;font-weight:500}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#3d4655;
  flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sus{flex:0 0 auto;font-size:10px;padding:1px 6px;border-radius:5px;color:#a15c00;
  background:#fff3d6;border:1px solid #ffe0a3}
.pg{font-size:10.5px;color:var(--ink3);flex:0 0 auto}
.empty{padding:40px 18px;text-align:center;color:var(--ink3);font-size:12.5px}
/* viewer */
.viewer{flex:1;min-width:0;display:flex;flex-direction:column;background:#eceef2}
.toolbar{height:48px;flex:0 0 48px;background:#fff;border-bottom:1px solid var(--line);
  display:flex;align-items:center;gap:8px;padding:0 16px}
.tb-group{display:flex;align-items:center;gap:4px;background:#f4f6f9;border:1px solid var(--line);
  border-radius:9px;padding:2px}
.tb-btn{border:0;background:transparent;color:#3d4655;padding:5px 9px;border-radius:7px;cursor:pointer;font-size:12.5px}
.tb-btn:hover{background:#fff;color:var(--ink)}
.tb-btn:disabled{opacity:.35;cursor:default;background:transparent}
.tb-btn.active{background:#fff;color:var(--accent);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.pgnum{font-size:12.5px;color:var(--ink2);min-width:64px;text-align:center}
.spacer{flex:1}
.switch{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--ink2);cursor:pointer;
  user-select:none}
.switch input{display:none}
.track{width:34px;height:19px;border-radius:99px;background:#d5d9e0;position:relative;transition:.18s}
.track::after{content:"";position:absolute;top:2px;left:2px;width:15px;height:15px;border-radius:50%;
  background:#fff;transition:.18s;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.switch input:checked + .track{background:var(--accent)}
.switch input:checked + .track::after{transform:translateX(15px)}
.canvas-wrap{flex:1;overflow:auto;padding:22px;display:flex;justify-content:center;align-items:flex-start;
  position:relative}
.canvas-wrap.draw{cursor:crosshair}
/* 顶部功能提示：能拖框、能双击取消 */
.hint-chip{display:flex;align-items:center;gap:5px;font-size:11.5px;color:#5b6675;
  background:#f4f6f9;border:1px solid var(--line);border-radius:8px;padding:4px 10px;
  white-space:nowrap;user-select:none}
.hint-chip svg{flex:0 0 12px;opacity:.75}
@media (max-width: 1040px){ .hint-chip{display:none} }
.canvas-wrap img{display:block;background:#fff;box-shadow:0 8px 30px -12px rgba(15,24,40,.28);
  border-radius:2px;user-select:none;-webkit-user-drag:none}
.band{position:fixed;border:1.5px dashed #ff2d55;background:rgba(255,45,85,.12);pointer-events:none;z-index:99}
.band.erase{border-color:#2f6bff;background:rgba(47,107,255,.15)}
/* 手动框选 / 橡皮擦共用：指针旁边的放大镜，便于只擦掉前缀和冒号 */
.loupe{position:fixed;width:120px;height:120px;border-radius:50%;border:2px solid #fff;
  box-shadow:0 4px 18px rgba(0,0,0,.35),0 0 0 1px rgba(0,0,0,.15);
  background-repeat:no-repeat;background-color:#fff;pointer-events:none;z-index:120;
  overflow:hidden}
/* 镜里的虚线框：和手指上那条是同一条线放大后的样子。
   手动=红、橡皮擦=蓝，与 .band 的配色一一对应，看一眼就知道现在是什么模式。 */
.loupe .lbox{position:absolute;left:0;top:0;width:0;height:0;display:none;
  border:1.5px dashed #ff2d55;background:rgba(255,45,85,.12);pointer-events:none}
.loupe .lbox.erase{border-color:#2f6bff;background:rgba(47,107,255,.15)}
/* action bar */
.actionbar{flex:0 0 66px;height:66px;background:#fff;border-top:1px solid var(--line);
  display:flex;align-items:center;gap:14px;padding:0 22px}
.sum{font-size:13px;color:var(--ink2)}
.sum b{color:var(--ink);font-size:15px}
/* overlay / toast / result */
.overlay{position:fixed;inset:0;background:rgba(244,245,247,.62);backdrop-filter:blur(3px);
  display:flex;align-items:flex-end;justify-content:center;z-index:200;padding:22px}
/* ---- 处理中的进度面板（窗口正中）----
   以前这里只有一个转圈加一行字：看不出进度、也停不下来。
   现在是「当前页 + 整个文件」两条进度，配暂停 / 停止 / 继续。
   overlay 本身是靠底对齐的，面板单独用 align-self:center 抬到正中，
   其它用同一个 overlay 的弹层不受影响。 */
.jobp{width:min(560px,100%);background:#fff;border-radius:20px;padding:18px 20px 16px;
  box-shadow:0 26px 70px -28px rgba(15,24,40,.5);
  align-self:center}
.jobhead{display:flex;align-items:center;gap:12px}
.jobtitle{flex:1;font-size:15px;font-weight:600;color:var(--ink);line-height:1.35}
.jobpct{font-size:22px;font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums}
.jobpage{font-size:12px;color:var(--ink2);margin-top:4px}
.barrow{display:grid;grid-template-columns:60px 1fr 44px;gap:10px;align-items:center;margin-top:10px}
.barrow > span{font-size:11.5px;color:var(--ink2)}
.bar{height:8px;border-radius:99px;background:#e8ecf3;overflow:hidden}
.barrow.strong .bar{height:12px}
.bar > i{display:block;height:100%;width:0;border-radius:99px;
  background:linear-gradient(90deg,rgba(79,124,247,.5),rgba(79,124,247,.85));
  transition:width .28s ease}
.barrow.strong .bar > i{background:linear-gradient(90deg,#4f7cf7,#7c5cf0)}
.barrow > b{font-size:11.5px;color:var(--ink2);text-align:right;font-variant-numeric:tabular-nums}
.barrow.strong > b{color:var(--accent);font-weight:600}
.jobp.paused .bar > i{filter:grayscale(.45);opacity:.55}
.jobbtns{display:flex;justify-content:center;gap:12px;margin-top:16px}
.jbtn{border:0;border-radius:99px;padding:10px 26px;font-size:13.5px;font-weight:600;cursor:pointer;
  background:#eef2ff;color:var(--accent);font-family:inherit;transition:filter .15s}
.jbtn:hover{filter:brightness(.97)}
.jbtn.primary{background:var(--accent);color:#fff}
.jbtn.stop{background:#fdecea;color:#b42318}
.spin{width:32px;height:32px;border:3px solid #e3e8f0;border-top-color:var(--accent);border-radius:50%;
  margin:0 auto 14px;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.ov-text{font-size:13.5px;color:var(--ink2)}
.toast{position:fixed;left:50%;bottom:84px;transform:translate(-50%,14px);background:#15181d;color:#fff;
  padding:10px 18px;border-radius:10px;font-size:13px;opacity:0;transition:.22s;z-index:300;pointer-events:none;
  max-width:80vw}
.toast.show{opacity:1;transform:translate(-50%,0)}
.toast.err{background:#b42318}
.result{position:fixed;inset:0;background:rgba(15,24,40,.42);display:grid;place-items:center;z-index:250}
.result .card{background:#fff;border-radius:18px;padding:30px 34px;width:min(520px,92%);
  box-shadow:0 30px 70px -30px rgba(0,0,0,.5);text-align:center}
.result h3{margin:14px 0 6px;font-size:18px}
.result .path{font-size:12px;color:var(--ink2);background:#f4f6f9;border:1px solid var(--line);
  border-radius:9px;padding:10px;word-break:break-all;margin:12px 0 18px;text-align:left;
  font-family:ui-monospace,Consolas,monospace}
.ok-ico{width:56px;height:56px;border-radius:50%;background:#e7f8ef;color:var(--ok);
  display:grid;place-items:center;margin:0 auto}
.res-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.warn{background:#fff8e8;border:1px solid #f6e2b3;color:#8a5a00;font-size:12px;padding:8px 12px;
  border-radius:9px;margin:10px 16px 0;line-height:1.5}
/* ---------- 能力徽章（顶部小字） ---------- */
.nocap{display:inline-block;margin-left:9px;font-size:10.5px;font-weight:700;line-height:1.5;
  color:#0f7a3d;background:#e9f8ef;border:1px solid #bce7cd;border-radius:5px;padding:0 6px;
  vertical-align:1.5px;letter-spacing:.3px;white-space:nowrap;cursor:default}
.brand .hint-draw{color:#b4423f}
/* ---------- 通用弹窗 ---------- */
.modal-mask{position:fixed;inset:0;background:rgba(20,24,32,.42);backdrop-filter:blur(2px);
  display:grid;place-items:center;z-index:420;padding:24px}
.modal{width:min(520px,100%);max-height:88vh;overflow:auto;background:#fff;border-radius:16px;
  padding:22px 24px 18px;box-shadow:0 30px 70px -30px rgba(15,24,40,.5)}
.modal h3{margin:0 0 4px;font-size:16.5px;letter-spacing:.2px}
.modal .sub{color:var(--ink3);font-size:12px;margin:0 0 16px;line-height:1.6}
.field-label{display:block;font-size:12px;color:var(--ink2);margin-bottom:7px}
.path-row{display:flex;gap:8px}
.path-input{flex:1;min-width:0;border:1px solid var(--line);border-radius:10px;padding:9px 11px;
  font:12.5px/1.4 ui-monospace,Consolas,monospace;color:var(--ink);background:#fbfcfd}
.path-input:focus{outline:none;border-color:var(--accent);background:#fff;
  box-shadow:0 0 0 3px rgba(47,107,255,.12)}
.path-input::placeholder{color:#aab2be}
.chk{display:flex;align-items:flex-start;gap:9px;font-size:12.5px;color:var(--ink2);
  margin-top:13px;cursor:pointer;line-height:1.55;user-select:none}
.chk input{appearance:none;-webkit-appearance:none;width:16px;height:16px;flex:0 0 16px;
  margin:1px 0 0;border:1.5px solid #c9d0da;border-radius:5px;cursor:pointer;position:relative;
  background:#fff;transition:.15s}
.chk:hover input{border-color:#a9b4c4}
.chk input:checked{background:var(--accent);border-color:var(--accent)}
.chk input:checked::after{content:"";position:absolute;left:4.6px;top:1.6px;width:4px;height:8px;
  border:solid #fff;border-width:0 2px 2px 0;transform:rotate(42deg)}
.chk b{color:var(--ink);font-weight:600}
.modal-actions{margin-top:20px;display:flex;justify-content:flex-end;gap:9px}
.modal-note{margin-top:15px;padding:9px 12px;background:#f7f9fc;border-radius:9px;
  font-size:11.5px;color:var(--ink3);line-height:1.7}
.modal-note em{font-style:normal;color:var(--ink2)}
/* ---------- 设置：语言 / 检查更新 ---------- */
.set-sec{margin-top:16px;padding-top:14px;border-top:1px solid var(--line2)}
.seg{display:flex;gap:3px;background:#f1f3f7;border-radius:10px;padding:3px}
.seg-btn{flex:1;border:0;background:transparent;padding:8px 0;border-radius:8px;
  font-size:12.5px;color:var(--ink2);cursor:pointer}
.seg-btn.on{background:#fff;color:var(--ink);font-weight:600;box-shadow:0 1px 2px rgba(16,24,40,.08)}
#updSrcSeg .seg-btn{font-size:12px;line-height:1.25;padding:7px 4px}
.ver-row{display:flex;align-items:center;gap:10px;justify-content:space-between}
.ver-cur{font-size:12.5px;color:var(--ink2)}
.ver-cur b{color:var(--ink)}
.upd-box{margin-top:10px;padding:11px 12px;border-radius:10px;background:#f7f9fc;
  border:1px solid var(--line2);font-size:12px;line-height:1.7;color:var(--ink2)}
.upd-box.ok{background:#f2fbf5;border-color:#cdeed9}
.upd-box.new{background:#f2f6ff;border-color:#d5e2ff}
.upd-box.fail{background:#fff6f6;border-color:#f7d4d4}
.upd-url{margin-top:7px;font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--ink);
  word-break:break-all;background:#fff;border:1px solid var(--line);border-radius:7px;
  padding:6px 8px;user-select:all;cursor:text}
.upd-actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.upd-help{margin-top:9px;font-size:11.5px;color:var(--ink3);line-height:1.8}
.upd-detail{margin-top:5px;font-size:11px;color:var(--ink3);word-break:break-all;line-height:1.6}
.upd-help b{color:var(--ink2)}
.upd-help ol{margin:6px 0 0;padding-left:18px}

/* ---------- 更新弹窗里的「一句话摘要 + 分平台详细」（v1.4.4） ----------
   摘要来自发布正文里那句「一句话」，控制在 100 字内；下面按 Windows / 安卓
   列出各条目，超出高度先滚动；末尾一条「具体详见 Release 页面」给全文。 */
.brief{margin-top:8px;padding:8px 10px;border-radius:9px;background:#fff;
  border:1px solid var(--line);font-size:12.5px;line-height:1.65;color:var(--ink);
  white-space:pre-line}
.au-brief{background:#f7f9fc}
.notes{margin-top:9px;max-height:220px;overflow:auto;padding:1px 10px;
  border:1px solid var(--line2);border-radius:9px;background:#fbfcfe;scrollbar-width:thin}
.upd-notes,.au-notes{max-height:220px}
.notes::-webkit-scrollbar{width:8px}
.notes::-webkit-scrollbar-thumb{background:#d7dde7;border-radius:4px}
.notes::-webkit-scrollbar-track{background:transparent}
.note{padding:7px 0;border-bottom:1px dashed var(--line2)}
.note:last-child{border-bottom:0}
.note-h{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap;font-size:12px;
  line-height:1.5;color:var(--ink)}
.note-tag{flex:0 0 auto;font-size:10.5px;padding:1px 6px;border-radius:999px;
  background:#eef1f6;color:var(--ink2);white-space:nowrap}
.note-tag.win{background:#eef4ff;color:#2b5bd0}
.note-tag.android{background:#eaf7ee;color:#1a7f45}
.note-tag.both{background:#f3eefe;color:#6b3fc4}
.note-b{margin-top:2px;font-size:11.5px;line-height:1.7;color:var(--ink3);white-space:pre-line}
.more{margin-top:7px;font-size:11.5px;color:var(--ink3)}
.more a{color:var(--accent);text-decoration:none;cursor:pointer}
.more a:hover{text-decoration:underline}

/* ---------- 启动自动检查更新（v1.4.2） ---------- */
#autoUpdMask{z-index:900}
.auto-upd{position:relative;width:min(470px,100%)}
.auto-upd h3{padding-right:34px}
.au-close{position:absolute;top:8px;right:10px;width:30px;height:30px;border:0;border-radius:8px;
  background:transparent;color:var(--ink3);font-size:19px;line-height:1;cursor:pointer}
.au-close:hover{background:#f1f3f7;color:var(--ink)}
.au-badge{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;margin-bottom:7px}
.au-badge.sug{background:#eef4ff;color:#2b5bd0}
.au-badge.strong{background:#fff0ea;color:#b3401a}
#autoUpdText{white-space:pre-line}
.au-spin{display:flex;align-items:center;gap:9px;margin-top:2px;font-size:12px;color:var(--ink3)}
.au-spin i{width:13px;height:13px;border:2px solid #e0e5ee;border-top-color:var(--accent);
  border-radius:50%;display:inline-block;animation:au-rot .9s linear infinite}
@keyframes au-rot{to{transform:rotate(360deg)}}
.au-acts{display:flex;gap:9px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap}
/* ---------- 跨版本说明翻页（v1.4.6.5） ----------
   当前版本落后好几个版本时，弹窗里能逐页翻看每一版的说明；
   但翻页只改说明，下载目标永远是最后一页（最新版）。 */
.vp{margin:10px 0 0;border:1px solid var(--line);border-radius:10px;background:#fbfcfe;overflow:hidden}
.vp-h{display:flex;flex-wrap:wrap;gap:4px 10px;justify-content:space-between;align-items:baseline;
  padding:7px 11px;font-size:11.5px;color:var(--ink3);background:#f4f7fd;border-bottom:1px solid var(--line)}
.vp-h b{color:var(--ink);font-weight:600}
.vp-body{padding:11px 13px 3px;touch-action:pan-y;cursor:grab;min-height:64px}
.vp-body.dragging{cursor:grabbing}
.vp-body .brief{margin:0 0 8px}
.vp-body .note{margin-top:8px}
.vp-nav{display:flex;align-items:center;justify-content:space-between;gap:8px;
  padding:7px 10px;border-top:1px solid var(--line);background:#f7f9fc}
.vp-nav button{border:1px solid var(--line);background:#fff;border-radius:7px;padding:4px 10px;
  font-size:12px;color:var(--ink2);cursor:pointer}
.vp-nav button:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
.vp-nav button:disabled{opacity:.38;cursor:default}
.vp-pos{font-size:11.5px;color:var(--ink3)}
.vp-goal{padding:6px 11px 8px;font-size:11.5px;color:#1f5b2e;background:#f2fbf4;
  border-top:1px dashed #cfe8d6}
.vp-goal b{color:#14501f}

.au-url{margin-top:10px;font-family:ui-monospace,Consolas,monospace;font-size:11px;color:var(--ink3);
  word-break:break-all;background:#f7f9fc;border:1px solid var(--line);border-radius:8px;padding:7px 9px}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand">
      <div class="logo">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 3l7 3v6c0 4.5-3 7.7-7 9-4-1.3-7-4.5-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/>
        </svg>
      </div>
      <div>
        <h1>PDF 隐私打码工具<span class="nocap" title="扫描件是纯图片、没有文字层，会自动用本地 OCR 识别（离线运行、不联网）；识别不到时可手工框选">支持扫描件</span></h1>
        <p>真马赛克 · 全程本地零上传 · <span class="hint-draw">扫描件自动识别 · 也可手动框选</span></p>
      </div>
    </div>
    <div class="top-right">
      <div class="badge-local"><span class="dot"></span>本机运行 127.0.0.1，文件不出电脑</div>
      <div class="about-link" id="setBtn">设置</div>
      <div class="about-link" id="aboutBtn">关于</div>
      <div class="quit" id="quitBtn" title="关闭程序">退出</div>
    </div>
  </header>

  <main>
    <section class="drop-view" id="dropView">
      <div class="drop-card" id="dropCard">
        <div class="ico">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#2f6bff" stroke-width="1.7"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/>
            <path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/>
          </svg>
        </div>
        <h2>把 PDF 拖到这里</h2>
        <p>自动识别手机号、身份证号、银行卡号、邮箱、姓名、座机、地址、出生日期、性别年龄</p>
        <button class="btn primary" id="pickBtn">选择 PDF 文件</button>
        <input type="file" id="fileInput" accept=".pdf,application/pdf" hidden>
      </div>
      <div class="tips">
        <span>· 不上传服务器</span><span>· 原文不可还原</span><span>· 版面保持一致</span>
        <span>· 原文件不改动</span><span>· 保存位置可自定义</span>
      </div>
      <div class="credit">
        <span>__CREDIT__</span>
        <span class="credit-url" id="footUrl" data-url="__URL__" title="点击复制原项目地址">原项目地址：__URLSHORT__</span>
        <span class="credit-url" id="footUrlGitee" data-url="__URLGITEE__" title="点击复制 Gitee 镜像地址">Gitee: __URLSHORT_GITEE__</span>
      </div>
    </section>

    <section class="work-view" id="workView" hidden>
      <aside class="side">
        <div class="file-card">
          <div class="file-ico">PDF</div>
          <div class="file-meta">
            <div class="file-name" id="fName">-</div>
            <div class="file-sub" id="fSub">-</div>
          </div>
          <button class="btn ghost" id="reupload" title="重新选择文件" style="padding:6px 10px">换</button>
        </div>
        <div class="stats" id="stats"></div>
        <div class="warn" id="scanWarn" hidden></div>
        <div class="list-head">
          <span>识别结果 <b id="totalCnt">0</b> 处</span>
          <span><button class="link" id="selAll">全选</button> / <button class="link" id="selNone">全不选</button></span>
        </div>
        <div class="list" id="list"></div>
      </aside>

      <div class="viewer">
        <div class="toolbar">
          <div class="tb-group">
            <button class="tb-btn" id="prevPage" title="上一页">‹</button>
            <span class="pgnum" id="pgNum">1 / 1</span>
            <button class="tb-btn" id="nextPage" title="下一页">›</button>
          </div>
          <div class="tb-group">
            <button class="tb-btn" id="zoomOut">−</button>
            <span class="pgnum" id="zoomTxt" style="min-width:44px">120%</span>
            <button class="tb-btn" id="zoomIn">+</button>
          </div>
          <div class="tb-group" style="gap:6px">
            <button class="tb-btn" id="drawBtn" title="按住鼠标拖出一个要打码的区域">手动框选</button>
            <button class="tb-btn" id="eraseBtn" title="按住鼠标擦掉误框的一小块，旁边该打码的内容不受影响">橡皮擦</button>
          </div>
          <div class="spacer"></div>
          <div class="hint-chip" title="左键按住拖动 = 框出要打码的区域；Ctrl+滚轮或笔记本双指捏合 = 缩放；放大后按住右键拖动 = 看前后左右；双击页面上的方框 = 取消或恢复该处打码">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/>
              <path d="M12 11v5"/><path d="M12 8h.01"/></svg>
            拖动框选 · 双击取消 · Ctrl+滚轮缩放 · 右键平移
          </div>
          <label class="switch">
            <input type="checkbox" id="maskPreview" checked><span class="track"></span>预览打码效果
          </label>
        </div>
        <div class="canvas-wrap" id="canvasWrap">
          <img id="pageImg" alt="页面预览">
        </div>
      </div>
    </section>
  </main>

  <div class="actionbar" id="actionBar" hidden>
    <div class="sum">已选 <b id="selCount">0</b> 处 · 生成后原文将被永久打散</div>
    <div class="spacer"></div>
    <button class="btn" id="backBtn">重新选择文件</button>
    <button class="btn primary" id="goBtn">生成打码 PDF</button>
  </div>
</div>

<div class="overlay" id="overlay" hidden>
  <div class="jobp" id="jobPanel">
    <div class="jobhead">
      <div class="jobtitle" id="jobTitle">处理中…</div>
      <div class="jobpct" id="jobPct">0%</div>
    </div>
    <div class="jobpage" id="jobPage">正在准备…</div>
    <div class="barrow"><span id="jobPageLabel">当前页</span>
      <div class="bar"><i id="jobBarPage"></i></div><b id="jobPagePct">0%</b></div>
    <div class="barrow strong"><span id="jobAllLabel">整个文件</span>
      <div class="bar"><i id="jobBarAll"></i></div><b id="jobAllPct">0%</b></div>
    <div class="jobbtns">
      <button class="jbtn primary" id="jobPause">暂停</button>
      <button class="jbtn stop" id="jobStop">停止</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<div class="about-mask" id="aboutMask" hidden>
  <div class="about-box">
    <h3>PDF 隐私打码工具</h3>
    <div class="ver">版本 __VERSION__ · <span id="verNote">本地离线运行</span></div>
    <dl>
      <dt>指导作者</dt><dd>__AUTHOR__。<br>需求、识别规则的设计、验收测试全部由本人完成。</dd>
      <dt>开发</dt><dd>__DEVELOPER__<br><span data-en-html='Note: DeepSeek-V4.1-Flash is the model we usually and mainly rely on - the core backbone for most scenarios and maintenance; other models such as GLM 5.3 Flash and Hy4 Flash are used occasionally.'>说明：常用、惯用、主要是 DeepSeek-V4.1-Flash——大多数场景和功能维护升级都由它作核心骨架；偶尔也会用其他模型，如 GLM 5.3 Flash、Hy4 Flash。</span></dd>
      <dt>开源协议</dt><dd>__LICENSE__</dd>
      <dt>原项目地址</dt><dd class="url" id="aboutUrl" data-url="__URL__" title="点击复制">__URL__</dd>
      <dt>Gitee 镜像</dt><dd class="url" id="aboutUrlGitee" data-url="__URLGITEE__" title="点击复制">__URLGITEE__</dd>
    </dl>
    <p class="about-note" data-en-html='<b>Maintenance:</b> I don’t usually have enough time or energy, so I only check in once every month or two — replies will be slow, don’t expect instant answers. All the code is public: if something doesn’t work for you, feel free to fix it or keep building on it. Commercial use is fine too — no fee, no need to ask me, just follow the three points below.'>
      <b>关于维护：</b>我平时没有充足的时间和精力，大概一两个月才上来看一两次，
      所以回复不会很快，别指望秒回。代码全部公开，修不动的地方欢迎你自己改、自己接着用；
      商用也行，不用付钱也不用问我，照下面三条做就可以。
    </p>
    <div class="about-rule" data-en-html='<b>Forks / commercial use: three requirements</b><ol><li>Keep the credit <em>Advisor: __AUTHOR__</em> and the developer line, unmodified.</li><li>Show the <em>upstream URL</em> where users can see it — the line just above in this window counts.</li><li>Modified builds must state: “Based on that project, not released by the original author.”</li></ol><p class="rule-foot">The above is the additional term under AGPL-3.0 section 7(b); the full text is in <code>ADDITIONAL-TERMS.md</code>. The license itself also requires you to publish the modified source and, for network services, offer that source to users. The program name and icon are not licensed — rename before republishing.</p>'>
      <b>二次开发 / 商用：三条硬要求</b>
      <ol>
        <li>保留署名 <em>指导作者：__AUTHOR__</em> 与开发者信息，不得删改。</li>
        <li>在程序里标注<em>原项目地址</em>，让使用者看得见——本窗口上方那行就是。</li>
        <li>改动过的版本必须注明「本程序基于该地址修改，非原作者发布」。</li>
      </ol>
      <p class="rule-foot">
        以上依据 AGPL-3.0 第 7 条(b) 附加条款，全文见开源包 <code>ADDITIONAL-TERMS.md</code>。
        另外协议本身要求：修改后的源码也要一并开放，网络服务须向使用者提供源码。
        程序名称与图标不在授权范围内，二次发布请改名。
      </p>
    </div>
    <div class="about-thanks">
      <b>如果这个工具帮到了你</b>
      <p data-en-html='It started as a small side project, and I am glad it is useful. Buying me a milk tea would make my day — completely optional. The app stays free and fully featured either way.'>本来就是顺手做的小工具，能派上用场就挺好。
      完全自愿，不打赏也一样免费、功能不缺。</p>
      <div class="about-star">
        <div class="about-star-txt">
          <b>星标仓库 = 最好的支持</b>
          <span data-en-html='No money needed — starring the repo helps others find it and keeps me motivated.'>不想花钱也没关系，点一颗 Star 就是最好的支持：别人搜得到，我才更有动力维护。</span>
        </div>
        <button class="btn" id="aboutStar">去点 Star</button>
      </div>
      <div class="thanks-cap">国内用户：微信扫码，请我喝杯奶茶（金额随意）</div>
      <img id="thanksQr" src="data:image/png;base64,__THANKS__" alt="赞赏码">
      <div class="thanks-cap">点下面的按钮保存这张码</div>
      <div class="thanks-save-row"><button class="btn" id="thanksSave">保存赞赏码</button></div>
    </div>
    <div class="about-actions"><button class="btn primary" id="aboutOk">知道了</button></div>
  </div>
</div>

<div class="modal-mask" id="autoUpdMask" hidden>
  <div class="modal auto-upd">
    <button class="au-close" id="autoUpdClose" title="关闭">×</button>
    <div class="au-badge" id="autoUpdBadge" hidden></div>
    <h3 id="autoUpdTitle">正在检查更新</h3>
    <p class="sub" id="autoUpdText"></p>
    <div class="vp" id="autoUpdVp" hidden>
      <div class="vp-h"><span id="autoUpdVpMeta"></span><span id="autoUpdVpTip"></span></div>
      <div class="vp-body" id="autoUpdVpBody"></div>
      <div class="vp-nav">
        <button type="button" id="autoUpdVpPrev"></button>
        <span class="vp-pos" id="autoUpdVpPos"></span>
        <button type="button" id="autoUpdVpNext"></button>
      </div>
      <div class="vp-goal" id="autoUpdVpGoal"></div>
    </div>
    <div class="brief au-brief" id="autoUpdBrief" hidden></div>
    <div class="notes au-notes" id="autoUpdNotes" hidden></div>
    <div class="more au-more" id="autoUpdMore" hidden><a id="autoUpdMoreLink"></a></div>
    <div class="au-spin" id="autoUpdSpin" hidden><i></i><span id="autoUpdSpinText"></span></div>
    <div class="au-url" id="autoUpdUrl" hidden></div>
    <div class="au-acts" id="autoUpdActs" hidden></div>
  </div>
</div>

<div class="modal-mask" id="saveMask" hidden>
  <div class="modal">
    <h3>选择保存位置</h3>
    <p class="sub">打码后的 PDF 会存到这个文件夹，原文件不会被改动。</p>
    <label class="field-label">保存到</label>
    <div class="path-row">
      <input class="path-input" id="savePath" spellcheck="false" placeholder="点右侧「浏览」选一个文件夹">
      <button class="btn" id="saveBrowse">浏览…</button>
    </div>
    <label class="chk"><input type="checkbox" id="optRemember"><span><b>下次默认使用这个路径</b>　以后打开就停在这个文件夹</span></label>
    <label class="chk"><input type="checkbox" id="optNoAsk"><span><b>不再询问</b>　以后直接存到这里，不再弹这个窗口</span></label>
    <div class="modal-note">两个勾选随时能在右上角<em>「设置」</em>里改。都不勾也没关系，下次还会再问一次。</div>
    <div class="modal-actions">
      <button class="btn ghost" id="saveCancel">取消</button>
      <button class="btn primary" id="saveOk">确定</button>
    </div>
  </div>
</div>

<div class="modal-mask" id="setMask" hidden>
  <div class="modal">
    <h3>设置</h3>
    <p class="sub">默认保存位置就是打码文件存放的地方。留空则自动跟随原 PDF 所在的文件夹。</p>
    <label class="field-label">默认保存位置</label>
    <div class="path-row">
      <input class="path-input" id="setPath" spellcheck="false" placeholder="留空 = 跟随原 PDF 所在文件夹">
      <button class="btn" id="setBrowse">浏览…</button>
    </div>
    <label class="chk"><input type="checkbox" id="setAsk"><span><b>每次生成前，先问我保存到哪里</b>　最稳妥，不会存到想不到的地方</span></label>
    <div class="modal-note">
      取消上面那个勾选，程序就会一路静默保存到这里的文件夹，不再弹窗。<br>
      无论怎么设置，原 PDF 都只会被读取，不会被改动或删除。
    </div>

    <div class="set-sec">
      <label class="field-label">界面语言 / Language</label>
      <div class="seg" id="langSeg">
        <button class="seg-btn" data-lang="zh">中文</button>
        <button class="seg-btn" data-lang="en">English</button>
      </div>
    </div>

    <div class="set-sec">
      <label class="field-label">更新检查方式 / Update checking</label>
      <div class="seg" id="updModeSeg">
        <button class="seg-btn" data-updmode="auto">自动检查（启动时）</button>
        <button class="seg-btn" data-updmode="manual">手动检查</button>
      </div>
      <div class="modal-note" style="margin-top:8px">自动：每次启动在后台静默查一次，没有网络就不响。手动：只有你点下面的「检查更新」才联网。</div>

      <label class="field-label" style="margin-top:14px">更新源 / Update source</label>
      <div class="seg" id="updSrcSeg">
        <button class="seg-btn" data-updsrc="gitee">Gitee（建议中国大陆用户）</button>
        <button class="seg-btn" data-updsrc="github">GitHub</button>
      </div>
      <div class="modal-note" style="margin-top:8px">默认就是 Gitee。只有系统语言不是中文、时区也不在东八区（明显在海外）才默认改用 GitHub，判断不出来一律按 Gitee。界面语言不参与判断；选中的源连不上会自动换另一个再试，并在结果里写明这次用的是哪个源。点一下立即生效。</div>
    </div>

    <div class="set-sec">
      <label class="field-label">版本与更新</label>
      <div class="ver-row">
        <span class="ver-cur"><span id="verLabel1">当前版本</span> v<b id="curVer">__VERSION__</b> ·
          <span id="verLabel2">仓库最新</span> <b id="latestVer">—</b></span>
        <button class="btn" id="checkBtn">检查更新</button>
      </div>
      <div class="modal-note" style="margin-top:8px">开着「自动检查」时启动会静默查一次；关掉后只有点这里才会联网。查到的更新来自上面选定的源。</div>
      <div class="upd-box" id="updBox" hidden>
        <div id="updText"></div>
        <div class="vp" id="updVp" hidden>
          <div class="vp-h"><span id="updVpMeta"></span><span id="updVpTip"></span></div>
          <div class="vp-body" id="updVpBody"></div>
          <div class="vp-nav">
            <button type="button" id="updVpPrev"></button>
            <span class="vp-pos" id="updVpPos"></span>
            <button type="button" id="updVpNext"></button>
          </div>
          <div class="vp-goal" id="updVpGoal"></div>
        </div>
        <div class="brief" id="updBrief" hidden></div>
        <div class="notes" id="updNotes" hidden></div>
        <div class="more" id="updMore" hidden><a id="updMoreLink"></a></div>
        <div class="upd-detail" id="updDetail" hidden></div>
        <div class="upd-url" id="updUrl" hidden></div>
        <div class="upd-actions" id="updActions" hidden>
          <button class="btn primary" id="updOpen">用浏览器打开下载</button>
          <button class="btn" id="updCopy">复制链接</button>
        </div>
        <div class="upd-help" id="updHelp" hidden></div>
      </div>
    </div>

    <div class="modal-actions">
      <button class="btn ghost" id="setReset">恢复默认</button>
      <button class="btn primary" id="setOk">保存</button>
    </div>
  </div>
</div>

<script>
const TOKEN = "__TOKEN__";
const BOOT = __BOOT__;
const S = {docId:null, name:'', pages:[], findings:[], sel:new Set(), page:0, zoom:1.2,
           mask:true, drawing:false, mode:'pan', erasers:{}, hi:null,
           scanned:[], ocrPages:[], ocrReady:false, outDir:'', stats:null, size:0};

/* 工作区里还开着文件时，关标签页 / 刷新前先让浏览器问一句。
   浏览器只允许这一种拦截方式，文案由浏览器决定（改不了），但足以避免
   「手一滑关掉，刚框好的选区全没了」——安卓端有对应的离开确认窗口。 */
window.addEventListener('beforeunload', e => {
  if (!S.docId) return;
  e.preventDefault();
  e.returnValue = '';
});

const $ = id => document.getElementById(id);

/* ---------- 中英双语 ----------
   静态文字按「原文」查表替换（含 title / placeholder / alt），
   动态提示走 T(中文, English)。切换立即生效，不用重启。 */
let LANG = 'zh';
const DICT = {
  '设置':'Settings', '关于':'About', '退出':'Quit',
  '手动框选':'Manual box', '橡皮擦':'Eraser',
  '按住鼠标拖出一个要打码的区域':'Hold and drag to mark an area to mask',
  '按住鼠标擦掉误框的一小块，旁边该打码的内容不受影响':
    'Hold and drag to erase a small mis-boxed patch; nearby masks stay',
  'PDF 隐私打码工具':'PDF Privacy Masker',
  '支持扫描件':'Scans supported',  '真马赛克 · 全程本地零上传 · ':'Real mosaic · 100% local · ',
  '扫描件自动识别 · 也可手动框选':'scans read automatically · manual box too',
  '本机运行 127.0.0.1，文件不出电脑':'Local 127.0.0.1 — files never leave your PC',
  '把 PDF 拖到这里':'Drop a PDF here',
  '自动识别手机号、身份证号、银行卡号、邮箱、姓名、座机、地址、出生日期、性别年龄':
    'Detects phone numbers, ID numbers, bank cards, emails, names, landlines, addresses, birth dates, gender and age',
  '选择 PDF 文件':'Choose a PDF',
  '· 不上传服务器':'· No uploads', '· 原文不可还原':'· Text unrecoverable',
  '· 版面保持一致':'· Layout kept', '· 原文件不改动':'· Original untouched',
  '· 保存位置可自定义':'· Choose where to save',
  '换':'Swap', '识别结果 ':'Detected ', ' 处':' items',
  '全选':'All', '全不选':'None',
  '框选手动打码':'Draw a box',
  '拖动框选 · 双击取消 · Ctrl+滚轮缩放 · 右键平移':'Drag to box · double-click to mute · Ctrl+wheel zoom · right-drag to pan',
  '预览打码效果':'Preview mosaic',
  '已选 ':'Selected ', ' 处 · 生成后原文将被永久打散':' items · text will be destroyed for good',
  '重新选择文件':'Choose another file', '生成打码 PDF':'Generate masked PDF',
  '处理中…':'Working…',
  '指导作者':'Advisor', '开发':'Built by', '开源协议':'License', '原项目地址':'Upstream',
  'Gitee 镜像':'Gitee mirror',
  '本地离线运行':'runs fully offline',
  '腾讯 WorkBuddy × DeepSeek-V4.1-Flash':'Tencent WorkBuddy × DeepSeek-V4.1-Flash',
  '需求、识别规则的设计、验收测试全部由本人完成。':
    'Requirements, detection rule design and acceptance testing were all done by the author.',
  '如果这个工具帮到了你':'If this tool helped you',
  '本来就是顺手做的小工具，能派上用场就挺好。要是你愿意请我喝杯奶茶，我会挺开心——':
    'It started as a small side project, and I am glad it is useful. If you feel like buying me a milk tea, that would make my day —',
  '完全自愿，不打赏也一样免费、功能不缺。':
    'completely optional. The app stays free and fully featured either way.',
  '微信扫码 · 金额随意 · 点下面的按钮保存图片':'Scan in WeChat · any amount · use the button below to save',
  '保存赞赏码':'Save the tip QR',
  '去点 Star':'Star it',
  '星标仓库 = 最好的支持':'A star is the best support',
  '国内用户：微信扫码，请我喝杯奶茶（金额随意）':'In China? Scan in WeChat to buy me a milk tea (any amount)',
  '点下面的按钮保存这张码':'Use the button below to save this code',
  '赞赏码':'Tip QR code', '知道了':'Got it', '点击复制':'Click to copy',
  '点击复制原项目地址':'Click to copy the upstream URL',
  '选择保存位置':'Choose a folder', '打码后的 PDF 会存到这个文件夹，原文件不会被改动。':
    'The masked PDF goes into this folder; the original is never modified.',
  '保存到':'Save to', '点右侧「浏览」选一个文件夹':'Pick a folder with “Browse”',
  '浏览…':'Browse…', '下次默认使用这个路径':'Remember this folder',
  '不再询问':'Don\'t ask again',
  '以后打开就停在这个文件夹':'next time we start here',
  '以后直接存到这里，不再弹这个窗口':'save straight here from now on',
  '最稳妥，不会存到想不到的地方':'safest — never lands somewhere unexpected',
  '两个勾选随时能在右上角':'Both toggles can be changed anytime under ',
  '「设置」':'“Settings”',
  '里改。都不勾也没关系，下次还会再问一次。':' at the top right. Leaving them unticked is fine — we will ask again next time.',
  '取消':'Cancel', '确定':'OK',
  '默认保存位置就是打码文件存放的地方。留空则自动跟随原 PDF 所在的文件夹。':
    'The default folder is where masked PDFs go. Leave it empty to follow the original PDF.',
  '默认保存位置':'Default save folder', '留空 = 跟随原 PDF 所在文件夹':'Empty = follow the original PDF',
  '每次生成前，先问我保存到哪里':'Ask me where to save before each run',
  '取消上面那个勾选，程序就会一路静默保存到这里的文件夹，不再弹窗。':
    'Untick the box above and the app saves here silently, with no dialog.',
  '无论怎么设置，原 PDF 都只会被读取，不会被改动或删除。':
    'Whatever you choose, the original PDF is only ever read — never modified or deleted.',
  '恢复默认':'Reset', '保存':'Save',
  '版本与更新':'Version & updates', '当前版本':'Current', '仓库最新':'latest',
  '检查更新':'Check for updates',
  '更新检查方式 / Update checking':'Update checking',
  '自动检查（启动时）':'Automatic (at launch)', '手动检查':'Manual only',
  '自动：每次启动在后台静默查一次，没有网络就不响。手动：只有你点下面的「检查更新」才联网。':
    'Automatic: one silent check at every launch, skipped when offline. Manual: only connects when you tap “Check for updates” below.',
  '更新源 / Update source':'Update source',
  'Gitee（建议中国大陆用户）':'Gitee (recommended in mainland China)',
  '默认就是 Gitee。只有系统语言不是中文、时区也不在东八区（明显在海外）才默认改用 GitHub，判断不出来一律按 Gitee。界面语言不参与判断；选中的源连不上会自动换另一个再试，并在结果里写明这次用的是哪个源。点一下立即生效。':
    'Gitee is the default. GitHub is only picked when the system language is not Chinese and the time zone is not UTC+8, i.e. clearly abroad; if either cannot be determined, Gitee is used. The interface language takes no part. If the chosen source is unreachable the other one is tried and the result says which source was used. Applies immediately.',
  '开着「自动检查」时启动会静默查一次；关掉后只有点这里才会联网。查到的更新来自上面选定的源。':
    'With automatic checking on, one silent check runs at launch; with it off, only this button goes online. Updates come from the source picked above.',
  '开着「自动检查」时启动会静默查一次；关掉后只有点这里才会联网。查到的更新来自上面选定的源。':'Updates are checked once at launch; offline, the check is skipped silently. You can also check again here at any time.', '用浏览器打开下载':'Open download in browser',
  '复制链接':'Copy link',
  '扫描件是纯图片、没有文字层，会自动用本地 OCR 识别（离线运行、不联网）；识别不到时可手工框选':
    'A scan has no text layer, so it is read with local OCR (offline, nothing uploaded); fall back to the manual box tool if needed',
  '按住鼠标拖动可以框出要打码的区域；Ctrl+滚轮或笔记本双指捏合可以缩放；放大后按住右键拖动能看前后左右；双击页面上的方框，可以取消或恢复该处打码':
    'Hold and drag to draw a box; Ctrl+wheel or a two-finger pinch zooms; right-drag pans once zoomed in; double-click a box to mute or unmute it',
  '重新选择文件':'Choose another file',
  '关闭程序':'Quit'
};
// 文本节点会被 trim 过再查表，所以键也统一去空白，省得结尾多个空格就漏译
const TK = {};
Object.keys(DICT).forEach(k=>{ TK[k.trim()] = DICT[k]; });

const PREFIX = [
  ['版本 ', 'Version '],
  ['项目创作时为初中生', 'Was a junior high school student when this project was created'],
  ['原项目地址：', 'Upstream: ']
];
const TYPE_EN = {phone:'Phone', idcard:'ID number', bankcard:'Bank card', email:'Email',
  name:'Name', tel:'Landline', address:'Address', birth:'Birth date', gender:'Gender',
  age:'Age', manual:'Manual box'};
const STAT_EN = {'身份证号':'ID number','银行卡号':'Bank card','手机号':'Phone','座机号':'Landline',
  '邮箱':'Email','姓名':'Name','地址':'Address','出生日期':'Birth date','性别':'Gender',
  '年龄':'Age','手动框选':'Manual','橡皮擦':'Eraser'};

function T(zh, en){ return LANG === 'en' ? en : zh; }
function labelOf(f){
  if (LANG !== 'en') return f.label;
  return TYPE_EN[f.type] || f.label;
}
const ORIG_TEXT = new WeakMap();
function trNode(node){
  if(!ORIG_TEXT.has(node)) ORIG_TEXT.set(node, node.nodeValue);
  const raw = ORIG_TEXT.get(node);
  const s = raw.trim();
  if(!s) return;
  let out = TK[s];
  if(out === undefined){
    for(const [zh, en] of PREFIX){
      if(s.indexOf(zh) === 0){ out = en + s.slice(zh.length); break; }
    }
  }
  if(out === undefined){ node.nodeValue = raw; return; }
  const lead = raw.match(/^\s*/)[0], tail = raw.match(/\s*$/)[0];
  node.nodeValue = LANG === 'en' ? (lead + out + tail) : raw;
}
function applyLang(){
  // 含行内标签的整段文字，直接整块换成另一种语言（原文存进 dataset，切回来能还原）
  document.querySelectorAll('[data-en-html]').forEach(el=>{
    if(el.dataset.zhHtml === undefined) el.dataset.zhHtml = el.innerHTML;
    el.innerHTML = LANG === 'en' ? el.dataset.enHtml : el.dataset.zhHtml;
  });
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(n){
      const p = n.parentNode;
      if(!p) return NodeFilter.FILTER_REJECT;
      if(p.nodeName === 'SCRIPT' || p.nodeName === 'STYLE') return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  let n; while((n = tw.nextNode())) trNode(n);
  document.querySelectorAll('[title],[placeholder],[alt]').forEach(el=>{
    ['title','placeholder','alt'].forEach(a=>{
      if(!el.hasAttribute(a)) return;
      const key = 'i18n' + a;
      if(el.dataset[key] === undefined) el.dataset[key] = el.getAttribute(a);
      const zh = el.dataset[key];
      el.setAttribute(a, LANG === 'en' ? (DICT[zh] || zh) : zh);
    });
  });
  document.documentElement.lang = LANG === 'en' ? 'en' : 'zh-CN';
  document.title = T('PDF 隐私打码工具', 'PDF Privacy Masker');
  document.querySelectorAll('.seg-btn').forEach(b=>b.classList.toggle('on', b.dataset.lang === LANG));
  renderMeta(); renderList(); renderStats(S.stats); syncBar(); renderUpdate();
  syncUpdSeg();
}

const TYPE_COLOR = {phone:'#f59e0b', idcard:'#e5484d', bankcard:'#7c5cff', email:'#12a150',
  name:'#2f6bff', tel:'#ea580c', address:'#0aa2c0', birth:'#d6409f', gender:'#78808c',
  age:'#78808c', manual:'#111827'};

function esc(s){return (s+'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function toast(msg, err){
  const t = $('toast'); t.textContent = msg; t.className = 'toast show' + (err?' err':'');
  clearTimeout(t._h); t._h = setTimeout(()=>{t.className='toast';}, 2600);
}
/* 复制原项目地址（附加条款要求它必须可见、可留存） */
function copyText(text, okMsg){
  const done = ()=> toast(okMsg + text);
  const fallback = ()=>{
    try{
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position='fixed'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta); done();
    }catch(e){ toast(T('复制失败，请手动记下：', 'Copy failed — write this down: ') + text, true); }
  };
  if (navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(fallback);
  } else fallback();
}
function copyProjectUrl(el){
  copyText(el.dataset.url || el.textContent, T('已复制项目地址：', 'Link copied: '));
}
/* ---------- 处理进度面板 ---------- */
/* 服务端每跑一页就会更新 /api/job，这里 250ms 拉一次画两条进度条。
   暂停 / 停止是「请求服务端」，本地不自己编状态——否则界面说停了、后台还在跑。 */
let JOB_TIMER = 0, JOB_PAUSED = false;

function jobShow(title){
  $('overlay').hidden = false;
  const el = $('jobTitle');
  el.textContent = title || T('正在处理…', 'Working…');
  $('jobPageLabel').textContent = T('当前页', 'This page');
  $('jobAllLabel').textContent = T('整个文件', 'Whole file');
  $('jobPause').textContent = T('暂停', 'Pause');
  $('jobStop').textContent = T('停止', 'Stop');
  $('jobPanel').classList.remove('paused');
  $('jobPage').textContent = T('正在准备…', 'Getting ready…');
  $('jobPct').textContent = '0%';
  $('jobPagePct').textContent = '0%';
  $('jobAllPct').textContent = '0%';
  $('jobBarPage').style.width = '0%';
  $('jobBarAll').style.width = '0%';
  JOB_PAUSED = false;
  clearTimeout(JOB_TIMER);
  jobPoll();
}
function jobHide(){
  clearTimeout(JOB_TIMER); JOB_TIMER = 0;
  $('overlay').hidden = true;
}
async function jobPoll(){
  try{
    const r = await fetch('/api/job', {headers:{'X-Token':TOKEN}, cache:'no-store'});
    if(r.ok){ const d = await r.json(); if(d && d.active) paintJob(d); }
  }catch(e){}
  JOB_TIMER = setTimeout(jobPoll, 250);
}
function paintJob(d){
  const pc = Math.round((d.overall || 0) * 100);
  const pf = Math.round((d.pageFrac || 0) * 100);
  JOB_PAUSED = !!d.paused;
  $('jobTitle').textContent = d.paused ? T('已暂停', 'Paused')
    : (LANG === 'en' ? (d.titleEn || d.title) : d.title);
  $('jobPct').textContent = pc + '%';
  $('jobPagePct').textContent = pf + '%';
  $('jobAllPct').textContent = pc + '%';
  $('jobBarPage').style.width = pf + '%';
  $('jobBarAll').style.width = pc + '%';
  $('jobPage').textContent = d.pages > 0
    ? (LANG === 'en' ? ('Page ' + (d.page || 1) + ' of ' + d.pages)
                     : ('第 ' + (d.page || 1) + ' / ' + d.pages + ' 页'))
      + (d.note ? (' · ' + d.note) : '')
    : T('正在准备…', 'Getting ready…');
  $('jobPanel').classList.toggle('paused', JOB_PAUSED);
  $('jobPause').textContent = JOB_PAUSED ? T('继续', 'Resume') : T('暂停', 'Pause');
}
async function jobCtrl(what){
  try{
    const r = await fetch('/api/job/' + what, {method:'POST', headers:{'X-Token':TOKEN}});
    if(r.ok){ const d = await r.json(); if(d && d.active) paintJob(d); }
  }catch(e){}
}
$('jobPause').onclick = () => jobCtrl(JOB_PAUSED ? 'resume' : 'pause');
$('jobStop').onclick = () => jobCtrl('stop');
async function api(path, opts){
  opts = opts || {};
  opts.headers = Object.assign({'X-Token':TOKEN}, opts.headers||{});
  const r = await fetch(path, opts);
  const ct = r.headers.get('content-type')||'';
  if (!r.ok){
    let m = T('请求失败', 'Request failed') + ' (' + r.status + ')';
    try{ const j = await r.json(); m = j.error||m; }catch(e){}
    throw new Error(m);
  }
  return ct.indexOf('json')>=0 ? r.json() : r;
}

/* ---------- 上传 / 打开 ---------- */
async function uploadFile(file){
  if(!file) return;
  if(!/\.pdf$/i.test(file.name)) return toast(T('只支持 PDF 文件', 'PDF files only'), true);
  jobShow(T('正在识别敏感信息…', 'Scanning for sensitive data…'));
  try{
    const r = await fetch('/api/upload', {method:'POST',
      headers:{'X-Token':TOKEN,'X-File-Name':encodeURIComponent(file.name)}, body:file});
    if(!r.ok){ let m=T('识别失败', 'Scan failed'); try{const j=await r.json(); m=j.error||m;}catch(e){} throw new Error(m); }
    applyDoc(await r.json());
  }catch(e){ toast(e.message, true); }
  finally{ jobHide(); }
}
async function openPath(path){
  jobShow(T('正在识别敏感信息…', 'Scanning for sensitive data…'));
  try{
    const d = await api('/api/open', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path:path})});
    applyDoc(d);
  }catch(e){ toast(e.message, true); }
  finally{ jobHide(); }
}

function applyDoc(d){
  S.docId = d.docId; S.name = d.name; S.pages = d.pages; S.findings = d.findings;
  S.scanned = d.scanned || []; S.outDir = d.outDir || '';
  S.ocrPages = d.ocrPages || []; S.ocrReady = !!d.ocrReady;
  S.stats = d.stats || {}; S.size = d.size || 0;
  S.sel = new Set(d.findings.filter(f=>!f.suspect).map(f=>f.id)); S.page = 0; S.hi = null;
  $('dropView').hidden = true; $('workView').hidden = false; $('actionBar').hidden = false;
  $('fName').textContent = d.name;
  renderMeta();
  renderStats(S.stats);
  renderList(); refreshPreview(); syncBar();
}

/* 文件摘要 + 扫描件提醒：切换语言时要重算，所以单独抽出来 */
function renderMeta(){
  if(!S.docId) return;
  const kb = (S.size||0)/1024;
  const sz = kb > 1024 ? (kb/1024).toFixed(1)+' MB' : Math.max(1, Math.round(kb))+' KB';
  const hitPages = new Set(S.findings.filter(f=>!f.suspect).map(f=>f.page)).size;
  const nHit = S.findings.filter(f=>!f.suspect).length;
  const nSus = S.findings.filter(f=>f.suspect).length;
  let sub;
  if(LANG === 'en'){
    sub = S.pages.length + ' pages · ' + sz + ' · ' + nHit + ' items (' +
      hitPages + '/' + S.pages.length + ' pages with hits)';
    if(nSus) sub += ', plus ' + nSus + ' possible names to confirm';
  } else {
    sub = S.pages.length + ' 页 · ' + sz + ' · 识别到 ' + nHit + ' 处（' +
      hitPages + '/' + S.pages.length + ' 页有内容）';
    if(nSus) sub += '，另有 ' + nSus + ' 处疑似人名待确认';
  }
  $('fSub').textContent = sub;
  if(S.scanned && S.scanned.length){
    const fmt = arr => arr.map(i=>i+1).join(T('、', ', '));
    const done = (S.scanned||[]).filter(i=>(S.ocrPages||[]).indexOf(i)>=0);
    const miss = (S.scanned||[]).filter(i=>(S.ocrPages||[]).indexOf(i)<0);
    let msg;
    if(!S.ocrReady){
      msg = T(
        '第 ' + fmt(S.scanned) + ' 页没有文字层（可能是扫描件），当前安装包不含 OCR 组件，无法自动识别，请用「框选手动打码」补齐。',
        'Page ' + fmt(S.scanned) + ' has no text layer. This build has no OCR component, so those pages cannot be detected — use the manual box tool.');
    } else if(!miss.length){
      msg = T(
        '第 ' + fmt(done) + ' 页没有文字层（扫描件），已用本地 OCR 自动识别，全程离线、不上传任何内容。请顺手核对一遍结果。',
        'Page ' + fmt(done) + ' has no text layer (a scan). It was read with local OCR — fully offline, nothing uploaded. Please double-check the result.');
    } else if(done.length){
      msg = T(
        '第 ' + fmt(done) + ' 页已用本地 OCR 自动识别；第 ' + fmt(miss) + ' 页没能识别出文字，请用「框选手动打码」补齐。',
        'Page ' + fmt(done) + ' was read with local OCR; page ' + fmt(miss) + ' could not be read — use the manual box tool there.');
    } else {
      msg = T(
        '第 ' + fmt(miss) + ' 页没有文字层，本地 OCR 也没能识别出文字，请用「框选手动打码」补齐。',
        'Page ' + fmt(miss) + ' has no text layer and local OCR could not read it — use the manual box tool.');
    }
    $('scanWarn').hidden = false;
    $('scanWarn').textContent = msg;
  } else {
    $('scanWarn').hidden = true;
  }
}

function renderStats(stats){
  const box = $('stats'); box.innerHTML = '';
  stats = stats || S.stats || {};
  const order = ['身份证号','银行卡号','手机号','座机号','邮箱','姓名','地址','出生日期','性别','年龄','手动框选'];
  let n = 0;
  order.forEach(k=>{
    if(!stats[k]) return;
    n += stats[k];
    const c = TYPE_COLOR[Object.keys(TYPE_COLOR).find(t=>(
      {'身份证号':'idcard','银行卡号':'bankcard','手机号':'phone','座机号':'tel','邮箱':'email',
       '姓名':'name','地址':'address','出生日期':'birth','性别':'gender','年龄':'age',
       '手动框选':'manual'}[k]))] || '#888';
    const el = document.createElement('span');
    el.className = 'chip';
    el.innerHTML = '<i style="background:'+c+'"></i>'+esc(T(k, STAT_EN[k] || k))+' <b>'+stats[k]+'</b>';
    box.appendChild(el);
  });
  if(!n) box.innerHTML = '<span class="chip">' + T('未识别到敏感信息', 'Nothing detected') + '</span>';
  $('totalCnt').textContent = n;
}

function renderList(){
  const list = $('list'); list.innerHTML = '';
  if(!S.findings.length){
    list.innerHTML = '<div class="empty">' + T(
      '没有自动识别到敏感信息。<br>可以点上方「框选手动打码」在页面上手动画框。',
      'Nothing detected automatically.<br>Use “Draw a box” above to mark areas by hand.') + '</div>';
    return;
  }
  const groups = {};
  S.findings.forEach(f=>{ (groups[f.page] = groups[f.page]||[]).push(f); });
  Object.keys(groups).sort((a,b)=>a-b).forEach(pg=>{
    const g = document.createElement('div');
    g.className = 'grp'; g.textContent = T('第 ' + (+pg+1) + ' 页', 'Page ' + (+pg+1));
    list.appendChild(g);
    groups[pg].forEach(f=>{
      const row = document.createElement('div');
      row.className = 'row' + (S.sel.has(f.id)?' on':'');
      row.dataset.id = f.id;
      row.innerHTML = '<input type="checkbox" '+(S.sel.has(f.id)?'checked':'')+'>'
        + '<span class="badge" style="color:'+(TYPE_COLOR[f.type]||'#555')+';background='+
          (TYPE_COLOR[f.type]||'#555')+'1a">'+esc(labelOf(f))+'</span>'
        + '<span class="mono">'+esc(f.mask)+'</span>'
        + (f.suspect ? '<span class="sus">' + T('疑似', 'maybe') + '</span>' : '');
      row.querySelector('input').addEventListener('click', ev=>{
        ev.stopPropagation(); toggle(f.id, ev.target.checked);
      });
      row.addEventListener('click', ()=>{ focusFinding(f); });
      list.appendChild(row);
    });
  });
}

function focusFinding(f){
  S.page = f.page; S.hi = f.id;
  if(!S.sel.has(f.id)){ S.sel.add(f.id); renderList(); syncBar(); }
  refreshPreview();
}
function toggle(id, on){
  if(on) S.sel.add(id); else S.sel.delete(id);
  const row = document.querySelector('.row[data-id="'+id+'"]');
  if(row) row.classList.toggle('on', on);
  syncBar(); refreshPreview();
}
function syncBar(){
  $('selCount').textContent = S.sel.size;
  $('goBtn').disabled = S.sel.size === 0;
  const cnt = {};
  S.findings.forEach(f=>{ cnt[f.page] = (cnt[f.page]||0) + 1; });
  let info = (S.page+1) + ' / ' + S.pages.length;
  if (S.scanned.indexOf(S.page) >= 0) info += (S.ocrPages||[]).indexOf(S.page)>=0 ? T(' · OCR 已识别', ' · OCR read') : T(' · 无文字层', ' · no text layer');
  else info += T(' · 本页 ' + (cnt[S.page]||0) + ' 处', ' · ' + (cnt[S.page]||0) + ' here');
  $('pgNum').textContent = info;
  $('prevPage').disabled = S.page <= 0;
  $('nextPage').disabled = S.page >= S.pages.length-1;
  $('zoomTxt').textContent = Math.round(S.zoom*100) + '%';
}

function refreshPreview(){
  const img = $('pageImg');
  const q = new URLSearchParams({doc:S.docId, page:S.page, zoom:S.zoom,
    sel:[...S.sel].join(','), mask:S.mask?'1':'0', hi:S.hi||'', t:Date.now()});
  const er = (S.erasers[S.page] || []).map(r=>r.join(',')).join(';');
  if(er) q.set('er', er);
  img.src = '/api/preview?' + q.toString();
  syncBar();
}

/* ---------- 事件 ---------- */
$('pickBtn').addEventListener('click', ()=>$('fileInput').click());
$('dropCard').addEventListener('click', e=>{ if(e.target.id!=='pickBtn') $('fileInput').click(); });
$('fileInput').addEventListener('change', e=>{ uploadFile(e.target.files[0]); e.target.value=''; });
['dragenter','dragover'].forEach(ev=>document.addEventListener(ev, e=>{
  e.preventDefault(); $('dropCard').classList.add('over');
}));
['dragleave','drop'].forEach(ev=>document.addEventListener(ev, e=>{
  e.preventDefault();
  if(ev==='dragleave' && e.relatedTarget) return;
  $('dropCard').classList.remove('over');
}));
document.addEventListener('drop', e=>{
  e.preventDefault();
  const f = e.dataTransfer.files && e.dataTransfer.files[0];
  if(f) uploadFile(f);
});
$('reupload').addEventListener('click', ()=>{ resetToDrop(); });
$('backBtn').addEventListener('click', ()=>{ resetToDrop(); });
function resetToDrop(){
  $('workView').hidden = true; $('actionBar').hidden = true; $('dropView').hidden = false;
  $('pageImg').src = ''; $('fileInput').click();
}
$('selAll').addEventListener('click', ()=>{
  S.findings.forEach(f=>S.sel.add(f.id)); renderList(); syncBar(); refreshPreview();
});
$('selNone').addEventListener('click', ()=>{
  S.sel.clear(); renderList(); syncBar(); refreshPreview();
});
$('prevPage').addEventListener('click', ()=>{ if(S.page>0){S.page--; S.hi=null; refreshPreview();} });
$('nextPage').addEventListener('click', ()=>{
  if(S.page < S.pages.length-1){ S.page++; S.hi=null; refreshPreview(); }
});
$('zoomIn').addEventListener('click', ()=>{ S.zoom = Math.min(3, +(S.zoom+0.2).toFixed(2)); refreshPreview(); });
$('zoomOut').addEventListener('click', ()=>{ S.zoom = Math.max(0.6, +(S.zoom-0.2).toFixed(2)); refreshPreview(); });

/* 缩放：Ctrl+滚轮，或笔记本触摸板双指捏合（浏览器会把它报成 ctrl+wheel）。
   普通滚轮不拦，仍然让页面正常滚动。 */
$('canvasWrap').addEventListener('wheel', e=>{
  if(!e.ctrlKey) return;
  e.preventDefault();
  const step = e.deltaY < 0 ? 0.1 : -0.1;
  const next = Math.min(3, Math.max(0.6, +(S.zoom + step).toFixed(2)));
  if(next === S.zoom) return;
  S.zoom = next;
  refreshPreview();
}, {passive:false});

/* 平移：放大后按住右键（或中键）拖动。左键始终留给画框，不抢主功能。 */
let panning = null;
$('canvasWrap').addEventListener('mousedown', e=>{
  if(e.button !== 2 && e.button !== 1) return;
  const w = $('canvasWrap');
  if(!$('pageImg').src) return;
  e.preventDefault();
  panning = {x:e.clientX, y:e.clientY, l:w.scrollLeft, t:w.scrollTop};
  w.style.cursor = 'grabbing';
});
$('canvasWrap').addEventListener('contextmenu', e=>{ if(panning || S.zoom > 1.01) e.preventDefault(); });
window.addEventListener('mousemove', e=>{
  if(!panning) return;
  const w = $('canvasWrap');
  w.scrollLeft = panning.l - (e.clientX - panning.x);
  w.scrollTop  = panning.t - (e.clientY - panning.y);
});
window.addEventListener('mouseup', e=>{
  if(e.button !== 2 && e.button !== 1) return;
  if(panning){ panning = null; $('canvasWrap').style.cursor = ''; }
});
$('maskPreview').addEventListener('change', e=>{ S.mask = e.target.checked; refreshPreview(); });
function setMode(m){
  if(S.mode === m){ S.mode='pan'; S.drawing=false; }
  else { S.mode=m; S.drawing=true; }
  $('drawBtn').classList.toggle('active', S.mode==='draw');
  $('eraseBtn').classList.toggle('active', S.mode==='erase');
  $('canvasWrap').classList.toggle('draw', S.drawing);
  if(S.mode==='draw') toast(T('手动框选：拖动框出要打码的区域，放大镜帮你对准', 'Box: drag to mark an area; the loupe helps you aim'));
  if(S.mode==='erase') toast(T('橡皮擦：拖动只擦掉误框的一小块，旁边该打的内容不动', 'Eraser: drag to restore just one small spot; nearby masks stay'));
}
$('drawBtn').addEventListener('click', ()=>setMode('draw'));
$('eraseBtn').addEventListener('click', ()=>setMode('erase'));

/* 双击方框：取消 / 恢复这一处打码（自动识别的框和手动框都支持） */
$('canvasWrap').addEventListener('dblclick', async e=>{
  const img = $('pageImg');
  if(!img || !img.src) return;
  if(S.mode==='erase'){
    const es = S.erasers[S.page] || [];
    if(!es.length) return;
    es.pop(); refreshPreview();
    try{ await api('/api/erase/undo', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({doc:S.docId, page:S.page})}); }catch(_err){}
    toast(T('已撤销最后一笔擦除', 'Last erase undone'));
    return;
  }
  if(!S.findings.length) return;
  const r = img.getBoundingClientRect();
  if(e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) return;
  const x = (e.clientX - r.left) / S.zoom;
  const y = (e.clientY - r.top) / S.zoom;
  const pad = 6 / S.zoom;               // 小框也点得中
  let hit = null;
  for(let i = S.findings.length - 1; i >= 0; i--){   // 从上往下找，后画的优先
    const f = S.findings[i];
    if(f.page !== S.page) continue;
    const b = f.rect;
    if(x >= b[0]-pad && x <= b[2]+pad && y >= b[1]-pad && y <= b[3]+pad){ hit = f; break; }
  }
  if(!hit) return;
  e.preventDefault();
  const wasOn = S.sel.has(hit.id);
  if(wasOn) S.sel.delete(hit.id); else S.sel.add(hit.id);
  S.hi = wasOn ? null : hit.id;
  renderList(); syncBar(); refreshPreview();
  toast((wasOn ? T('已取消这处打码：', 'Mask removed: ') : T('已恢复这处打码：', 'Mask restored: ')) + labelOf(hit));
});

/* 手动框选 / 橡皮擦：共用拖动与放大镜 */
let band=null, startPt=null, loupe=null;
function updateLoupe(e){
  const img = $('pageImg'); if(!img.src) return;
  if(!loupe){ loupe=document.createElement('div'); loupe.className='loupe'; document.body.appendChild(loupe); }
  const r = img.getBoundingClientRect();
  const z = 3, size = 120;
  loupe.style.backgroundImage = 'url("' + img.src + '")';
  loupe.style.backgroundSize = Math.round(r.width*z)+'px '+Math.round(r.height*z)+'px';
  loupe.style.backgroundPosition = (-Math.round((e.clientX-r.left)*z-size/2))+'px '+
                                   (-Math.round((e.clientY-r.top)*z-size/2))+'px';
  loupe.style.left = Math.min(window.innerWidth-130, e.clientX+16)+'px';
  loupe.style.top  = Math.max(4, e.clientY-140)+'px';
  // 镜里同步画出正在拉的那条虚线框。坐标换算和 backgroundPosition 同一套：
  // 内容点相对 img 的偏移 × z，再减去「镜心对准的指下点」，最后挪到圆心。
  let box = loupe.querySelector('.lbox');
  if(!box){ box = document.createElement('div'); box.className = 'lbox'; loupe.appendChild(box); }
  if(band){
    const br = band.getBoundingClientRect();
    const bw = br.width * z, bh = br.height * z;
    box.className = 'lbox' + (S.mode === 'erase' ? ' erase' : '');
    box.style.display = (bw < 1 || bh < 1) ? 'none' : 'block';
    box.style.left = ((br.left - e.clientX) * z + size/2) + 'px';
    box.style.top  = ((br.top  - e.clientY) * z + size/2) + 'px';
    box.style.width = bw + 'px';
    box.style.height = bh + 'px';
  } else {
    box.style.display = 'none';
  }
}
function hideLoupe(){ if(loupe){ loupe.remove(); loupe=null; } }
$('canvasWrap').addEventListener('mousedown', e=>{
  if(!S.drawing || e.button!==0) return;
  const img = $('pageImg'); if(!img.src) return;
  const r = img.getBoundingClientRect();
  if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom) return;
  e.preventDefault();
  startPt = {x:e.clientX, y:e.clientY};
  band = document.createElement('div');
  band.className = 'band' + (S.mode==='erase' ? ' erase' : '');
  document.body.appendChild(band);
  drawBand(startPt, startPt); updateLoupe(e);
});
$('canvasWrap').addEventListener('mousemove', e=>{
  if(band && startPt){ drawBand(startPt, {x:e.clientX, y:e.clientY}); updateLoupe(e); }
});
window.addEventListener('mouseup', async e=>{
  hideLoupe();
  if(!band || !startPt) return;
  const end = {x:e.clientX, y:e.clientY};
  band.remove(); band=null;
  const p0 = startPt; startPt=null;
  const img = $('pageImg'); const r = img.getBoundingClientRect();
  const x0 = Math.min(p0.x,end.x), y0 = Math.min(p0.y,end.y);
  const x1 = Math.max(p0.x,end.x), y1 = Math.max(p0.y,end.y);
  if(x1-x0 < 4 || y1-y0 < 4) return;
  const rect = [ (x0-r.left)/S.zoom, (y0-r.top)/S.zoom, (x1-r.left)/S.zoom, (y1-r.top)/S.zoom ];
  try{
    if(S.mode==='erase'){
      await api('/api/erase', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({doc:S.docId, page:S.page, rect:rect})});
      (S.erasers[S.page] = S.erasers[S.page] || []).push(rect);
      refreshPreview(); toast(T('已擦掉这一小块，旁边的打码还在', 'Spot restored; nearby masks kept'));
    }else{
      const res = await api('/api/manual', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({doc:S.docId, page:S.page, rect:rect})});
      S.findings.push({id:res.id, type:'manual', label:T('手动框选', 'Manual box'),
        mask:T('手动框选区域', 'Manual area'), page:S.page, rect:rect, note:'manual'});
      S.sel.add(res.id); S.hi = res.id;
      renderList(); syncBar(); refreshPreview(); toast(T('已添加手动打码区域', 'Manual mask added'));
    }
  }catch(err){ toast(err.message, true); }
});
function drawBand(a,b){
  const x=Math.min(a.x,b.x), y=Math.min(a.y,b.y), w=Math.abs(a.x-b.x), h=Math.abs(a.y-b.y);
  band.style.left=x+'px'; band.style.top=y+'px'; band.style.width=w+'px'; band.style.height=h+'px';
}

/* ---------- 设置 / 保存位置 ---------- */
let CFG = {saveDir:'', rememberDir:true, noAsk:false, defaultDir:'', effectiveDir:'',
           lang:'zh', autoCheck:true, updateSource:'auto', resolvedSource:'gitee'};

async function loadCfg(){
  try{
    const q = S.docId ? ('?doc=' + encodeURIComponent(S.docId)) : '';
    CFG = await api('/api/settings' + q);
  }catch(e){}
  return CFG;
}

/* 更新方式 / 更新源：点一下立刻存盘，不用按「保存」 */
function syncUpdSeg(){
  const mode = (CFG.autoCheck === false) ? 'manual' : 'auto';
  document.querySelectorAll('#updModeSeg .seg-btn').forEach(b=>{
    b.classList.toggle('on', b.dataset.updmode === mode);
  });
  let src = CFG.updateSource;
  if (src !== 'gitee' && src !== 'github') src = CFG.resolvedSource || 'gitee';
  document.querySelectorAll('#updSrcSeg .seg-btn').forEach(b=>{
    b.classList.toggle('on', b.dataset.updsrc === src);
  });
}
async function saveUpdSeg(patch){
  syncUpdSeg();
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(patch)});
    await loadCfg();
    toast(T('设置已保存', 'Settings saved'));
  }catch(e){ toast(e.message, true); }
  syncUpdSeg();
  if (UPD) renderUpdate();
}
$('updModeSeg').addEventListener('click', e=>{
  const b = e.target.closest('.seg-btn');
  if(!b) return;
  const auto = b.dataset.updmode !== 'manual';
  if (auto === (CFG.autoCheck !== false)) return;
  CFG.autoCheck = auto;
  saveUpdSeg({autoCheck: auto});
});
$('updSrcSeg').addEventListener('click', e=>{
  const b = e.target.closest('.seg-btn');
  if(!b) return;
  if (b.dataset.updsrc === CFG.updateSource) return;
  CFG.updateSource = b.dataset.updsrc;
  saveUpdSeg({updateSource: b.dataset.updsrc});
});

async function pickDir(inputId){
  const cur = ($(inputId).value || '').trim();
  try{
    const r = await api('/api/pickdir', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({initial:cur})});
    if(r.path){ $(inputId).value = r.path; }
    else if(r.status === 'error'){
      toast(T('打不开系统的选择框，可以直接把文件夹路径粘贴到输入框里', 'Could not open the folder picker — paste the path into the box instead'), true);
    }
  }catch(e){ toast(e.message, true); }
}

async function saveCopyAs(token, initial){
  try{
    const r = await api('/api/pickdir', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({initial:initial || ''})});
    if(r.status === 'cancel') return;
    if(!r.path) return toast(T('打不开系统的选择框', 'Could not open the folder picker'), true);
    const res = await api('/api/copyout', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token:token, dir:r.path})});
    toast(T('已另存到 ', 'Saved a copy to ') + res.path);
  }catch(e){ toast(e.message, true); }
}

async function doRender(opt){
  if(!S.sel.size) return;
  jobShow(T('正在生成打码 PDF…', 'Generating masked PDF…'));
  try{
    const body = {doc:S.docId, ids:[...S.sel], erasers:S.erasers};
    if(opt){ body.dir = opt.dir || ''; body.remember = !!opt.remember; body.noAsk = !!opt.noAsk; }
    const d = await api('/api/render', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    jobHide();
    if(opt) await loadCfg();
    showResult(d);
  }catch(e){ jobHide(); toast(e.message, true); }
}

/* 生成：先决定要不要问保存位置 */
$('goBtn').addEventListener('click', async ()=>{
  if(!S.sel.size) return;
  await loadCfg();
  if(CFG.noAsk && CFG.effectiveDir){
    doRender({dir:CFG.effectiveDir, remember:true, noAsk:true});
    return;
  }
  const def = CFG.saveDir || S.outDir || CFG.defaultDir || '';
  $('savePath').value = def;
  $('optRemember').checked = CFG.rememberDir !== false;
  $('optNoAsk').checked = !!CFG.noAsk;
  $('saveMask').hidden = false;
  $('savePath').focus();
});

$('saveBrowse').addEventListener('click', ()=>pickDir('savePath'));
$('saveCancel').addEventListener('click', ()=>{ $('saveMask').hidden = true; });
$('saveMask').addEventListener('click', e=>{ if(e.target === $('saveMask')) $('saveMask').hidden = true; });
$('saveOk').addEventListener('click', async ()=>{
  const dir = ($('savePath').value || '').trim();
  if(!dir) return toast(T('请先选一个保存文件夹', 'Pick a folder first'), true);
  const remember = $('optRemember').checked, noAsk = $('optNoAsk').checked;
  $('saveMask').hidden = true;
  doRender({dir:dir, remember:remember, noAsk:noAsk});
});

/* 设置面板 */
$('setBtn').addEventListener('click', async ()=>{
  await loadCfg();
  $('setPath').value = CFG.saveDir || '';
  $('setAsk').checked = !CFG.noAsk;
  $('setMask').hidden = false;
  applyLang();                 // 顺带把语言按钮的选中态同步一下
  syncUpdSeg();
  if (UPD) renderUpdate();
});
$('setBrowse').addEventListener('click', ()=>pickDir('setPath'));
$('setMask').addEventListener('click', e=>{ if(e.target === $('setMask')) $('setMask').hidden = true; });
$('setOk').addEventListener('click', async ()=>{
  const v = ($('setPath').value || '').trim();
  const ask = $('setAsk').checked;
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({saveDir:v, noAsk:!ask})});
    await loadCfg();
    syncUpdSeg();
    $('setMask').hidden = true;
    toast(T('设置已保存', 'Settings saved'));
  }catch(e){ toast(e.message, true); }
});
$('setReset').addEventListener('click', async ()=>{
  $('setPath').value = ''; $('setAsk').checked = true;
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({saveDir:'', noAsk:false, autoCheck:true, updateSource:'auto'})});
    await loadCfg(); syncUpdSeg();
    toast(T('已恢复默认设置', 'Defaults restored'));
  }catch(e){ toast(e.message, true); }
});

/* ---------- 界面语言 / 检查更新 ---------- */
$('langSeg').addEventListener('click', async e=>{
  const b = e.target.closest('.seg-btn');
  if(!b) return;
  LANG = b.dataset.lang === 'en' ? 'en' : 'zh';
  applyLang();
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({lang:LANG})});
  }catch(err){}
});

let UPD = null;      // {r: 后端返回, opened: 浏览器是否被成功唤起}

/* ---------- 发布正文 → 弹窗里的两段文字 ----------
   后端已经把发布页正文拆好：一句 100 字以内的摘要 + 按 Windows / 安卓
   归类的条目。两个窗口（启动自动检查、设置里手动检查）共用这一套渲染，
   保证用户看到的东西完全一样：
     摘要（顶部一行，极简）
     详细（可滚动，每条前面标 Windows / 安卓 / 两端）
     具体详见 Release 页面 → */
function digestPick(obj){
  const d = obj && obj.digest;
  if(!d) return null;
  // 先按当前界面语言取，那份是空的就退回另一种语言（发布页只有中文时也能显示）
  const pick = o => {
    if(!o) return null;
    const first = o[LANG];
    if(first && (!Array.isArray(first) ? first : first.length)) return first;
    if(o.zh && (!Array.isArray(o.zh) ? o.zh : o.zh.length)) return o.zh;
    if(o.en && (!Array.isArray(o.en) ? o.en : o.en.length)) return o.en;
    return null;
  };
  return {brief:(pick(d.brief) || '').trim(), items: pick(d.notes) || []};
}

function digestNotesHtml(items){
  let html = '';
  for(const it of (items || [])){
    const p = (it.p === 'win' || it.p === 'android') ? it.p : 'both';
    const tag = p === 'win' ? 'Windows'
              : (p === 'android' ? T('安卓', 'Android') : T('两端', 'Both'));
    html += '<div class="note"><div class="note-h"><span class="note-tag ' + p + '">' + tag +
            '</span><b>' + esc(it.t) + '</b></div>';
    if(it.b && it.b.length){
      html += '<div class="note-b">' + esc(it.b.join('\n')) + '</div>';
    }
    html += '</div>';
  }
  return html;
}

function digestOf(obj){
  const p = digestPick(obj);
  if(!p) return null;
  return {brief:p.brief, notes:digestNotesHtml(p.items)};
}

/* prefix = 'upd' 或 'autoUpd'，对应 HTML 里的 Brief / Notes / More / MoreLink 四个 id */
function fillDigest(prefix, r){
  const briefEl = $(prefix + 'Brief'), notesEl = $(prefix + 'Notes');
  const moreEl = $(prefix + 'More'), link = $(prefix + 'MoreLink');
  if(!briefEl || !notesEl || !moreEl) return;
  const dig = digestOf(r);
  briefEl.hidden = !(dig && dig.brief);
  briefEl.textContent = (dig && dig.brief) || '';
  notesEl.hidden = !(dig && dig.notes);
  notesEl.innerHTML = (dig && dig.notes) || '';
  moreEl.hidden = !(dig && (dig.brief || dig.notes));
  if(link){
    link.textContent = T('具体详见 Release 页面 →', 'Full notes on the release page →');
    link.onclick = ()=> openUpdateUrl((r && (r.releasesUrl || r.url)) || '');
  }
}

function clearDigest(prefix){
  ['Brief', 'Notes', 'More'].forEach(k=>{
    const el = $(prefix + k);
    if(el){ el.hidden = true; }
  });
}

/* ---------- 跨版本说明的翻页（v1.4.6.5） ----------
   当前版本落后好几个版本时（例如 1.4.6.2 对着 1.4.6.3、1.4.6.4），弹窗里可以
   逐页翻看每一版的说明。页面顺序是「旧 → 新」，默认停在最后一页（最新版）。

   手势方向刻意做成「相反逻辑」：
     向右滑（手指往右）→ 上一页，也就是**更早**的未更新版本；
     向左滑（手指往左）→ 下一页，也就是**更新**的版本。
   左右两个按钮的方向与手势一致，不会出现「箭头和滑动反着来」。

   翻页只改变「看哪一版的说明」：下载按钮、复制链接、底部那行地址全部取
   r.url（最新版的包），底部固定写明「下载目标：最新版 vX」，翻到旧页时
   按钮文案也不变——避免用户以为自己在下载翻到的那一版。 */
const VP = {};

function vpPages(r){
  return ((r && r.pending) || []).map(p => ({
    ver: p.ver,
    digest: p.digest || null,
    strong: !!p.strong,
    page: p.page || (r && (r.releasesUrl || r.url)) || '',
  }));
}

function vpHide(prefix){
  const box = $(prefix + 'Vp');
  if(box) box.hidden = true;
  delete VP[prefix];
}

function vpRender(prefix){
  const st = VP[prefix];
  if(!st) return;
  const it = st.pages[st.idx];
  const body = $(prefix + 'VpBody');
  if(!body) return;
  const dig = digestOf(it);
  let html = '';
  if(dig && dig.brief) html += '<div class="brief">' + esc(dig.brief) + '</div>';
  if(dig && dig.notes) html += '<div class="notes">' + dig.notes + '</div>';
  if(!html){
    html = '<div class="brief">' + T('这一版没有写更新说明。', 'No notes were written for this version.') + '</div>';
  }
  body.innerHTML = html;

  const n = st.pages.length, i = st.idx;
  const meta = $(prefix + 'VpMeta'), tip = $(prefix + 'VpTip');
  if(meta){
    meta.innerHTML = T('共 <b>' + n + '</b> 个版本未更新（当前 v' + st.curVer + ' → 最新 v' + st.latestVer + '）',
                       n + ' version' + (n > 1 ? 's' : '') + ' behind (v' + st.curVer + ' → v' + st.latestVer + ')');
  }
  if(tip){
    tip.innerHTML = T('正在看 <b>v' + it.ver + '</b> · 右滑看更早，左滑看更新',
                      'Viewing <b>v' + it.ver + '</b> · swipe right for older, left for newer');
  }
  const pos = $(prefix + 'VpPos');
  if(pos) pos.textContent = (i + 1) + ' / ' + n;
  const prev = $(prefix + 'VpPrev'), next = $(prefix + 'VpNext');
  if(prev){
    prev.textContent = T('‹ 更早版本', '‹ Older');
    prev.disabled = (i <= 0);
  }
  if(next){
    next.textContent = T('更新版本 ›', 'Newer ›');
    next.disabled = (i >= n - 1);
  }
  const goal = $(prefix + 'VpGoal');
  if(goal){
    goal.innerHTML = T('下载目标固定为 <b>最新版 v' + st.latestVer + '</b> —— 翻页只换说明，翻到哪一页点下载装的都是最新版。',
                       'Download target is always <b>v' + st.latestVer + '</b> — paging only changes the notes.');
  }
}

function vpStep(prefix, d){
  const st = VP[prefix];
  if(!st) return;
  const nx = Math.max(0, Math.min(st.pages.length - 1, st.idx + d));
  if(nx === st.idx) return;
  st.idx = nx;
  vpRender(prefix);
}

function vpWire(prefix){
  const body = $(prefix + 'VpBody');
  if(!body || body.dataset.wired) return;
  body.dataset.wired = '1';
  let x0 = 0, dx = 0, dragging = false;
  body.addEventListener('pointerdown', e => {
    if(e.button !== undefined && e.button !== 0) return;
    dragging = true; dx = 0; x0 = e.clientX;
    body.classList.add('dragging');
    try{ body.setPointerCapture(e.pointerId); }catch(_){ }
  });
  body.addEventListener('pointermove', e => {
    if(!dragging) return;
    dx = e.clientX - x0;
    body.style.transform = 'translateX(' + Math.max(-70, Math.min(70, dx)) + 'px)';
  });
  const finish = () => {
    if(!dragging) return;
    dragging = false;
    body.classList.remove('dragging');
    body.style.transform = '';
    if(dx >= 60) vpStep(prefix, -1);        // 向右滑 → 上一页（更早）
    else if(dx <= -60) vpStep(prefix, 1);   // 向左滑 → 下一页（更新）
    dx = 0;
  };
  body.addEventListener('pointerup', finish);
  body.addEventListener('pointercancel', finish);
  body.addEventListener('pointerleave', finish);
  const prev = $(prefix + 'VpPrev'), next = $(prefix + 'VpNext');
  if(prev) prev.onclick = ()=> vpStep(prefix, -1);
  if(next) next.onclick = ()=> vpStep(prefix, 1);
}

/* 有多个未更新版本就用翻页，只有一个（或没有）就保持原来的单页渲染 */
function fillUpdateNotes(prefix, r){
  const pages = vpPages(r);
  if(pages.length <= 1){
    vpHide(prefix);
    fillDigest(prefix, r);
    return false;
  }
  ['Brief', 'Notes', 'More'].forEach(k=>{
    const el = $(prefix + k);
    if(el) el.hidden = true;
  });
  const box = $(prefix + 'Vp');
  if(!box){ fillDigest(prefix, r); return false; }
  box.hidden = false;
  VP[prefix] = {pages: pages, idx: pages.length - 1,
                latestVer: r.latest, curVer: r.current};
  vpWire(prefix);
  vpRender(prefix);
  return true;
}

function setHelp(){
  $('updHelp').innerHTML = T(
    '还是打不开？按顺序试：<ol>' +
    '<li><b>查权限</b>：安全软件 / 家长控制有没有拦浏览器；系统「设置 → 网络和 Internet → 代理」是不是还开着；防火墙有没有拦本程序联网。</li>' +
    '<li><b>复制链接</b>，自己粘到浏览器地址栏里打开。</li>' +
    '<li>都不行就<b>截屏这一屏</b>，用微信「提取文字」或相册的文字识别把链接抠出来，手动输入。</li></ol>',
    'Still blocked? Try in order:<ol>' +
    '<li><b>Check permissions</b>: is a security suite or parental control blocking your browser? Is a proxy still on under Settings → Network & Internet → Proxy? Is the firewall blocking this app?</li>' +
    '<li><b>Copy the link</b> and paste it into your browser yourself.</li>' +
    '<li>If that fails, <b>screenshot this window</b> and use text recognition (WeChat “Extract text”, or your photo app) to pull the link out by hand.</li></ol>'
  );
}

function renderUpdate(){
  if(!UPD) return;
  const r = UPD.r;
  const box = $('updBox'), txt = $('updText');
  const urlBox = $('updUrl'), acts = $('updActions'), help = $('updHelp');
  box.hidden = false;
  urlBox.hidden = true; acts.hidden = true; help.hidden = true;
  clearDigest('upd');
  vpHide('upd');
  const detail = $('updDetail');
  detail.hidden = true; detail.textContent = '';
  if(!r || !r.ok){
    box.className = 'upd-box fail';
    txt.textContent = T('检查失败：', 'Check failed: ') +
      ((r && r.error) || T('网络不通。', 'network error.')) +
      T(' 可以直接去发布页手动看看，也可以按下面的步骤排查。',
        ' You can also open the releases page yourself, or work through the steps below.');
    if(r && r.detail){ detail.hidden = false; detail.textContent = r.detail; }
    urlBox.textContent = (r && (r.url || r.releasesUrl)) || '';
    urlBox.hidden = !urlBox.textContent;
    acts.hidden = false; help.hidden = false;
    setHelp();
    return;
  }
  $('latestVer').textContent = 'v' + r.latest;
  // 从哪个源读到的：自动换源时说清原因，免得用户以为「默认 Gitee 怎么跑去 GitHub」
  const srcLine = !r.channel ? ''
    : (r.fallbackFrom
        ? T('（' + r.fallbackFrom + ' 这次没连上，已经自动改用 ' + r.channel + '）',
            ' (' + r.fallbackFrom + ' could not be reached, so ' + r.channel + ' was used)')
        : T('（本次从 ' + r.channel + ' 读取）', ' (read from ' + r.channel + ')'));
  if(!r.hasUpdate){
    box.className = 'upd-box ok';
    txt.textContent = T('已是最新版本（v' + r.current + '）。',
                        'You are on the latest version (v' + r.current + ').') + srcLine;
    return;
  }
  box.className = 'upd-box new';
  txt.textContent = UPD.opened
    ? T('发现新版本 v' + r.latest + '（当前 v' + r.current + '），已经让浏览器去下载了。',
        'New version v' + r.latest + ' is out (you have v' + r.current + '). Your browser is downloading it now.')
    : T('发现新版本 v' + r.latest + '（当前 v' + r.current + '），但没能自动打开浏览器，点下面的按钮再试一次。',
        'New version v' + r.latest + ' is out (you have v' + r.current + '), but the browser did not open — try the button below.');
  txt.textContent += srcLine;
  // 跨版本：比当前新的版本不止一个时，明确告诉用户「还有几版没更新」
  const pend = r.pending || [];
  if(pend.length > 1){
    txt.textContent += T(
      ' 你还有 ' + pend.length + ' 个版本没更新（v' + pend[0].ver + ' 等），可以在下面左右滑动逐页看说明。',
      ' You are ' + pend.length + ' versions behind (v' + pend[0].ver + ' and others) — swipe below to read each one.');
  }
  // 有发布正文就给摘要和详细，没有就保持原来的样子（不影响任何老版本）
  fillUpdateNotes('upd', r);
  // 按钮写明「装的是哪一版」，翻页不影响它
  $('updOpen').textContent = T('用浏览器下载最新版 v' + r.latest,
                               'Download v' + r.latest + ' in browser');
  urlBox.textContent = r.url || '';
  urlBox.hidden = !urlBox.textContent;
  acts.hidden = false; help.hidden = false;
  setHelp();
}

async function openUpdateUrl(url){
  if(!url) return false;
  try{
    await api('/api/openurl', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url:url})});
    return true;
  }catch(err){
    toast(T('打不开默认浏览器：', 'Could not launch a browser: ') + err.message, true);
    return false;
  }
}

$('checkBtn').addEventListener('click', async ()=>{
  const btn = $('checkBtn');
  btn.disabled = true;
  btn.textContent = T('检查中…', 'Checking…');
  $('updBox').hidden = false;
  $('updBox').className = 'upd-box';
  // 这里必须写实际要连的那个源：以前写死「正在连接 GitHub」，而默认源是
  // Gitee，于是出现「先说 GitHub，最后又说本次从 Gitee 读取」的自相矛盾。
  const _srcName = (CFG && CFG.resolvedSource === 'github') ? 'GitHub' : 'Gitee';
  $('updText').textContent = T('正在连接 ' + _srcName + ' 查询最新版本…',
                               'Contacting ' + _srcName + ' for the latest release…');
  $('updUrl').hidden = true; $('updActions').hidden = true; $('updHelp').hidden = true;

  let r;
  try{ r = await api('/api/check_update'); }
  catch(e){ r = {ok:false, error:e.message}; }
  let opened = false;
  if(r && r.ok && r.hasUpdate){
    // 有新版本才跳浏览器，直接指向安装包
    opened = await openUpdateUrl(r.url);
  }
  UPD = {r:r, opened:opened};
  btn.disabled = false;
  btn.textContent = T('检查更新', 'Check for updates');
  renderUpdate();
});

$('updOpen').addEventListener('click', async ()=>{
  const url = (UPD && UPD.r && (UPD.r.url || UPD.r.releasesUrl)) || '';
  const ok = await openUpdateUrl(url);
  if(ok && UPD){ UPD.opened = true; renderUpdate(); }
});
$('updCopy').addEventListener('click', ()=>{
  const url = (UPD && UPD.r && (UPD.r.url || UPD.r.releasesUrl)) || '';
  if(!url) return;
  copyText(url, T('已复制下载链接：', 'Download link copied: '));
});

function showResult(d){
  const stats = Object.keys(d.stats).map(k=>T(k, STAT_EN[k]||k)+' '+d.stats[k]).join(' · ');
  const wrap = document.createElement('div');
  wrap.className = 'result';
  wrap.innerHTML = '<div class="card">'
    + '<div class="ok-ico"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5 5L20 6.5"/></svg></div>'
    + '<h3>' + T('打码完成', 'Masking done') + '</h3>'
    + '<div style="color:var(--ink2);font-size:13px">' +
      T('共处理 ' + d.count + ' 处：', 'Masked ' + d.count + ' items: ') + esc(stats) + '</div>'
    + '<div style="color:var(--ink3);font-size:12px;margin-top:2px">' + T(
      '全文 ' + (d.pages||'-') + ' 页，其中 ' + (d.hitPages||'-') + ' 页有打码，其余页面原样保留',
      (d.pages||'-') + ' pages in total, ' + (d.hitPages||'-') + ' of them masked, the rest untouched') + '</div>'
    + '<div class="path">' + esc(d.path) + '</div>'
    + '<div class="res-actions">'
    + '<button class="btn primary" id="rOpen">' + T('打开 PDF', 'Open PDF') + '</button>'
    + '<button class="btn" id="rFolder">' + T('打开所在文件夹', 'Open containing folder') + '</button>'
    + '<button class="btn" id="rDl">' + T('另存到别处…', 'Save a copy…') + '</button>'
    + '<button class="btn ghost" id="rClose">' + T('关闭', 'Close') + '</button>'
    + '</div></div>';
  document.body.appendChild(wrap);
  wrap.querySelector('#rClose').onclick = ()=>wrap.remove();
  wrap.querySelector('#rOpen').onclick = ()=>post('/api/openfile', {token:d.token});
  wrap.querySelector('#rFolder').onclick = ()=>post('/api/showfolder', {token:d.token});
  wrap.querySelector('#rDl').onclick = ()=>saveCopyAs(d.token, d.dir);
  async function post(p, body){
    try{ await api(p, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); }
    catch(e){ toast(e.message, true); }
  }
}

/* ---------- 启动自动检查更新（v1.4.2） ----------
   和「设置 → 检查更新」共用同一个 /api/check_update，只是把结果做成一个可以先关掉的窗口：
   · 断网 / 超时 / 已是最新 —— 一律不弹，直接进主程序；
   · 1.2 秒还没结果 —— 弹「正在检查」，右上角能关，随时跳过；
   · 超过 12 秒 —— 当作卡住，给一个「进入主程序」的兜底；
   · 发现新版本 —— 自动用默认浏览器打开发布页，同时给「用浏览器下载 / 复制链接」两条路；
   · 更新级别只有两档：建议更新 / 强烈建议更新 —— 都只是建议，永远留着关闭；
     用户真要点「暂不更新」，先劝一次挽留，点第二次就放行，不再纠缠。 */
const AUTO = {strong:false, skipped:false, shown:false, state:'', pled:false, opened:false, r:null};

function autoUpdHide(){
  const m = $('autoUpdMask');
  if (m) m.hidden = true;
  AUTO.state = '';
}

function autoUpdOpen(){
  const m = $('autoUpdMask');
  if (!m) return false;
  m.hidden = false;
  AUTO.shown = true;
  $('autoUpdBadge').hidden = true;
  $('autoUpdBadge').className = 'au-badge';
  $('autoUpdSpin').hidden = true;
  vpHide('autoUpd');
  $('autoUpdUrl').hidden = true;
  $('autoUpdUrl').textContent = '';
  $('autoUpdActs').innerHTML = '';
  $('autoUpdActs').hidden = true;
  $('autoUpdClose').hidden = false;
  clearDigest('autoUpd');
  return true;
}

function autoUpdBtn(label, primary, fn){
  const b = document.createElement('button');
  b.className = 'btn' + (primary ? ' primary' : '');
  b.textContent = label;
  b.onclick = fn;
  $('autoUpdActs').appendChild(b);
  $('autoUpdActs').hidden = false;
  return b;
}

/* 检查中：慢的时候才出现，给一个「跳过」 */
function autoUpdChecking(){
  if (!autoUpdOpen()) return;
  AUTO.state = 'check';
  // 同上：说实际要连的那个源，别把 GitHub / Gitee 写死
  const src = (CFG && CFG.resolvedSource === 'github') ? 'GitHub' : 'Gitee';
  $('autoUpdTitle').textContent = T('正在检查更新', 'Checking for updates');
  $('autoUpdText').textContent = T(
    '正在向 ' + src + ' 读一次版本号，不传任何文件。网络慢的话可以直接关掉，不影响使用。',
    'Reading the latest version number from ' + src + '. No files are sent. If the network is slow, just close this.');
  $('autoUpdSpinText').textContent = T('连接 ' + src + '…', 'Contacting ' + src + '…');
  $('autoUpdSpin').hidden = false;
  autoUpdBtn(T('跳过，先进入', 'Skip and continue'), false, ()=>{
    AUTO.skipped = true;
    autoUpdHide();
  });
}

/* 卡住：超时兜底，必须能一键进主程序 */
function autoUpdStuck(){
  if (!autoUpdOpen()) return;
  AUTO.state = 'stuck';
  AUTO.skipped = true;
  $('autoUpdTitle').textContent = T('检查更新没有回应', 'Update check timed out');
  $('autoUpdText').textContent = T(
    '网络似乎不通，这次检查已经跳过，可以直接使用。想再试一次：设置 → 版本与更新 → 检查更新。',
    'The network looks unreachable, so this check was skipped — you can go ahead. To retry later: Settings → Version & updates → Check.');
  autoUpdBtn(T('重新检查', 'Try again'), false, ()=>{ autoUpdHide(); autoCheckUpdates(); });
  autoUpdBtn(T('进入主程序', 'Continue'), true, autoUpdHide);
}

/* 有新版：两档都只是建议，关闭按钮永远在 */
function autoUpdNew(r, opened){
  AUTO.r = r;
  AUTO.strong = !!r.strong;
  if (typeof opened === 'boolean') AUTO.opened = opened;
  if (!autoUpdOpen()) return;
  AUTO.state = 'new';
  const strong = AUTO.strong;
  const badge = $('autoUpdBadge');
  badge.hidden = false;
  badge.className = 'au-badge ' + (strong ? 'strong' : 'sug');
  badge.textContent = strong
    ? T('强烈建议更新', 'Strongly suggested')
    : T('建议更新', 'Suggested');
  $('autoUpdTitle').textContent = (strong ? T('强烈建议更新到 ', 'Strongly suggested: ') : T('发现新版本 ', 'New version ')) + 'v' + r.latest;
  // 发布页写了「一句话」就用它当正文，不再堆模板话术；没写就退回原来的通用说明
  const dig = digestOf(r);
  const hasDigest = !!(dig && (dig.brief || dig.notes));
  $('autoUpdText').textContent = hasDigest
    ? T('你当前是 v' + r.current + '。这一版的关键改动就是下面这几条，完整说明在 Release 页面。',
        'You are on v' + r.current + '. The key changes are listed below; the full notes are on the release page.')
    : (strong
      ? T('你当前是 v' + r.current + '。这一版修了一直在影响使用的问题，强烈建议尽快换上——更新只要一分钟，原来的功能都在，文件也始终留在你的电脑里。',
          'You are on v' + r.current + '. This build fixes problems that keep getting in the way, so updating is strongly suggested — it takes a minute, everything keeps working, and your files never leave your computer.')
      : T('你当前是 v' + r.current + '。新版修了几个已知问题，也更稳——不更新也能继续用，但建议尽快换上。',
          'You are on v' + r.current + '. The new build fixes a few known problems and is more reliable — you can keep using this version, but updating is worth it.'));
  const pend2 = r.pending || [];
  if(pend2.length > 1){
    $('autoUpdText').textContent += T(
      ' 另外你还有 ' + pend2.length + ' 个版本没更新（v' + pend2[0].ver + ' 等），下面可以左右滑动逐页看每一版的说明。',
      ' You are ' + pend2.length + ' versions behind (v' + pend2[0].ver + ' and others) — swipe below to read each one.');
  }
  fillUpdateNotes('autoUpd', r);
  $('autoUpdUrl').hidden = false;
  $('autoUpdUrl').textContent = r.url || r.releasesUrl || '';
  autoUpdBtn(T('暂不更新', 'Not now'), false, autoUpdAskLater);
  autoUpdBtn(T('复制链接', 'Copy link'), false, ()=>{
    const url = r.url || r.releasesUrl || '';
    if (url) copyText(url, T('已复制下载链接：', 'Download link copied: '));
  });
  autoUpdBtn(T('用浏览器下载最新版 v' + r.latest, 'Download v' + r.latest + ' in browser'), true, async ()=>{
    const ok = await openUpdateUrl(r.url || r.releasesUrl);
    if (!ok){
      toast(T('打不开默认浏览器，可以复制链接自己粘到浏览器里。',
              'Could not launch a browser — copy the link and paste it yourself.'), true);
    }
  });
  if (!AUTO.opened){
    // 自动跳浏览器失败时，直接把话说清楚，免得用户以为没反应
    $('autoUpdText').textContent = T(
      '你当前是 v' + r.current + '，最新是 v' + r.latest + '，但没能自动打开浏览器，点下面的按钮再试一次。',
      'You have v' + r.current + ' and v' + r.latest + ' is out, but the browser did not open — try the button below.');
  }
}

/* 点「暂不更新」或右上角 ×：先劝一次挽留；已经劝过就真的放行，不再纠缠 */
function autoUpdAskLater(){
  const r = AUTO.r;
  if (!r){ autoUpdHide(); return; }
  if (AUTO.pled){ AUTO.skipped = true; autoUpdHide(); return; }
  AUTO.pled = true;
  if (!autoUpdOpen()) return;
  AUTO.state = 'plea';
  const strong = AUTO.strong;
  clearDigest('autoUpd');
  $('autoUpdTitle').textContent = strong
    ? T('再看一眼，好吗？', 'One more look?')
    : T('确定先不更新吗？', 'Skip this update?');
  $('autoUpdText').textContent = strong
    ? T('这一版修的是一上手就会碰到的问题——旧版里那些反复出错、只能一遍遍重来的地方，新版已经处理好了。花一分钟换上，往后能省下不少时间。\n\n当然，换不换还是你说了算：点「我还是要用旧版」就能继续用，下次打开只会再提醒你一次而已。',
        'This release fixes the things you run into as soon as you start — the repeated failures and retries are gone. One minute now saves a lot of hassle later.\n\nIt is still your call: click “Keep the old version” to carry on. You will just be reminded once next time.')
    : T('不更新也能照常用，只是新版顺手修了几个小毛病，用起来更稳。\n\n下次打开还会再提醒一次，到时候想换也来得及。',
        'The app works fine without it — the new build just tidies up a few rough edges and is steadier.\n\nYou will be reminded once more next time, so you can always switch later.');
  autoUpdBtn(strong
      ? T('我还是要用旧版', "I'll stay on the old version")
      : T('先这样，下次再说', 'Skip for now'),
    false, ()=>{ AUTO.skipped = true; autoUpdHide(); });
  autoUpdBtn(T('好，现在更新', 'Okay, update now'), true, async ()=>{
    const ok = await openUpdateUrl(r.url || r.releasesUrl);
    autoUpdNew(r, ok);
  });
}

async function autoCheckUpdates(){
  if (!$('autoUpdMask')) return;
  if (CFG && CFG.autoCheck === false) return;   // 用户选了手动检查，就不联网
  AUTO.skipped = false;
  AUTO.pled = false;
  let settled = false;
  const slow = setTimeout(()=>{ if (!settled) autoUpdChecking(); }, 1200);
  let r = null;
  try{
    r = await Promise.race([
      api('/api/check_update'),
      new Promise(res => setTimeout(()=> res({__timeout:true}), 12000))
    ]);
  }catch(e){ r = null; }
  settled = true;
  clearTimeout(slow);
  if (r && r.__timeout){ autoUpdStuck(); return; }
  // 断网 / 没有包 / 已是最新：静默，什么都不提示
  if (!r || !r.ok || !r.hasUpdate){ autoUpdHide(); return; }
  if (AUTO.skipped){ autoUpdHide(); return; }
  const opened = await openUpdateUrl(r.url || r.releasesUrl);
  autoUpdNew(r, opened);
}

/* 启动：先按上次保存的语言刷新整页文案，再决定要不要打开命令行带来的文件 */
(async ()=>{
  try{
    await loadCfg();
    if(CFG && CFG.lang === 'en') LANG = 'en';
  }catch(e){}
  applyLang();
  if (BOOT) openPath(BOOT);
  autoCheckUpdates();
})();

setInterval(()=>{ fetch('/api/ping').catch(()=>{}); }, 60000);

const aboutMask = $('aboutMask');
if (aboutMask) {
  $('aboutBtn').onclick = ()=> aboutMask.hidden = false;
  $('aboutOk').onclick = ()=> aboutMask.hidden = true;
  // 保存赞赏码：浏览器里直接用 a[download] 落盘，不需要后端
  const thanksSave = $('thanksSave');
  if (thanksSave) thanksSave.onclick = ()=>{
    const qr = $('thanksQr');
    if (!qr) return;
    const a = document.createElement('a');
    a.href = qr.src;
    a.download = 'PDFPrivacyMasker-' + (CFG.lang === 'en' ? 'thanks-qr' : '赞赏码') + '.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
  aboutMask.addEventListener('click', e=>{ if (e.target === aboutMask) aboutMask.hidden = true; });
}

const autoCloseBtn = $('autoUpdClose');
if (autoCloseBtn) autoCloseBtn.onclick = ()=>{
  // 正在展示新版时，× 等同于「暂不更新」——先劝一次；检查中/超时/挽留界面直接关
  if (AUTO.state === 'new') autoUpdAskLater();
  else autoUpdHide();
};

/* 关于窗里的「去点 Star」：直接开仓库页，打不开就复制地址 */
const aboutStarBtn = $('aboutStar');
if (aboutStarBtn) aboutStarBtn.onclick = async ()=>{
  const url = ($('aboutUrl') && $('aboutUrl').dataset.url) || '';
  if (!url) return;
  if (!await openUpdateUrl(url)) copyText(url, T('已复制仓库地址：', 'Repository URL copied: '));
};
/* 项目地址：点一下就复制，方便二次开发者把来源留在自己版本里 */
['aboutUrl', 'aboutUrlGitee', 'footUrl', 'footUrlGitee'].forEach(id=>{
  const el = $(id);
  if (el) el.addEventListener('click', ()=>{ copyProjectUrl(el); });
});

$('quitBtn').addEventListener('click', async ()=>{
  try{ await api('/api/quit', {method:'POST'}); }catch(e){}
  document.body.innerHTML = '<div style="height:100vh;display:grid;place-items:center;'
    + 'font:14px system-ui;color:#5b6472">' +
    T('已退出，可直接关闭此页面。', 'Closed. You can shut this tab now.') + '</div>';
});
</script>
</body>
</html>
"""
