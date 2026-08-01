import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

// 刻意不使用 next/font/google：CI 与离线构建环境不应依赖外部字体下载。
export const metadata: Metadata = {
  title: "企业级 RAG 智能助手",
  description: "带引用与权限控制的企业知识库问答系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
