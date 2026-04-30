import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "스마트올 AI 학습코치",
  description: "웅진 스마트올 화면 위에 얹히는 AI 학습코치 T11 프론트엔드 목업",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
