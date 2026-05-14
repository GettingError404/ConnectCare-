
# ConnectedCare+ Frontend — Implementation Plan

## Design System
- **Elder side**: Warm, calm, large text, soft greens/blues, accessible, voice-first
- **Family side**: Professional SaaS dashboard, clean navy/teal palette, data-dense
- **Font**: Plus Jakarta Sans (headings), Inter (body)
- **Colors**: Primary teal `#0D9488`, Elder accent `#22C55E`, Alert red `#EF4444`, Warning amber `#F59E0B`, Background `#F8FAFC`

## Phase 1: Foundation
1. Design system setup (index.css, tailwind.config.ts)
2. State management with Zustand stores (auth, elder, family, reminders, vitals, mood, alerts, smart-home, chat, check-ins, emergency, relationships)
3. Mock data & services (users, vitals, reminders, alerts, chat history)
4. Auth system (login, register, role selection, mock auth service)
5. Route guards & role-based routing

## Phase 2: Elder Dashboard
6. Elder layout with voice-first design
7. Voice system (Web Speech API STT/TTS, intent recognition, continuous loop)
8. AI companion with contextual responses
9. Reminders system (medication, hydration, appointments, movement)
10. Daily health micro-check-ins (conversational voice flow)
11. Mood & emotional wellness (journaling, sentiment detection, interventions)
12. Engagement tools (trivia, exercises, Wellness Stars rewards)
13. RPM vitals dashboard (heart rate, BP, glucose, activity, fall detection)
14. Smart home controls (lights, locks, thermostat, automations)
15. SOS emergency system

## Phase 3: Family Dashboard
16. Family layout (sidebar, header, elder switcher)
17. Family dashboard overview (elder summary, health cards, insights)
18. Alert management system (severity levels, actions, history)
19. 24-hour chat visibility panel
20. Activity timeline
21. Emergency & telehealth section
22. Smart home & safety overview
23. RPM device overview
24. Reports & trends

## Phase 4: Integration
25. Cross-module event system (elder actions → family alerts)
26. Relationship management (elder ↔ family linking)
27. Polish, transitions, loading states, empty states
