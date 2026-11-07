# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 项目创作时为初中生
#
# This file is part of PDF 隐私打码工具 (PDF Privacy Masker) and is distributed
# under the GNU Affero General Public License v3.0 or later. See LICENSE.

"""首页 UI：一整页 HTML（含 CSS 与前端 JS），与后端逻辑分开维护。

这个字符串里出现的 __TOKEN__ / __VERSION__ / __URL__ / __CREDIT__ /
__URLSHORT__ / __THANKS__ 占位符由 pdfmask.Handler 在返回页面时替换。
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
/* action bar */
.actionbar{flex:0 0 66px;height:66px;background:#fff;border-top:1px solid var(--line);
  display:flex;align-items:center;gap:14px;padding:0 22px}
.sum{font-size:13px;color:var(--ink2)}
.sum b{color:var(--ink);font-size:15px}
/* overlay / toast / result */
.overlay{position:fixed;inset:0;background:rgba(244,245,247,.82);backdrop-filter:blur(3px);
  display:grid;place-items:center;z-index:200}
.overlay .box{background:#fff;border-radius:16px;padding:26px 34px;text-align:center;
  box-shadow:0 24px 60px -24px rgba(15,24,40,.4);min-width:260px}
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
/* ---------- 扫描件提示（左上角红字） ---------- */
.nocap{display:inline-block;margin-left:9px;font-size:10.5px;font-weight:700;line-height:1.5;
  color:#e5484d;background:#fdecee;border:1px solid #f7c6cb;border-radius:5px;padding:0 6px;
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
        <h1>PDF 隐私打码工具<span class="nocap" title="扫描件是纯图片、没有文字层，无法自动识别，请用「框选手动打码」">不支持扫描件 PDF</span></h1>
        <p>真马赛克 · 全程本地零上传 · <span class="hint-draw">扫描件可用「框选手动打码」</span></p>
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
          <button class="tb-btn" id="drawBtn" style="border:1px solid var(--line);background:#fff;border-radius:9px;padding:6px 11px">
            框选手动打码
          </button>
          <div class="spacer"></div>
          <div class="hint-chip" title="按住鼠标拖动可以框出要打码的区域；双击页面上的方框，可以取消或恢复该处打码">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/>
              <path d="M12 11v5"/><path d="M12 8h.01"/></svg>
            拖动框选 · 双击方框取消/恢复打码
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
  <div class="box"><div class="spin"></div><div class="ov-text" id="ovText">处理中…</div></div>
</div>
<div class="toast" id="toast"></div>

<div class="about-mask" id="aboutMask" hidden>
  <div class="about-box">
    <h3>PDF 隐私打码工具</h3>
    <div class="ver">版本 __VERSION__ · <span id="verNote">本地离线运行</span></div>
    <dl>
      <dt>指导作者</dt><dd>__AUTHOR__。<br>需求、识别规则的设计、验收测试全部由本人完成。</dd>
      <dt>开发</dt><dd>__DEVELOPER__</dd>
      <dt>开源协议</dt><dd>__LICENSE__</dd>
      <dt>原项目地址</dt><dd class="url" id="aboutUrl" data-url="__URL__" title="点击复制">__URL__</dd>
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
      <label class="field-label">版本与更新</label>
      <div class="ver-row">
        <span class="ver-cur"><span id="verLabel1">当前版本</span> v<b id="curVer">__VERSION__</b> ·
          <span id="verLabel2">仓库最新</span> <b id="latestVer">—</b></span>
        <button class="btn" id="checkBtn">检查更新</button>
      </div>
      <div class="modal-note" style="margin-top:8px">启动时会自动查一次更新；没有网络就静默跳过，不会打扰你。这里可以随时手动再查。</div>
      <div class="upd-box" id="updBox" hidden>
        <div id="updText"></div>
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
           mask:true, drawing:false, hi:null, scanned:[], outDir:'', stats:null, size:0};

const $ = id => document.getElementById(id);

/* ---------- 中英双语 ----------
   静态文字按「原文」查表替换（含 title / placeholder / alt），
   动态提示走 T(中文, English)。切换立即生效，不用重启。 */
let LANG = 'zh';
const DICT = {
  '设置':'Settings', '关于':'About', '退出':'Quit',
  'PDF 隐私打码工具':'PDF Privacy Masker',
  '不支持扫描件 PDF':'No scanned PDFs',
  '真马赛克 · 全程本地零上传 · ':'Real mosaic · 100% local · ',
  '扫描件可用「框选手动打码」':'for scans, use the manual box tool',
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
  '拖动框选 · 双击方框取消/恢复打码':'Drag to draw · double-click a box to mute/unmute',
  '预览打码效果':'Preview mosaic',
  '已选 ':'Selected ', ' 处 · 生成后原文将被永久打散':' items · text will be destroyed for good',
  '重新选择文件':'Choose another file', '生成打码 PDF':'Generate masked PDF',
  '处理中…':'Working…',
  '指导作者':'Advisor', '开发':'Built by', '开源协议':'License', '原项目地址':'Upstream',
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
  '启动时会自动查一次更新；没有网络就静默跳过，不会打扰你。这里可以随时手动再查。':'Updates are checked once at launch; offline, the check is skipped silently. You can also check again here at any time.', '用浏览器打开下载':'Open download in browser',
  '复制链接':'Copy link',
  '扫描件是纯图片、没有文字层，无法自动识别，请用「框选手动打码」':
    'A scan is just an image with no text layer, so it cannot be detected — use the manual box tool',
  '按住鼠标拖动可以框出要打码的区域；双击页面上的方框，可以取消或恢复该处打码':
    'Hold and drag to draw a box; double-click a box on the page to mute or unmute it',
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
  '年龄':'Age','手动框选':'Manual'};

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
function overlay(on, text){
  $('overlay').hidden = !on; if (text) $('ovText').textContent = text;
}
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
  overlay(true, T('正在识别敏感信息…', 'Scanning for sensitive data…'));
  try{
    const r = await fetch('/api/upload', {method:'POST',
      headers:{'X-Token':TOKEN,'X-File-Name':encodeURIComponent(file.name)}, body:file});
    if(!r.ok){ let m=T('识别失败', 'Scan failed'); try{const j=await r.json(); m=j.error||m;}catch(e){} throw new Error(m); }
    applyDoc(await r.json());
  }catch(e){ toast(e.message, true); }
  finally{ overlay(false); }
}
async function openPath(path){
  overlay(true, T('正在识别敏感信息…', 'Scanning for sensitive data…'));
  try{
    const d = await api('/api/open', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path:path})});
    applyDoc(d);
  }catch(e){ toast(e.message, true); }
  finally{ overlay(false); }
}

function applyDoc(d){
  S.docId = d.docId; S.name = d.name; S.pages = d.pages; S.findings = d.findings;
  S.scanned = d.scanned || []; S.outDir = d.outDir || '';
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
    const pages = S.scanned.map(i=>i+1).join(T('、', ', '));
    $('scanWarn').hidden = false;
    $('scanWarn').textContent = T(
      '第 ' + pages + ' 页没有文字层（可能是扫描件），这几页无法自动识别，请用「框选手动打码」补齐。',
      'Page ' + pages + ' has no text layer (probably a scan). Those pages cannot be detected — use the manual box tool.'
    );
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
  if (S.scanned.indexOf(S.page) >= 0) info += T(' · 无文字层', ' · no text layer');
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
$('maskPreview').addEventListener('change', e=>{ S.mask = e.target.checked; refreshPreview(); });
$('drawBtn').addEventListener('click', ()=>{
  S.drawing = !S.drawing;
  $('drawBtn').classList.toggle('active', S.drawing);
  $('canvasWrap').classList.toggle('draw', S.drawing);
  if(S.drawing) toast(T('在页面上按住鼠标拖动，框出要打码的区域', 'Hold and drag on the page to draw a box'));
});

/* 双击方框：取消 / 恢复这一处打码（自动识别的框和手动框都支持） */
$('canvasWrap').addEventListener('dblclick', e=>{
  const img = $('pageImg');
  if(!img || !img.src || !S.findings.length) return;
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

/* 手动框选 */
let band=null, startPt=null;
$('canvasWrap').addEventListener('mousedown', e=>{
  if(!S.drawing || e.button!==0) return;
  const img = $('pageImg'); if(!img.src) return;
  const r = img.getBoundingClientRect();
  if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom) return;
  e.preventDefault();
  startPt = {x:e.clientX, y:e.clientY};
  band = document.createElement('div'); band.className='band'; document.body.appendChild(band);
  drawBand(startPt, startPt);
});
$('canvasWrap').addEventListener('mousemove', e=>{
  if(band && startPt) drawBand(startPt, {x:e.clientX, y:e.clientY});
});
window.addEventListener('mouseup', async e=>{
  if(!band || !startPt) return;
  const end = {x:e.clientX, y:e.clientY};
  band.remove(); band=null;
  const p0 = startPt; startPt=null;
  const img = $('pageImg'); const r = img.getBoundingClientRect();
  const x0 = Math.min(p0.x,end.x), y0 = Math.min(p0.y,end.y);
  const x1 = Math.max(p0.x,end.x), y1 = Math.max(p0.y,end.y);
  if(x1-x0 < 5 || y1-y0 < 5) return;
  const rect = [ (x0-r.left)/S.zoom, (y0-r.top)/S.zoom, (x1-r.left)/S.zoom, (y1-r.top)/S.zoom ];
  try{
    const res = await api('/api/manual', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({doc:S.docId, page:S.page, rect:rect})});
    S.findings.push({id:res.id, type:'manual', label:T('手动框选', 'Manual box'),
      mask:T('手动框选区域', 'Manual area'), page:S.page, rect:rect, note:'manual'});
    S.sel.add(res.id); S.hi = res.id;
    const sub = $('fSub');
    renderList(); syncBar(); refreshPreview(); toast(T('已添加手动打码区域', 'Manual mask added'));
  }catch(err){ toast(err.message, true); }
});
function drawBand(a,b){
  const x=Math.min(a.x,b.x), y=Math.min(a.y,b.y), w=Math.abs(a.x-b.x), h=Math.abs(a.y-b.y);
  band.style.left=x+'px'; band.style.top=y+'px'; band.style.width=w+'px'; band.style.height=h+'px';
}

/* ---------- 设置 / 保存位置 ---------- */
let CFG = {saveDir:'', rememberDir:true, noAsk:false, defaultDir:'', effectiveDir:''};

async function loadCfg(){
  try{
    const q = S.docId ? ('?doc=' + encodeURIComponent(S.docId)) : '';
    CFG = await api('/api/settings' + q);
  }catch(e){}
  return CFG;
}

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
  overlay(true, T('正在生成打码 PDF…', 'Generating masked PDF…'));
  try{
    const body = {doc:S.docId, ids:[...S.sel]};
    if(opt){ body.dir = opt.dir || ''; body.remember = !!opt.remember; body.noAsk = !!opt.noAsk; }
    const d = await api('/api/render', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    overlay(false);
    if(opt) await loadCfg();
    showResult(d);
  }catch(e){ overlay(false); toast(e.message, true); }
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
    $('setMask').hidden = true;
    toast(T('设置已保存', 'Settings saved'));
  }catch(e){ toast(e.message, true); }
});
$('setReset').addEventListener('click', async ()=>{
  $('setPath').value = ''; $('setAsk').checked = true;
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({saveDir:'', noAsk:false})});
    await loadCfg(); toast(T('已恢复默认设置', 'Defaults restored'));
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
  if(!r.hasUpdate){
    box.className = 'upd-box ok';
    txt.textContent = T('已是最新版本（v' + r.current + '）。',
                        'You are on the latest version (v' + r.current + ').');
    return;
  }
  box.className = 'upd-box new';
  txt.textContent = UPD.opened
    ? T('发现新版本 v' + r.latest + '（当前 v' + r.current + '），已经让浏览器去下载了。',
        'New version v' + r.latest + ' is out (you have v' + r.current + '). Your browser is downloading it now.')
    : T('发现新版本 v' + r.latest + '（当前 v' + r.current + '），但没能自动打开浏览器，点下面的按钮再试一次。',
        'New version v' + r.latest + ' is out (you have v' + r.current + '), but the browser did not open — try the button below.');
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
  $('updText').textContent = T('正在连接 GitHub 查询最新版本…', 'Contacting GitHub for the latest release…');
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
  $('autoUpdUrl').hidden = true;
  $('autoUpdUrl').textContent = '';
  $('autoUpdActs').innerHTML = '';
  $('autoUpdActs').hidden = true;
  $('autoUpdClose').hidden = false;
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
  $('autoUpdTitle').textContent = T('正在检查更新', 'Checking for updates');
  $('autoUpdText').textContent = T(
    '正在向 GitHub 读一次版本号，不传任何文件。网络慢的话可以直接关掉，不影响使用。',
    'Reading the latest version number from GitHub. No files are sent. If the network is slow, just close this.');
  $('autoUpdSpinText').textContent = T('连接 GitHub…', 'Contacting GitHub…');
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
  $('autoUpdText').textContent = strong
    ? T('你当前是 v' + r.current + '。这一版修了一直在影响使用的问题，强烈建议尽快换上——更新只要一分钟，原来的功能都在，文件也始终留在你的电脑里。',
        'You are on v' + r.current + '. This build fixes problems that keep getting in the way, so updating is strongly suggested — it takes a minute, everything keeps working, and your files never leave your computer.')
    : T('你当前是 v' + r.current + '。新版修了几个已知问题，也更稳——不更新也能继续用，但建议尽快换上。',
        'You are on v' + r.current + '. The new build fixes a few known problems and is more reliable — you can keep using this version, but updating is worth it.');
  $('autoUpdUrl').hidden = false;
  $('autoUpdUrl').textContent = r.url || r.releasesUrl || '';
  autoUpdBtn(T('暂不更新', 'Not now'), false, autoUpdAskLater);
  autoUpdBtn(T('复制链接', 'Copy link'), false, ()=>{
    const url = r.url || r.releasesUrl || '';
    if (url) copyText(url, T('已复制下载链接：', 'Download link copied: '));
  });
  autoUpdBtn(T('用浏览器下载', 'Download in browser'), true, async ()=>{
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
['aboutUrl', 'footUrl'].forEach(id=>{
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
