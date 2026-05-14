import type { Metadata } from 'next';
import { Providers } from './providers';
import '@/app/globals.css';
import enMessages from '@/messages/en.json';

export const metadata: Metadata = {
  title: 'ConnectedCare+',
  description: 'ConnectedCare+ eldercare platform for families, caregivers, and elders.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
