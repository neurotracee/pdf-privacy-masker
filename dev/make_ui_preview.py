# -*- coding: utf-8 -*-
"""生成 UI 预览页（用假数据跑真实前端逻辑），供截图检查。

不修改源码：把 HTML_UI 里的占位符替换掉，再在 </body> 前注入一个 fetch 假实现，
然后驱动真实的点击流程，检查弹窗、勾选框、结果卡片是否正常渲染。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pdfmask  # noqa: E402

OUT = os.path.join(ROOT, "dev", "_ui")

MOCK = r"""
<script>
(function(){
  window.__errs = [];
  window.addEventListener('error', function(e){ window.__errs.push(String(e.message)); });

  var OUTDIR = 'D:\\HugoMoveData\\User\\YB\\Downloads';
  var DOC = {
    docId: 't1', name: '样例_纯段落多人多页_未打码.pdf', size: 812345,
    pages: [{w:595,h:842,hasText:true,rot:0},{w:595,h:842,hasText:true,rot:0}],
    findings: [
      {id:'f1',type:'idcard',label:'身份证号',mask:'1101**********1234',page:0,rect:[100,100,220,120],note:'',suspect:false},
      {id:'f2',type:'phone',label:'手机号',mask:'138****8888',page:0,rect:[100,140,200,160],note:'',suspect:false},
      {id:'f3',type:'name',label:'姓名',mask:'陈██',page:0,rect:[240,140,320,160],note:'',suspect:false},
      {id:'f4',type:'email',label:'邮箱',mask:'ch***@qq.com',page:0,rect:[100,180,260,200],note:'',suspect:false},
      {id:'f5',type:'bankcard',label:'银行卡号',mask:'6222********1234',page:1,rect:[100,100,240,120],note:'',suspect:false},
      {id:'f6',type:'address',label:'地址',mask:'广东省深圳市南山区****',page:1,rect:[100,140,320,160],note:'',suspect:false},
      {id:'f7',type:'name',label:'姓名',mask:'林██',page:1,rect:[100,180,160,200],note:'',suspect:true}
    ],
    stats: {'身份证号':1,'手机号':1,'姓名':2,'邮箱':1,'银行卡号':1,'地址':1},
    scanned: [], outDir: OUTDIR
  };
  var CFG = {saveDir:'', rememberDir:true, noAsk:false, defaultDir:OUTDIR,
             effectiveDir:OUTDIR, configured:false, lang:'zh',
             settingsPath:'C:\\Users\\YB\\AppData\\Roaming\\PDF隐私打码工具\\settings.json'};
  window.__UPD = {ok:true, current:'1.4.7.0', latest:'1.5.0.0', hasUpdate:false, strong:false,
    channel:'Gitee', fallbackFrom:'',
    url:'https://github.com/neurotracee/pdf-privacy-masker/releases/download/v1.5.0/PDFPrivacyMasker-1.5.0.0.exe',
    releasesUrl:'https://github.com/neurotracee/pdf-privacy-masker/releases/latest',
    digest: __DIGEST__};
  function json(o){ return new Response(JSON.stringify(o),
      {status:200, headers:{'content-type':'application/json; charset=utf-8'}}); }

  window.fetch = function(url, opts){
    var u = String(url), m = (opts && opts.method) || 'GET';
    var b = {};
    try { b = JSON.parse((opts && opts.body) || '{}'); } catch(e){}
    if (u.indexOf('/api/settings') === 0){
      if (m === 'POST'){
        if ('saveDir' in b) CFG.saveDir = b.saveDir;
        if ('noAsk' in b) CFG.noAsk = !!b.noAsk;
        CFG.effectiveDir = CFG.saveDir || CFG.defaultDir;
        CFG.configured = !!CFG.saveDir;
        return Promise.resolve(json({ok:true, settings:CFG, path:CFG.settingsPath}));
      }
      return Promise.resolve(json(CFG));
    }
    if (u.indexOf('/api/check_update') >= 0) return Promise.resolve(json(window.__UPD));
    if (u.indexOf('/api/openurl') >= 0) return Promise.resolve(json({ok:true, url:b.url}));
    if (u.indexOf('/api/pickdir') >= 0)
      return Promise.resolve(json({path:'D:\\HugoMoveData\\User\\YB\\Downloads\\已打码输出', status:'ok'}));
    if (u.indexOf('/api/render') >= 0){
      var dir = b.dir || CFG.effectiveDir;
      return Promise.resolve(json({token:'tk', dir:dir,
        path: dir + '\\样例_纯段落多人多页_未打码_已打码.pdf',
        name: '样例_纯段落多人多页_未打码_已打码.pdf', size: 798211,
        count: 6, stats: {'身份证号':1,'手机号':1,'姓名':2,'邮箱':1,'银行卡号':1},
        pages: 2, hitPages: 2}));
    }
    return Promise.resolve(json({ok:true}));
  };

  // 页面预览用一张假 A4 图代替（避免真去请求 /api/preview）
  function placeholder(){
    var c = document.createElement('canvas'); c.width = 620; c.height = 877;
    var x = c.getContext('2d');
    x.fillStyle = '#fff'; x.fillRect(0,0,620,877);
    x.fillStyle = '#dfe3ea'; x.fillRect(56,42,210,13);
    x.fillStyle = '#eef0f4';
    for (var i=0;i<26;i++){
      if (i === 6 || i === 13 || i === 20) continue;
      x.fillRect(56, 82+i*26, 508-((i%4===0)?140:0), 7);
    }
    return c.toDataURL('image/png');
  }
  var PH = placeholder();
  window.refreshPreview = function(){
    var img = document.getElementById('pageImg');
    img.src = PH;
    if (typeof window.syncBar === 'function') window.syncBar();
  };

  window.__ready = function(steps){
    setTimeout(function(){
      try {
        if (steps !== 'home') window.applyDoc(DOC);
        setTimeout(function(){ if (typeof steps === 'function') steps(); }, 60);
      } catch(e){ window.__errs.push(String(e)); }
    }, 40);
  };
})();
</script>
"""

# 点「暂不更新」后应该出现挽留界面
PLEA = ("function(){ setTimeout(function(){"
        " var b = document.querySelector('#autoUpdActs .btn'); if (b) b.click(); }, 600); }")

STEPS = {
    "ui_01_home": "'home'",
    "ui_02_work": 'function(){}',
    "ui_03_save": "function(){ document.getElementById('goBtn').click(); }",
    "ui_04_settings": "function(){ document.getElementById('setBtn').click(); }",
    "ui_05_result": ("function(){ document.getElementById('goBtn').click();"
                     " setTimeout(function(){ document.getElementById('saveOk').click(); }, 320); }"),
    # 勾了「不再询问」之后：点生成应该直接出结果，不再弹窗
    "ui_06_noask": "function(){ document.getElementById('goBtn').click(); }",
    # 「关于」窗口：附加条款的三条硬要求是否完整、不溢出
    "ui_07_about": "function(){ document.getElementById('aboutBtn').click(); }",
    # 设置面板：中英切换 + 检查更新三种结果
    "ui_08_settings_en": ("function(){ document.getElementById('setBtn').click();"
                          " setTimeout(function(){ document.querySelector('.seg-btn[data-lang=en]').click(); }, 80); }"),
    "ui_09_update_new": ("function(){ window.__UPD.hasUpdate = true;"
                         " document.getElementById('setBtn').click();"
                         " setTimeout(function(){ document.getElementById('checkBtn').click(); }, 120); }"),
    "ui_10_update_latest": ("function(){ window.__UPD.hasUpdate = false; window.__UPD.latest = '1.4.7.0';"
                            " document.getElementById('setBtn').click();"
                            " setTimeout(function(){ document.getElementById('checkBtn').click(); }, 120); }"),
    # 英文界面下同一份发布正文：摘要和条目要切成英文
    "ui_20_update_new_en": ("function(){ window.__UPD.hasUpdate = true;"
                            " document.getElementById('setBtn').click();"
                            " setTimeout(function(){"
                            "  document.querySelector('.seg-btn[data-lang=en]').click();"
                            "  setTimeout(function(){ document.getElementById('checkBtn').click(); }, 80);"
                            " }, 120); }"),
    # 首选 Gitee 没连上、自动改用 GitHub：界面要说清原因，别让人以为设置被改了
    "ui_21_update_fallback": ("function(){ window.__UPD.hasUpdate = true;"
                              " window.__UPD.channel = 'GitHub'; window.__UPD.fallbackFrom = 'Gitee';"
                              " document.getElementById('setBtn').click();"
                              " setTimeout(function(){ document.getElementById('checkBtn').click(); }, 120); }"),
    "ui_11_update_fail": ("function(){ window.__UPD = {ok:false, error:'TimeoutError: timed out'};"
                          " document.getElementById('setBtn').click();"
                          " setTimeout(function(){ document.getElementById('checkBtn').click(); }, 120); }"),
    "ui_12_work_en": ("function(){ document.querySelector('.seg-btn[data-lang=en]').click(); }"),
    "ui_13_about_en": ("function(){ document.querySelector('.seg-btn[data-lang=en]').click();"
                       " setTimeout(function(){ document.getElementById('aboutBtn').click(); }, 80); }"),
    "ui_14_save_en": ("function(){ document.querySelector('.seg-btn[data-lang=en]').click();"
                      " setTimeout(function(){ document.getElementById('goBtn').click(); }, 80); }"),
    # 启动自动检查：建议 / 强烈建议 / 检查中卡住 / 两档挽留 五个状态
    "ui_15_auto_suggest": "function(){}",
    "ui_16_auto_strong": "function(){}",
    "ui_17_auto_checking": "function(){}",
    "ui_18_auto_plea_suggest": PLEA,
    "ui_19_auto_plea_strong": PLEA,
}

# 启动自动检查发生在页面脚本一开始，改不了 __UPD，所以按页面改 mock
PER_PAGE = {
    "ui_15_auto_suggest": [("hasUpdate:false", "hasUpdate:true")],
    "ui_16_auto_strong": [("hasUpdate:false", "hasUpdate:true"), ("strong:false,", "strong:true,")],
    # 卡住：让 /api/check_update 永不返回，看 1.2 秒后那个可关闭的提示
    "ui_17_auto_checking": [
        ("if (u.indexOf('/api/check_update') >= 0) return Promise.resolve(json(window.__UPD));",
         "if (u.indexOf('/api/check_update') >= 0) return new Promise(function(){});"),
    ],
    "ui_18_auto_plea_suggest": [("hasUpdate:false", "hasUpdate:true")],
    "ui_19_auto_plea_strong": [("hasUpdate:false", "hasUpdate:true"), ("strong:false,", "strong:true,")],
}


def build():
    os.makedirs(OUT, exist_ok=True)
    # 弹窗文案用真实发布正文解析出来，预览里看到的就是用户会看到的那两段
    notes = os.path.join(ROOT, "release", "v%s" % pdfmask.VERSION, "RELEASE-NOTES.md")
    digest = {"brief": {"zh": "", "en": ""}, "notes": {"zh": [], "en": []}}
    if os.path.exists(notes):
        import pdfmask_update
        digest = pdfmask_update.parse_digest(open(notes, encoding="utf-8").read())
    digest_js = json.dumps(digest, ensure_ascii=False)
    base = pdfmask.HTML_UI
    base = (base.replace("__TOKEN__", "testtoken")
                .replace("__BOOT__", '""')
                .replace("__VERSION__", pdfmask.VERSION)
                .replace("__AUTHOR__", pdfmask.AUTHOR)
                .replace("__DEVELOPER__", pdfmask.DEVELOPER)
                .replace("__LICENSE__", pdfmask.LICENSE_NAME)
                .replace("__CREDIT__", pdfmask.CREDIT_LINE)
                .replace("__URLSHORT__", pdfmask.URL_SHORT)
                .replace("__URL__", pdfmask.PROJECT_URL)
                .replace("__THANKS__", pdfmask.QR_PNG_B64))
    for name, step in STEPS.items():
        mock = MOCK.replace("__DIGEST__", digest_js)
        if name.startswith("ui_06"):
            mock = mock.replace("noAsk:false", "noAsk:true").replace(
                "saveDir:''", "saveDir:'D:\\\\HugoMoveData\\\\User\\\\YB\\\\Downloads'")
        for a, b in PER_PAGE.get(name, []):
            mock = mock.replace(a, b)
        boot = "<script>window.__ready(%s);</script>" % step
        # mock 必须在页面主脚本之前生效，否则启动自动检查会用真实 fetch
        html = base.replace("<body>", "<body>" + mock, 1).replace("</body>", boot + "</body>", 1)
        path = os.path.join(OUT, name + ".html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print("生成", path)


if __name__ == "__main__":
    build()
