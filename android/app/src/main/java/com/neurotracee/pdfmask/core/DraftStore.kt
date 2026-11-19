package com.neurotracee.pdfmask.core

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * 临时保存（草稿）。
 *
 * 用户在处理页按返回时，除了「继续编辑」和「直接离开」，还能选「临时保存」——
 * 把这份 PDF 和当前的编辑状态（哪些框、哪些擦了、哪些取消了勾选、停在第几页）
 * 一起存到应用私有目录，下次打开应用在首页点「继续编辑」就能接上。
 *
 * 只保留**最近一份**草稿：这是「临走前收一下」的功能，不是多文档工作台。
 * 存两份只会让用户在首页纠结该点哪个。
 *
 * 为什么源 PDF 也要复制一份：用户在系统文件管理器里把原文件删掉/改名，
 * 草稿里的坐标就无处可用；复制一份（几十 MB 上限）换「一定能接上」。
 */
object DraftStore {

    /** 草稿格式版本。字段增删时跟着改，读到老版本直接丢弃而不是猜。 */
    private const val VERSION = 1

    private fun dir(ctx: Context) = File(ctx.filesDir, "draft").apply { mkdirs() }

    fun jsonFile(ctx: Context) = File(dir(ctx), "draft.json")
    fun pdfFile(ctx: Context) = File(dir(ctx), "source.pdf")

    fun has(ctx: Context): Boolean {
        val j = jsonFile(ctx)
        return j.length() > 0 && pdfFile(ctx).length() > 0
    }

    /** 首页卡片要用的轻量信息，不读 findings 明细。 */
    data class Meta(
        val name: String,
        val savedAt: Long,
        val pages: Int,
        val marks: Int,
        val current: Int
    )

    /**
     * 保存一份草稿。
     *
     * @param source 已经拷到应用目录的 PDF（load 时的那份缓存文件）
     * @return 成功与否；失败时调用方应提示「临时保存失败」，而不是假装成功
     */
    fun save(
        ctx: Context,
        source: File,
        name: String,
        pagesCount: Int,
        findings: List<Finding>,
        selected: Set<Int>,
        erasers: Map<Int, List<Rect>>,
        current: Int
    ): Boolean {
        return runCatching {
            val d = dir(ctx)
            // 先写临时文件再改名：中途被杀不会留下半个 JSON
            val tmpJson = File(d, "draft.json.tmp")
            val tmpPdf = File(d, "source.pdf.tmp")
            source.copyTo(tmpPdf, overwrite = true)

            val root = JSONObject()
            root.put("v", VERSION)
            root.put("name", name)
            root.put("savedAt", System.currentTimeMillis())
            root.put("pages", pagesCount)
            root.put("current", current)

            val fs = JSONArray()
            for (f in findings) {
                fs.put(
                    JSONObject()
                        .put("id", f.id)
                        .put("page", f.page)
                        .put("type", f.type)
                        .put("text", f.text)
                        .put("note", f.note)
                        .put("suspect", f.suspect)
                        .put("rect", rectToJson(f.rect))
                )
            }
            root.put("findings", fs)

            val sel = JSONArray()
            for (id in selected) sel.put(id)
            root.put("selected", sel)

            val es = JSONObject()
            for ((p, list) in erasers) {
                val arr = JSONArray()
                for (r in list) arr.put(rectToJson(r))
                es.put(p.toString(), arr)
            }
            root.put("erasers", es)

            tmpJson.writeText(root.toString())
            if (!tmpJson.renameTo(jsonFile(ctx))) {
                // 某些文件系统不允许覆盖式改名，退一步直接写
                jsonFile(ctx).writeText(root.toString())
                tmpJson.delete()
            }
            if (!tmpPdf.renameTo(pdfFile(ctx))) {
                tmpPdf.copyTo(pdfFile(ctx), overwrite = true)
                tmpPdf.delete()
            }
            true
        }.getOrDefault(false)
    }

    fun meta(ctx: Context): Meta? {
        val j = jsonFile(ctx)
        if (j.length() <= 0 || pdfFile(ctx).length() <= 0) return null
        return runCatching {
            val o = JSONObject(j.readText())
            if (o.optInt("v", 0) != VERSION) return null
            Meta(
                name = o.optString("name", "document.pdf"),
                savedAt = o.optLong("savedAt", 0L),
                pages = o.optInt("pages", 0),
                marks = o.optJSONArray("findings")?.length() ?: 0,
                current = o.optInt("current", 0)
            )
        }.getOrNull()
    }

    /** 完整草稿内容；meta() 失败或版本不符时返回 null（宁可当作没有，也不要半套状态） */
    class Snapshot(
        val name: String,
        val pdf: File,
        val current: Int,
        val findings: List<Finding>,
        val selected: Set<Int>,
        val erasers: Map<Int, List<Rect>>
    )

    fun load(ctx: Context): Snapshot? {
        val j = jsonFile(ctx)
        val p = pdfFile(ctx)
        if (j.length() <= 0 || p.length() <= 0) return null
        return runCatching {
            val o = JSONObject(j.readText())
            if (o.optInt("v", 0) != VERSION) return null

            val fs = mutableListOf<Finding>()
            val arr = o.optJSONArray("findings") ?: JSONArray()
            for (i in 0 until arr.length()) {
                val e = arr.getJSONObject(i)
                val rect = rectFromJson(e.optJSONArray("rect")) ?: continue
                fs += Finding(
                    page = e.optInt("page", 0),
                    type = e.optString("type", Kind.MANUAL),
                    text = e.optString("text", ""),
                    rect = rect,
                    note = e.optString("note", ""),
                    suspect = e.optBoolean("suspect", false),
                    id = e.optInt("id", -1)
                )
            }

            val selArr = o.optJSONArray("selected") ?: JSONArray()
            val sel = HashSet<Int>()
            for (i in 0 until selArr.length()) sel += selArr.getInt(i)

            val esObj = o.optJSONObject("erasers") ?: JSONObject()
            val es = HashMap<Int, List<Rect>>()
            for (key in esObj.keys()) {
                val pageNo = key.toIntOrNull() ?: continue
                val list = esObj.optJSONArray(key) ?: continue
                val rects = mutableListOf<Rect>()
                for (i in 0 until list.length()) {
                    rectFromJson(list.optJSONArray(i))?.let { rects += it }
                }
                if (rects.isNotEmpty()) es[pageNo] = rects
            }

            Snapshot(
                name = o.optString("name", "document.pdf"),
                pdf = p,
                current = o.optInt("current", 0),
                findings = fs,
                selected = sel,
                erasers = es
            )
        }.getOrNull()
    }

    fun clear(ctx: Context) {
        runCatching {
            jsonFile(ctx).delete()
            pdfFile(ctx).delete()
            File(dir(ctx), "draft.json.tmp").delete()
            File(dir(ctx), "source.pdf.tmp").delete()
        }
    }

    private fun rectToJson(r: Rect) =
        JSONArray().put(r.x0.toDouble()).put(r.y0.toDouble()).put(r.x1.toDouble()).put(r.y1.toDouble())

    private fun rectFromJson(a: JSONArray?): Rect? {
        if (a == null || a.length() < 4) return null
        return Rect(
            a.getDouble(0).toFloat(), a.getDouble(1).toFloat(),
            a.getDouble(2).toFloat(), a.getDouble(3).toFloat()
        )
    }
}
