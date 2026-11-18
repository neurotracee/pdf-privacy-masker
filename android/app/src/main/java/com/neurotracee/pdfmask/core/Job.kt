package com.neurotracee.pdfmask.core

/**
 * 用户点了「停止」。工作线程把它抛到最外层，界面据此退回干净状态。
 *
 * 继承 [RuntimeException] 而不是 [InterruptedException]：处理管线里到处是
 * `catch (t: Throwable)` 的兜底，用独立的类型才好在那些地方一眼认出「这是
 * 用户主动停的，不是处理出错」，顺手 rethrow 出去。
 */
class JobCancelled : RuntimeException("stopped by user")

/**
 * 一个长任务（识别 / 打码）的暂停、停止开关。
 *
 * 工作线程在**安全点**调 [checkpoint]：暂停时在那里等，停止时直接抛
 * [JobCancelled]。之所以不用协程的 `cancel()`，是因为真正耗时的
 * [OcrEngine] / [PdfMasker] 是同步函数（onnxruntime、PDFBox 都是阻塞调用），
 * 里面没有挂起点，协程取消只能在页与页之间生效；用阻塞式 checkpoint 才能
 * 做到「这一页做完就停」，语义更好解释，也不会把 ONNX 的 native 调用打断。
 *
 * 线程安全：所有字段都是 @Volatile 或由 [lock] 保护，可以从任意线程调。
 */
class JobControl {

    @Volatile
    var paused: Boolean = false
        private set

    @Volatile
    var stopped: Boolean = false
        private set

    private val lock = Object()

    fun pause() {
        if (stopped) return
        paused = true
    }

    fun resume() {
        synchronized(lock) {
            if (stopped) return
            paused = false
            lock.notifyAll()
        }
    }

    fun stop() {
        synchronized(lock) {
            stopped = true
            paused = false
            lock.notifyAll()
        }
    }

    /**
     * 安全点：暂停时原地等（每 120ms 醒一次，保证 stop 能及时生效），
     * 停止时抛 [JobCancelled]。
     */
    fun checkpoint() {
        while (true) {
            if (stopped) throw JobCancelled()
            if (!paused) return
            synchronized(lock) {
                if (paused && !stopped) {
                    try {
                        lock.wait(120)
                    } catch (_: InterruptedException) {
                        // 被外部打断：按停止处理，别把异常漏给上层
                        Thread.currentThread().interrupt()
                        throw JobCancelled()
                    }
                }
            }
        }
    }

    /** 供「渲染一页要很久」的循环用：只在没暂停没停止时才继续，不阻塞 */
    val running: Boolean get() = !paused && !stopped
}
