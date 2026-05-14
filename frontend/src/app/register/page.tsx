'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Heart, Mail, Lock, User as UserIcon, ArrowLeft, Eye, EyeOff, Stethoscope, Users, User, Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import { toast } from 'sonner';
import type { UserRole } from '@/types';

const registrationSchema = z.object({
  name: z.string().min(2, 'Enter your full name'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  age: z.preprocess((value) => Number(value), z.number().min(50).max(120).optional()),
  relationship: z.string().optional(),
  title: z.string().optional(),
  specialty: z.string().optional(),
});

type RegistrationFormValues = z.infer<typeof registrationSchema>;

const roleOptions: { id: UserRole; icon: React.ElementType; title: string; desc: string }[] = [
  { id: 'elder', icon: User, title: 'I am an Elder', desc: 'Voice-first care, reminders, wellness tracking, and an AI companion.' },
  { id: 'family', icon: Users, title: 'I am a Family Member', desc: 'Monitor health, receive alerts, and manage care remotely.' },
  { id: 'caregiver', icon: Stethoscope, title: 'I am a Caregiver', desc: 'Doctors, nurses, and health workers managing patients.' },
];

export default function RegisterPage() {
  const router = useRouter();
  const [step, setStep] = useState<'role' | 'details'>('role');
  const [role, setRole] = useState<UserRole | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const { register: registerUser, error, clearError, isLoading } = useAuthStore();

  const { register, handleSubmit, watch, setError, formState: { errors } } = useForm<RegistrationFormValues>({
    resolver: zodResolver(registrationSchema),
  });

  const password = watch('password') || '';
  const passwordStrength = password.length === 0 ? 0 : password.length < 6 ? 1 : password.length < 10 ? 2 : 3;
  const strengthLabel = ['', 'Weak', 'Good', 'Strong'][passwordStrength];
  const strengthColor = ['bg-muted', 'bg-destructive', 'bg-warning', 'bg-success'][passwordStrength];

  const onSubmit = async (values: RegistrationFormValues) => {
    if (!role) return;
    clearError();

    const success = await registerUser(values.name, values.email, values.password, role, {
      age: values.age,
      relationship: values.relationship,
      title: values.title,
      specialty: values.specialty,
    });

    if (!success) {
      setError('password', { type: 'manual', message: error || 'Unable to create account' });
      return;
    }

    toast.success('Account created — welcome!');
    if (role === 'elder') router.push('/elder');
    else if (role === 'caregiver') router.push('/caregiver/dashboard');
    else router.push('/family/dashboard');
  };

  if (step === 'role') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4 py-8">
        <div className="w-full max-w-2xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10 mb-3">
              <Heart className="w-7 h-7 text-primary" />
            </div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-foreground">Join ConnectedCare+</h1>
            <p className="text-muted-foreground mt-2 text-sm">Choose how you'll be using the platform</p>
          </div>

          <div className="grid sm:grid-cols-3 gap-3 sm:gap-4">
            {roleOptions.map((option) => {
              const Icon = option.icon;
              return (
                <button key={option.id} type="button" onClick={() => { setRole(option.id); setStep('details'); }} className="bg-card rounded-2xl border-2 border-border hover:border-primary p-5 text-left transition-all group focus-ring shadow-sm hover:shadow-md">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                    <Icon className="w-6 h-6" />
                  </div>
                  <h3 className="font-heading text-base font-semibold text-foreground">{option.title}</h3>
                  <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{option.desc}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-8 text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/login" className="text-primary font-medium hover:underline">Sign in</Link>
          </div>
        </div>
      </div>
    );
  }

  const RoleIcon = roleOptions.find((r) => r.id === role)?.icon ?? UserIcon;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 py-8">
      <div className="w-full max-w-md">
        <button onClick={() => setStep('role')} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors focus-ring rounded-md px-2 py-1 -ml-2">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="bg-card rounded-2xl shadow-sm border border-border p-6 sm:p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-11 h-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <RoleIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-bold text-foreground">
                {role === 'elder' ? 'Elder Registration' : role === 'caregiver' ? 'Caregiver Registration' : 'Family Member Registration'}
              </h2>
              <p className="text-xs text-muted-foreground">Step 2 of 2</p>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {(error || errors.name || errors.email || errors.password) && (
              <div role="alert" className="bg-destructive/10 text-destructive text-sm rounded-lg p-3 border border-destructive/20">
                {errors.name?.message || errors.email?.message || errors.password?.message || error}
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="name" className="text-sm font-medium">Full name</label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input id="name" placeholder="Your full name" className="pl-10 h-11" {...register('name')} />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input id="email" type="email" autoComplete="email" inputMode="email" placeholder="you@example.com" className="pl-10 h-11" {...register('email')} />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input id="password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" placeholder="At least 6 characters" className="pl-10 pr-10 h-11" {...register('password')} />
                <button type="button" onClick={() => setShowPassword((current) => !current)} aria-label={showPassword ? 'Hide password' : 'Show password'} className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors focus-ring">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {password.length > 0 && (
                <div className="flex items-center gap-2 pt-1">
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className={`h-full transition-all ${strengthColor}`} style={{ width: `${(passwordStrength / 3) * 100}%` }} />
                  </div>
                  <span className="text-[10px] text-muted-foreground font-medium w-12 text-right">{strengthLabel}</span>
                </div>
              )}
            </div>

            {role === 'elder' && (
              <div className="space-y-1.5">
                <label htmlFor="age" className="text-sm font-medium">Age</label>
                <Input id="age" type="number" inputMode="numeric" placeholder="Your age" className="h-11" {...register('age')} />
              </div>
            )}

            {role === 'family' && (
              <div className="space-y-1.5">
                <label htmlFor="relationship" className="text-sm font-medium">Relationship to elder</label>
                <Input id="relationship" placeholder="e.g. Daughter, Son, Spouse" className="h-11" {...register('relationship')} />
              </div>
            )}

            {role === 'caregiver' && (
              <>
                <div className="space-y-1.5">
                  <label htmlFor="title" className="text-sm font-medium">Title / role</label>
                  <Input id="title" placeholder="e.g. Doctor, Nurse, Health Worker" className="h-11" {...register('title')} />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="specialty" className="text-sm font-medium">Specialty <span className="text-muted-foreground font-normal">(optional)</span></label>
                  <Input id="specialty" placeholder="e.g. Geriatric Medicine" className="h-11" {...register('specialty')} />
                </div>
              </>
            )}

            <Button type="submit" className="w-full h-11 text-base font-semibold mt-2" disabled={isLoading}>
              {isLoading ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Creating account…</> : <><Check className="w-5 h-5 mr-2" /> Create account</>}
            </Button>

            <p className="text-[11px] text-muted-foreground text-center pt-1">By continuing you agree to our Terms and Privacy Policy.</p>
          </form>
        </div>
      </div>
    </div>
  );
}
