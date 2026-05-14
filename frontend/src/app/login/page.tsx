'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Heart, Mail, Lock, Loader2, Eye, EyeOff, Stethoscope, Users, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import { toast } from 'sonner';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const { login, error, clearError, isLoading } = useAuthStore();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (values: LoginFormValues) => {
    clearError();
    const success = await login(values.email, values.password);
    if (!success) {
      setError('password', { type: 'manual', message: error || 'Invalid email or password' });
      return;
    }
    const user = useAuthStore.getState().user;
    toast.success(`Welcome back, ${user?.name?.split(' ')[0] ?? ''}`);
    if (user?.role === 'elder') router.push('/elder');
    else if (user?.role === 'caregiver') router.push('/caregiver/dashboard');
    else router.push('/family/dashboard');
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <aside className="hidden lg:flex flex-col justify-between p-10 bg-family-sidebar text-family-sidebar-foreground relative overflow-hidden">
        <div className="absolute inset-0 opacity-30 pointer-events-none" style={{ background: 'radial-gradient(circle at 20% 20%, hsl(184 64% 44% / 0.4), transparent 60%), radial-gradient(circle at 80% 80%, hsl(212 76% 50% / 0.3), transparent 55%)' }} />
        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-primary/20 flex items-center justify-center">
              <Heart className="w-6 h-6 text-family-sidebar-active" />
            </div>
            <span className="font-heading text-xl font-bold">ConnectedCare+</span>
          </div>
        </div>

        <div className="relative space-y-6 max-w-md">
          <h2 className="font-heading text-3xl xl:text-4xl font-bold leading-tight">A calmer way to care for the people you love.</h2>
          <p className="text-sm text-family-sidebar-foreground/70 leading-relaxed">Real-time health monitoring, intelligent alerts, and a voice-first experience built for elders, families, and care teams.</p>
          <div className="grid grid-cols-3 gap-3 pt-4">
            {[
              { label: 'Patients monitored', value: '12k+' },
              { label: 'Alerts handled', value: '99.9%' },
              { label: 'Care teams', value: '500+' },
            ].map((stat) => (
              <div key={stat.label} className="rounded-xl border border-sidebar-border bg-sidebar-accent/40 p-3">
                <p className="font-heading text-lg font-bold text-family-sidebar-active">{stat.value}</p>
                <p className="text-[10px] text-family-sidebar-foreground/60 leading-tight">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-xs text-family-sidebar-foreground/50">© ConnectedCare+ — secure healthcare platform</p>
      </aside>

      <main className="flex items-center justify-center p-4 sm:p-6 md:p-10">
        <div className="w-full max-w-md">
          <div className="text-center mb-6 lg:hidden">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 mb-3">
              <Heart className="w-7 h-7 text-primary" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-foreground">ConnectedCare+</h1>
          </div>

          <div className="hidden lg:block mb-6">
            <h1 className="font-heading text-2xl font-bold text-foreground">Sign in</h1>
            <p className="text-sm text-muted-foreground mt-1">Welcome back. Enter your details to continue.</p>
          </div>

          <div className="bg-card rounded-2xl shadow-sm border border-border p-6 sm:p-8">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
              {(error || errors.email || errors.password) && (
                <div role="alert" className="bg-destructive/10 text-destructive text-sm rounded-lg p-3 border border-destructive/20">
                  {errors.email?.message || errors.password?.message || error}
                </div>
              )}

              <div className="space-y-1.5">
                <label htmlFor="email" className="text-sm font-medium text-foreground">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  <Input id="email" type="email" autoComplete="email" inputMode="email" placeholder="you@example.com" className="pl-10 h-11" {...register('email')} />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="text-sm font-medium text-foreground">Password</label>
                  <button type="button" className="text-xs text-primary hover:underline">Forgot?</button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  <Input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="••••••••" className="pl-10 pr-10 h-11" {...register('password')} />
                  <button type="button" onClick={() => setShowPassword((current) => !current)} aria-label={showPassword ? 'Hide password' : 'Show password'} className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors focus-ring">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <Button type="submit" className="w-full h-11 text-base font-semibold" disabled={isLoading}>
                {isLoading ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Signing in…</> : 'Sign in'}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-muted-foreground">
              New to ConnectedCare+?{' '}
              <Link href="/register" className="text-primary font-medium hover:underline">Create account</Link>
            </div>

            <div className="mt-6 pt-5 border-t border-border">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground text-center mb-3 font-medium">Demo accounts</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[
                  { label: 'Elder', email: 'elder@example.com', pw: 'elder123', Icon: User },
                  { label: 'Family', email: 'family@example.com', pw: 'family123', Icon: Users },
                  { label: 'Caregiver', email: 'caregiver@example.com', pw: 'care123', Icon: Stethoscope },
                ].map((demo) => (
                  <button key={demo.label} type="button" onClick={() => {
                    const emailField = document.getElementById('email') as HTMLInputElement | null;
                    const passwordField = document.getElementById('password') as HTMLInputElement | null;
                    if (emailField) emailField.value = demo.email;
                    if (passwordField) passwordField.value = demo.pw;
                  }} className="flex items-center justify-center gap-1.5 text-xs bg-accent text-accent-foreground rounded-lg p-2.5 hover:bg-accent/80 transition-colors focus-ring font-medium">
                    <demo.Icon className="w-3.5 h-3.5" />
                    {demo.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
