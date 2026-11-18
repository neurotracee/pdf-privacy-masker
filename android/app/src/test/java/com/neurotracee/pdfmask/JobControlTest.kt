package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.JobCancelled
import com.neurotracee.pdfmask.core.JobControl
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/**
 * 暂停 / 停止开关的行为：它是「进度面板能不能真的停下」的底层保证，
 * 所以单独测一遍——界面看着停了、后台还在跑，比不提供按钮更糟。
 */
class JobControlTest {

    @Test
    fun checkpoint_is_free_when_running() {
        val j = JobControl()
        repeat(1000) { j.checkpoint() }
        assertTrue(j.running)
    }

    @Test
    fun pause_holds_the_worker_until_resume() {
        val j = JobControl()
        val done = CountDownLatch(1)
        val reached = CountDownLatch(1)
        val t = Thread {
            j.pause()
            reached.countDown()
            j.checkpoint()          // 应该在这里等
            done.countDown()
        }
        t.start()
        assertTrue(reached.await(2, TimeUnit.SECONDS))
        // 已经进到 checkpoint 里了，这时不该放行
        assertTrue("暂停期间 checkpoint 不能返回", !done.await(400, TimeUnit.MILLISECONDS))
        j.resume()
        assertTrue("继续之后应该放行", done.await(2, TimeUnit.SECONDS))
        t.join(2000)
    }

    @Test
    fun stop_throws_from_checkpoint() {
        val j = JobControl()
        j.stop()
        val err = AtomicReference<Throwable?>(null)
        try {
            j.checkpoint()
        } catch (t: Throwable) {
            err.set(t)
        }
        assertTrue(err.get() is JobCancelled)
    }

    @Test
    fun stop_wakes_a_paused_worker_instead_of_hanging() {
        val j = JobControl()
        val caught = CountDownLatch(1)
        val err = AtomicReference<Throwable?>(null)
        val t = Thread {
            j.pause()
            try {
                j.checkpoint()
            } catch (x: Throwable) {
                err.set(x)
                caught.countDown()
            }
        }
        t.start()
        Thread.sleep(150)           // 让它先进到 wait 里
        j.stop()
        assertTrue("停止必须把等待中的线程叫醒", caught.await(2, TimeUnit.SECONDS))
        assertTrue(err.get() is JobCancelled)
        assertEquals(false, j.paused)
        assertEquals(true, j.stopped)
        t.join(2000)
    }

    @Test
    fun resume_after_stop_does_not_revive_the_job() {
        val j = JobControl()
        j.stop()
        j.resume()
        assertEquals(true, j.stopped)
        assertEquals(false, j.paused)
    }

    @Test
    fun pause_after_stop_is_ignored() {
        val j = JobControl()
        j.stop()
        j.pause()
        assertEquals(false, j.paused)
    }
}
