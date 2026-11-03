package com.neurotracee.pdfmask

import androidx.compose.ui.test.click
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.longClick
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.unit.dp
import com.neurotracee.pdfmask.ui.AboutPanel
import com.neurotracee.pdfmask.ui.PdfMaskTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/**
 * 回归：关于页的赞赏码必须真的响应长按。
 *
 * 1.4.0 的 bug 是文案写着「长按图片可保存」，但 Image 上从来没挂过长按手势，
 * 用户长按毫无反应。这里用真实控件把长按走到回调上，防止再退化。
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-xhdpi")
class ThanksQrLongPressTest {

    @get:Rule
    val compose = createComposeRule()

    @Test
    fun longPressOnThanksQr_triggersSave() {
        var hits = 0
        compose.setContent {
            PdfMaskTheme {
                AboutPanel(
                    onClose = {},
                    maxHeight = 2400.dp,
                    thanksOnLongPress = { hits++ }
                )
            }
        }

        compose.onNodeWithContentDescription("赞赏码")
            .performScrollTo()
            .performTouchInput { longClick() }
        compose.waitForIdle()

        assertEquals("长按赞赏码应触发一次保存", 1, hits)
    }

    @Test
    fun shortTapOnThanksQr_doesNothing() {
        var hits = 0
        compose.setContent {
            PdfMaskTheme {
                AboutPanel(
                    onClose = {},
                    maxHeight = 2400.dp,
                    thanksOnLongPress = { hits++ }
                )
            }
        }

        compose.onNodeWithContentDescription("赞赏码")
            .performScrollTo()
            .performTouchInput { click() }
        compose.waitForIdle()

        assertEquals("单击不应触发保存", 0, hits)
    }
}
