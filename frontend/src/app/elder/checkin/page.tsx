'use client';

import { useElderStore } from '@/store/elderStore';
import ElderHeader from '@/components/elder/ElderHeader';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { Button } from '@/components/ui/button';

export default function ElderCheckinPage() {
  const { checkIn, updateCheckIn, completeCheckIn } = useElderStore();

  return (
    <AuthGuard allowedRoles={['elder']}>
      <div className="min-h-screen bg-elder-bg">
        <ElderHeader />
        <main className="mx-auto max-w-3xl px-4 py-6 space-y-5">
          <div className="card-elevated rounded-3xl p-5">
            <h1 className="font-heading text-2xl font-semibold text-foreground mb-2">Daily Check-in</h1>
            <p className="text-sm text-muted-foreground">Keep your wellness score updated by answering the quick daily check-in questions.</p>
          </div>

          {checkIn.questions.map((question) => (
            <div key={question.id} className="card-elevated rounded-3xl p-5">
              <p className="text-sm text-muted-foreground mb-3">{question.category.toUpperCase()}</p>
              <h2 className="font-semibold text-foreground mb-4">{question.question}</h2>
              <div className="grid gap-3 sm:grid-cols-3">
                {['Yes', 'No', 'Maybe'].map((answer) => (
                  <Button
                    key={answer}
                    variant={question.answer === answer ? 'secondary' : 'outline'}
                    onClick={() => updateCheckIn(question.id, answer, answer === 'Yes' ? 8 : answer === 'Maybe' ? 5 : 2)}
                  >
                    {answer}
                  </Button>
                ))}
              </div>
            </div>
          ))}

          <div className="flex justify-end">
            <Button onClick={completeCheckIn}>Complete check-in</Button>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
