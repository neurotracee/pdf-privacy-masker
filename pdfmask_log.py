# -*- coding: utf-8 -*-
"""运行日志：启动即记录，崩溃自动留痕，按天分文件，只留 365 天。

设计原则（这是隐私打码工具，日志绝不能反噬隐私）：
1. **绝不记录被处理的内容**——不写 PDF 正文、不写识别出的证件号/手机号/姓名/地址、
   不写用户选择的原始文件名（只记扩展名与大小档位），不写输出路径里的文件名。
2. 只记「发生了什么事件」：启动、导入、开始识别、识别完成（记条目数不记内容）、
   导出、报错堆栈、退出。堆栈里的绝对路径会被归一化。
3. 按天一个文件（logs/YYYY-MM-DD.log，UTF-8），方便按日期查看、按日期段删除。
4. 每次启动生成一个 session 短 ID，行内带 session，界面「本次打开」就按它筛。

对外 API：
    init(app_name, version)     启动时调用：建目录、生成 session、清理过期、装崩溃钩子
    info/warn/error(msg)        记一条普通事件
    exception(where)            在 except 里调用，记完整堆栈
    session_lines()             读回本次会话的日志行
    list_days()                 有日志的日期列表（倒序）
    read_day(date) / read_range(start,end) / read_since(ts)
    delete_range(start,end)     删除某日期段的日志，返回删除的文件数
    export_text(path, text)     把文本写成 TXT（供界面「保存为 TXT」）
    scrub_path(p)               脱敏一个路径：保留盘符/家目录层级，抹掉文件名
"""

import os
import sys
import time
import uuid
import threading
import traceback
from datetime import datetime, timedelta

# 这些状态在 init() 里确定
_BASE_DIR = None      # 日志根目录
_LOG_DIR = None       # .../logs
_SESSION = "--------"  # 8 位会话短 ID
_APP = "App"
_VER = "0"
_LOCK = threading.RLock()
_DATE_FMT = "%Y-%m-%d"

# 保留天数：用户要求「最近一年」，按 365 天算
KEEP_DAYS = 365

# 上次运行是否是「异常结束」（没走到正常退出）。启动时据此提示用户去关于页看日志。
_PREV_CRASHED = False
_PREV_SESSION = ""

# 家目录前缀，用于把路径归一化成 <home>
_HOME = os.path.expanduser("~")


def _platform_base():
    """和设置文件同源的根目录：Windows 用 %APPDATA%\\<App>，其他用家目录下同名目录。"""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "PDF隐私打码工具")
    return os.path.join(_HOME, ".pdfmask")


def scrub_path(p):
    """把路径脱敏到可安全写日志的形态。

    - 抹掉文件名（隐私工具里文件名常就是当事人姓名/证件号）
    - 家目录替换成 <home>
    - 只保留「目录层级 + 扩展名」，例如：
      C:\\Users\\张三\\Desktop\\身份证.pdf  ->  C:\\Users\\<home>\\Desktop\\*.pdf
    """
    if not p:
        return "(空)"
    try:
        p = str(p)
        # 先归一化家目录
        if _HOME and p.lower().startswith(_HOME.lower()):
            p = "<home>" + p[len(_HOME):]
        d, name = os.path.split(p)
        ext = os.path.splitext(name)[1].lower()
        if ext:
            name = "*" + ext
        else:
            name = "*"
        if d:
            return os.path.join(d, name)
        return name
    except Exception:
        return "(路径)"


def _redact(msg):
    """最后一道兜底：把常见的敏感串（长数字串、邮箱）在整行里抹掉。

    业务层本就不该把内容塞进日志；这里只防手滑。长数字（>=11 位）一律打成 [数字]，
    邮箱打成 [邮箱]。保证即使有人误传也没把证件号/手机号写进磁盘。
    """
    try:
        import re
        s = str(msg)
        s = re.sub(r"\b\d{11,}\b", "[数字]", s)
        s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[邮箱]", s)
        return s
    except Exception:
        return str(msg)


def _log_path(day=None):
    day = day or datetime.now().strftime(_DATE_FMT)
    return os.path.join(_LOG_DIR, "%s.log" % day)


def _write(level, msg):
    """写日志：时间 [session] [LEVEL] 内容。

    多行内容（典型是异常堆栈）**每一行都补上同样的前缀**——这样「按会话筛选」
    「按时间段筛选」都能逐行命中，不会只捞到堆栈第一行。
    线程安全，出错绝不抛（日志自身不能拖垮程序）。
    """
    if not _LOG_DIR:
        return
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        prefix = "[%s] [%s] [%s] " % (ts, _SESSION, level)
        raw = _redact(msg)
        rows = str(raw).splitlines() or [""]
        chunk = "".join("%s%s\n" % (prefix, r) for r in rows)
        with _LOCK:
            os.makedirs(_LOG_DIR, exist_ok=True)
            with open(_log_path(), "a", encoding="utf-8") as f:
                f.write(chunk)
    except Exception:
        pass


def info(msg):
    _write("INFO", msg)


def warn(msg):
    _write("WARN", msg)


def error(msg):
    _write("ERROR", msg)


def exception(where="", exc=None):
    """在 except 块里调用，记完整堆栈（堆栈里的路径先脱敏）。"""
    try:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else traceback.format_exc()
        # 堆栈里的绝对路径逐个脱敏（只处理看起来像路径的片段太复杂，这里整段过一遍家目录替换）
        if _HOME:
            tb = tb.replace(_HOME, "<home>")
        _write("ERROR", "异常@%s:\n%s" % (where or "?", tb.rstrip()))
    except Exception:
        pass


def cleanup_old():
    """删除超过 KEEP_DAYS 天的日志文件。返回删除数量。"""
    if not _LOG_DIR or not os.path.isdir(_LOG_DIR):
        return 0
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0
    try:
        for name in os.listdir(_LOG_DIR):
            if not name.endswith(".log"):
                continue
            stem = name[:-4]
            try:
                d = datetime.strptime(stem, _DATE_FMT)
            except ValueError:
                continue
            if d < cutoff:
                try:
                    os.remove(os.path.join(_LOG_DIR, name))
                    removed += 1
                except Exception:
                    pass
    except Exception:
        pass
    return removed


def init(app_name="App", version="0", base_dir=None):
    """启动时调用一次。幂等。"""
    global _BASE_DIR, _LOG_DIR, _SESSION, _APP, _VER
    with _LOCK:
        _APP = app_name or _APP
        _VER = str(version or _VER)
        if _LOG_DIR:
            return
        _BASE_DIR = base_dir or _platform_base()
        _LOG_DIR = os.path.join(_BASE_DIR, "logs")
        _SESSION = uuid.uuid4().hex[:8]
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
        except Exception:
            pass
    _install_crash_hooks()
    _detect_prev_crash()
    n = cleanup_old()
    py = "%s %s" % (sys.implementation.name, ".".join(map(str, sys.version_info[:3])))
    info("启动 %s v%s · 平台 %s · %s · 已清理过期日志 %d 个"
         % (_APP, _VER, sys.platform, py, n))


def _detect_prev_crash():
    """启动前扫一遍上一个会话：若它没以「程序正常退出」收尾，判定为异常结束。"""
    global _PREV_CRASHED, _PREV_SESSION
    try:
        path = _log_path()
        if not os.path.isfile(path):
            return
        last_session = None
        last_line = ""
        # 行格式：[2026-11-23 18:49:37.215] [dbf650f7] [INFO] ...
        import re
        pat = re.compile(r"^\[[^\]]+\]\s+\[([0-9a-f]{8})\]\s+\[(INFO|WARN|ERROR|FATAL)\]\s?(.*)$")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = pat.match(line.rstrip("\n"))
                if not m:
                    continue
                last_session = m.group(1)
                last_line = m.group(3)
        if not last_session:
            return
        _PREV_SESSION = last_session
        # 正常收尾会写「程序正常退出」；被强杀 / 崩溃则不会。
        _PREV_CRASHED = "正常退出" not in last_line
    except Exception:
        pass


def prev_crashed():
    """上次运行是否异常结束。界面可在首次加载时据此弹提示。"""
    return _PREV_CRASHED and bool(_PREV_SESSION)


def prev_session():
    return _PREV_SESSION


def _install_crash_hooks():
    """接管未捕获异常：先写日志，再交给原处理器（保持原有行为）。"""
    try:
        old_hook = sys.excepthook

        def _hook(etype, value, tb):
            try:
                txt = "".join(traceback.format_exception(etype, value, tb))
                if _HOME:
                    txt = txt.replace(_HOME, "<home>")
                _write("FATAL", "未捕获异常:\n%s" % txt.rstrip())
            except Exception:
                pass
            try:
                old_hook(etype, value, tb)
            except Exception:
                pass

        sys.excepthook = _hook
    except Exception:
        pass

    # 子线程里的异常默认只打到 stderr，也接管一下
    try:
        if hasattr(threading, "excepthook"):
            old_th = threading.excepthook

            def _th_hook(args):
                try:
                    txt = "".join(traceback.format_exception(
                        args.exc_type, args.exc_value, args.exc_traceback))
                    if _HOME:
                        txt = txt.replace(_HOME, "<home>")
                    _write("FATAL", "线程未捕获异常(%s):\n%s"
                           % (getattr(args.thread, "name", "?"), txt.rstrip()))
                except Exception:
                    pass
                try:
                    old_th(args)
                except Exception:
                    pass

            threading.excepthook = _th_hook
    except Exception:
        pass


def session_id():
    return _SESSION


def log_dir():
    return _LOG_DIR


def session_lines():
    """本次会话的全部日志行（按 session 前缀筛当天文件）。"""
    if not _LOG_DIR:
        return []
    out = []
    try:
        with open(_log_path(), "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if "[%s]" % _SESSION in line:
                    out.append(line.rstrip("\n"))
    except Exception:
        pass
    return out


def list_days():
    """有日志的日期（YYYY-MM-DD），倒序。"""
    if not _LOG_DIR or not os.path.isdir(_LOG_DIR):
        return []
    out = []
    try:
        for name in os.listdir(_LOG_DIR):
            if name.endswith(".log"):
                stem = name[:-4]
                try:
                    datetime.strptime(stem, _DATE_FMT)
                    out.append(stem)
                except ValueError:
                    pass
    except Exception:
        pass
    return sorted(out, reverse=True)


def read_day(date):
    """读某一天（YYYY-MM-DD）的全部日志。"""
    if not _LOG_DIR:
        return ""
    try:
        with open(_log_path(date), "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def read_range(start, end):
    """读 [start, end] 闭区间日期段的日志，拼成一段文本。"""
    days = [d for d in list_days() if start <= d <= end]
    parts = []
    for d in sorted(days):
        body = read_day(d)
        if body:
            parts.append("# ==== %s ====\n%s" % (d, body))
    return "\n".join(parts)


def read_since(year, month, day, hour=0, minute=0):
    """从指定时刻起（含）到现在的日志行。用于「精准定位当时的错误」。"""
    if not _LOG_DIR:
        return ""
    try:
        since = datetime(year, month, day, hour, minute)
    except Exception:
        return ""
    out = []
    days = [d for d in list_days() if d >= since.strftime(_DATE_FMT)]
    for d in sorted(days):
        try:
            with open(_log_path(d), "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.rstrip("\n")
                    # 行首是 [YYYY-MM-DD HH:MM:SS.mmm]
                    if line.startswith("[") and len(line) > 24:
                        try:
                            stamp = datetime.strptime(line[1:24], "%Y-%m-%d %H:%M:%S.%f")
                            if stamp >= since:
                                out.append(line)
                        except Exception:
                            pass
        except Exception:
            continue
    return "\n".join(out)


def delete_range(start, end):
    """删除 [start, end] 闭区间日期段的日志文件，返回删除数量。"""
    if not _LOG_DIR or not os.path.isdir(_LOG_DIR):
        return 0
    removed = 0
    for d in list_days():
        if start <= d <= end:
            try:
                os.remove(_log_path(d))
                removed += 1
            except Exception:
                pass
    if removed:
        info("用户删除了 %s ~ %s 的日志，共 %d 个文件" % (start, end, removed))
    return removed


def export_text(path, text):
    """把文本写成 UTF-8 TXT。返回实际写入的路径。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def total_size():
    """当前日志目录占用的字节数（界面提示用）。"""
    if not _LOG_DIR or not os.path.isdir(_LOG_DIR):
        return 0
    total = 0
    try:
        for name in os.listdir(_LOG_DIR):
            if name.endswith(".log"):
                try:
                    total += os.path.getsize(os.path.join(_LOG_DIR, name))
                except Exception:
                    pass
    except Exception:
        pass
    return total
