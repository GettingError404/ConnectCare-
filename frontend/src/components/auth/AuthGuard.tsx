'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import type { UserRole } from '@/types';

interface AuthGuardProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export function AuthGuard({ children, allowedRoles }: AuthGuardProps) {
  const router = useRouter();
  const [isMounted, setIsMounted] = useState(false);
  const { isAuthenticated, user } = useAuthStore();

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMounted) return;

    if (!isAuthenticated || !user) {
      router.replace('/login');
      return;
    }

    if (allowedRoles && !allowedRoles.includes(user.role)) {
      const redirectPath = user.role === 'elder' ? '/elder' : user.role === 'caregiver' ? '/caregiver' : '/family/dashboard';
      router.replace(redirectPath);
    }
  }, [isMounted, isAuthenticated, user, allowedRoles, router]);

  if (!isMounted) {
    return null;
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}
