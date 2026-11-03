package com.neurotracee.pdfmask.ui

import androidx.compose.runtime.Composable
import com.neurotracee.pdfmask.AppPrefs

/**
 * 界面文案取值：默认中文，设置里切成英文后立即生效。
 * 用法：T("选择 PDF 文件", "Choose a PDF")
 */
@Composable
fun T(zh: String, en: String): String = if (AppPrefs.isEn) en else zh

/** 非 Composable 场景的版本 */
fun t(zh: String, en: String): String = if (AppPrefs.isEn) en else zh
