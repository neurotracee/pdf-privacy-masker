# PDFBox 大量使用反射与运行时类型判断，保留其全部类
-keep class org.apache.pdfbox.** { *; }
-keep class com.tom_roush.** { *; }
-dontwarn org.apache.pdfbox.**
-dontwarn com.tom_roush.**
-dontwarn org.bouncycastle.**
-dontwarn javax.**
