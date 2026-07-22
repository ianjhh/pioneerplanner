import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PioneerPlanner",
  description: "Academic Advising & Prerequisite Graph Search",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} antialiased h-full`}>
      <body className="min-h-full flex flex-col bg-gray-50 text-gray-900">
        <header className="bg-white border-b shadow-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex-shrink-0 flex items-center">
                <Link href="/" className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
                  PioneerPlanner
                </Link>
              </div>
              <nav className="flex space-x-8">
                <Link href="/" className="text-gray-500 hover:text-gray-900 inline-flex items-center px-1 pt-1 font-medium transition-colors">
                  Search
                </Link>
                <Link href="/graph" className="text-gray-500 hover:text-gray-900 inline-flex items-center px-1 pt-1 font-medium transition-colors">
                  Prerequisites
                </Link>
                <Link href="/chat" className="text-gray-500 hover:text-gray-900 inline-flex items-center px-1 pt-1 font-medium transition-colors">
                  AI Chat
                </Link>
              </nav>
            </div>
          </div>
        </header>
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </body>
    </html>
  );
}
