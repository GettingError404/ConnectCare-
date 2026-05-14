'use client';

import { forwardRef } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { cn } from '@/lib/utils';

export interface NavLinkCompatProps {
  to: string;
  className?: string;
  activeClassName?: string;
  pendingClassName?: string;
  children?: React.ReactNode;
  ariaLabel?: string;
}

const NavLink = forwardRef<HTMLAnchorElement, NavLinkCompatProps>(
  ({ className, activeClassName, pendingClassName, to, children, ariaLabel }, ref) => {
    const pathname = usePathname();

    const isActive = pathname === to || (to !== '/' && pathname?.startsWith(to));

    return (
      <Link
        ref={ref}
        href={to}
        aria-label={ariaLabel}
        className={cn(className, isActive && activeClassName, pendingClassName)}
      >
        {children}
      </Link>
    );
  },
);

NavLink.displayName = 'NavLink';

export { NavLink };

