import type { Metadata } from 'next';
import TopNavigation from '@/components/navigation/TopNavigation';
import './globals.css';

export const metadata: Metadata = {
  title: 'Matilda — Historical Representation & Attribution Intelligence',
  description: 'Academic document intelligence system for identifying historical attribution issues, missing context, credit displacement, and representation gaps.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-screen bg-[#FAF8F5] text-[#1C1917] flex flex-col antialiased selection:bg-[#FEE2E2] selection:text-[#991B1B]">
        <TopNavigation />
        <main className="flex-1 flex flex-col min-h-0">{children}</main>
      </body>
    </html>
  );
}
