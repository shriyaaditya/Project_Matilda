import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Project Matilda — Historical Representation Auditor',
  description: 'AI-powered historical representation auditor for educational materials',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-900 text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
