/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from "next";
import { DM_Sans } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { AppShell } from "@/components/layout/app-shell";
import { Toaster } from "sonner";
import { CommandPalette } from "@/components/ui/command-palette";

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "OVAL — Brand Intelligence Platform",
  description: "See what they say before it spreads. Brand intelligence across Instagram, Reddit, YouTube, Telegram, and Google.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,400;0,700;1,400;1,700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={`${dmSans.variable} font-sans antialiased`}>
        <ThemeProvider>
          <a href="#main-content" className="skip-link">Skip to main content</a>
          <AppShell>{children}</AppShell>
          <Toaster position="bottom-right" richColors closeButton />
          <CommandPalette />
        </ThemeProvider>
      </body>
    </html>
  );
}
