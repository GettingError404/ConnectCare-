import { Reminder, VitalSign, CheckInSession, SmartDevice, FamilyContact, GameSession, CallState } from '@/types';

const greetings = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
};

export interface IntentResult {
  intent: string;
  response: string;
  action?: string;
  data?: unknown;
}


interface IntentContext {
  reminders?: Reminder[];
  name?: string;
  vitals?: VitalSign[];
  checkIn?: CheckInSession;
  smartDevices?: SmartDevice[];
  familyContacts?: FamilyContact[];
  gameSession?: GameSession;
  callState?: CallState;
}

export function detectIntent(text: string, context?: IntentContext): IntentResult {
  const lower = text.toLowerCase().trim();
  const name = context?.name || 'dear';
  const game = context?.gameSession;


  // === ACTIVE GAME ANSWER HANDLING (highest priority when game is active) ===
  if (game && game.status === 'active') {
    // Stop/quit game
    if (/^(stop|quit|exit|end|cancel)\s*(game|playing|quiz)?$/i.test(lower)) {
      return { intent: 'end_game', response: `No problem, ${name}! We'll stop the game. Your score was ${game.score}. Want to do something else?`, action: 'end_game' };
    }
    // Skip question
    if (/^(skip|pass|next|i\s*don'?t\s*know|no\s*idea)$/i.test(lower)) {
      return { intent: 'game_answer', response: '', action: 'game_answer', data: { answer: '__SKIP__', skipped: true } };
    }
    // Hint request
    if (/hint|clue|help\s*me/.test(lower) && game.type === 'word' && game.wordData) {
      return { intent: 'game_hint', response: `Here's your hint: ${game.wordData.hint}. The word has ${game.wordData.answer.length} letters. Take your time!` };
    }
    // Treat as game answer
    return { intent: 'game_answer', response: '', action: 'game_answer', data: { answer: text } };
  }

  // === MUSIC PLAYBACK CONTROLS (high priority when music is playing) ===
  if (/^(pause|resume)\s*(music|song|playback)?$/i.test(lower)) {
    return { intent: 'music_control', response: lower.includes('pause') ? `Pausing the music, ${name}. Say "resume" to continue.` : `Resuming the music, ${name}! 🎵`, action: 'toggle_music' };
  }
  if (/^(next|skip)\s*(song|track|music)?$/i.test(lower)) {
    return { intent: 'music_control', response: `Playing the next track, ${name}! 🎵`, action: 'next_track' };
  }
  if (/^(previous|back|go\s*back)\s*(song|track)?$/i.test(lower)) {
    return { intent: 'music_control', response: `Going back, ${name}!`, action: 'prev_track' };
  }
  if (/^(stop|close|end)\s*(music|song|playback|playing)$/i.test(lower)) {
    return { intent: 'music_control', response: `Stopping the music, ${name}. What would you like to do next?`, action: 'stop_music' };
  }

  // === NAVIGATION INTENTS ===
  if (/^(go\s*to|open|show\s*me|navigate\s*to|switch\s*to|take\s*me\s*to)\s*(the\s*)?(reminder|medicine|medication|pill)\s*(page|tab|section|screen)?/i.test(lower) ||
      /^(show|check|view|see)\s*(my\s*)?(reminder|medicine|medication)s?$/i.test(lower)) {
    return { intent: 'navigate', response: `Opening your reminders, ${name}.`, action: 'navigate_reminders' };
  }
  if (/^(go\s*to|open|show\s*me|navigate\s*to|switch\s*to|take\s*me\s*to)\s*(the\s*)?(health|vital|heart|blood|glucose)\s*(page|tab|section|screen)?/i.test(lower) ||
      /^(show|check|view|see)\s*(my\s*)?(health|vital|heart|blood)s?$/i.test(lower)) {
    return { intent: 'navigate', response: `Opening your health vitals, ${name}.`, action: 'navigate_health' };
  }
  if (/^(go\s*to|open|show\s*me|navigate\s*to|switch\s*to|take\s*me\s*to)\s*(the\s*)?(home|smart\s*home|device|light|thermostat)\s*(page|tab|section|screen)?/i.test(lower)) {
    return { intent: 'navigate', response: `Opening smart home controls, ${name}.`, action: 'navigate_home' };
  }
  if (/^(go\s*to|open|show\s*me|navigate\s*to|switch\s*to|take\s*me\s*to)\s*(the\s*)?(talk|chat|companion|conversation)\s*(page|tab|section|screen)?/i.test(lower) ||
      /^go\s*back$/i.test(lower)) {
    return { intent: 'navigate', response: `Going back to the conversation, ${name}.`, action: 'navigate_companion' };
  }

  // === GREETINGS ===
  if (/^(hi|hello|hey|good\s*(morning|afternoon|evening))/.test(lower)) {
    const upcoming = context?.reminders?.filter(r => r.status === 'upcoming') || [];
    const missed = context?.reminders?.filter(r => r.status === 'missed') || [];
    let extra = '';
    if (upcoming.length > 0) extra += ` You have ${upcoming.length} upcoming reminder${upcoming.length > 1 ? 's' : ''}.`;
    if (missed.length > 0) extra += ` ⚠️ You have ${missed.length} missed reminder${missed.length > 1 ? 's' : ''}.`;
    return { intent: 'greeting', response: `${greetings()}, ${name}! I'm here to help you today. 😊${extra}` };
  }

  // === REMINDERS ===
  if (/remind|medicine|medication|pill|tablet/.test(lower)) {
    const upcoming = context?.reminders?.filter(r => r.status === 'upcoming' && r.type === 'medication') || [];
    const missed = context?.reminders?.filter(r => r.status === 'missed') || [];
    if (/mark.*done|taken|completed|took|i\s*(took|had|finished)/.test(lower)) {
      return { intent: 'mark_medicine', response: `Great job taking your medicine, ${name}! I've marked it as completed. 🌟 You earned 5 wellness stars!`, action: 'mark_medicine_done' };
    }
    if (/mark.*all|all.*done/.test(lower)) {
      return { intent: 'mark_all', response: `I've marked all your upcoming reminders as done, ${name}! Great work! 🌟`, action: 'mark_all_reminders_done' };
    }
    if (/what|any|do i have|next|upcoming|when/.test(lower)) {
      if (upcoming.length > 0) {
        const list = upcoming.map(r => r.title).join(', ');
        return { intent: 'check_reminders', response: `You have ${upcoming.length} upcoming medication${upcoming.length > 1 ? 's' : ''}: ${list}. Would you like me to remind you when it's time?`, action: 'show_reminders' };
      }
      return { intent: 'check_reminders', response: `All your medications are taken care of for now, ${name}! Well done! 🌟` };
    }
    if (missed.length > 0) {
      return { intent: 'missed_meds', response: `You have ${missed.length} missed medication${missed.length > 1 ? 's' : ''}: ${missed.map(r => r.title).join(', ')}. Would you like to take ${missed.length === 1 ? 'it' : 'them'} now?`, action: 'navigate_reminders' };
    }
    if (upcoming.length > 0) {
      return { intent: 'check_reminders', response: `You have ${upcoming.length} upcoming medication${upcoming.length > 1 ? 's' : ''}: ${upcoming.map(r => r.title).join(', ')}. Would you like me to remind you later?`, action: 'show_reminders' };
    }
    return { intent: 'check_reminders', response: `All your medications are taken care of for now, ${name}! Well done! 🌟` };
  }

  if (/remind.*later|snooze|not now|later/.test(lower)) {
    return { intent: 'snooze_reminder', response: `No problem, ${name}! I'll remind you again in 30 minutes.`, action: 'snooze_reminder' };
  }

  // === HEALTH / VITALS ===
  if (/health|vital|blood\s*pressure|heart\s*rate|glucose|sugar|how\s*(am|is)\s*(my|i)\s*(doing|health)/.test(lower)) {
    const vitalsSummary = context?.vitals;
    if (vitalsSummary && vitalsSummary.length > 0) {
      const hr = vitalsSummary.find(v => v.type === 'heart_rate');
      const bp = vitalsSummary.find(v => v.type === 'blood_pressure');
      const gl = vitalsSummary.find(v => v.type === 'glucose');
      const steps = vitalsSummary.find(v => v.type === 'activity');
      const warnings = vitalsSummary.filter(v => v.status !== 'normal');
      let resp = `Here's your health summary, ${name}: `;
      if (hr) resp += `Heart rate is ${hr.value} ${hr.unit} — ${hr.status}. `;
      if (bp) resp += `Blood pressure is ${bp.value} ${bp.unit} — ${bp.status}. `;
      if (gl) resp += `Glucose is ${gl.value} ${gl.unit} — ${gl.status}. `;
      if (steps) resp += `Steps today: ${steps.value}. `;
      if (warnings.length > 0) resp += `⚠️ ${warnings.length} reading${warnings.length > 1 ? 's' : ''} need${warnings.length === 1 ? 's' : ''} attention. `;
      resp += `Would you like to see the details?`;
      return { intent: 'health_summary', response: resp, action: 'navigate_health' };
    }
    return { intent: 'health_summary', response: `Your vitals look stable, ${name}. Heart rate is normal and activity is on track. Would you like more details?`, action: 'navigate_health' };
  }

  // === CHECK-IN ===
  if (/check.?in|daily\s*check|how\s*am\s*i|start\s*(my\s*)?check/.test(lower)) {
    return { intent: 'start_checkin', response: `Let's do your daily check-in, ${name}! I'll ask you a few simple questions, one at a time. Just answer naturally. Here's the first one: How are you feeling emotionally right now?`, action: 'start_checkin' };
  }

  // === MOOD & EMOTIONAL ===
  if (/mood|feeling|emotion|sad|happy|lonely|anxious|worried|stressed|depressed|scared|frustrated|angry|upset/.test(lower)) {
    let sentiment: 'positive' | 'neutral' | 'negative' | 'risk' = 'neutral';
    let moodResponse = '';
    let triggers: string[] = [];
    if (/happy|great|wonderful|good|fantastic|amazing|excellent|blessed|grateful/.test(lower)) {
      sentiment = 'positive';
      moodResponse = `That's wonderful to hear, ${name}! I'm so glad you're feeling good. Your positive energy is inspiring! 🌟 You've earned 3 wellness stars.`;
    } else if (/sad|lonely|down|depressed|miss|alone|nobody|isolated/.test(lower)) {
      sentiment = 'negative'; triggers = ['loneliness', 'sadness'];
      if (/very|extremely|terribly|so\s+(sad|lonely|depressed)/.test(lower)) {
        sentiment = 'risk';
        moodResponse = `I hear you, ${name}. Those feelings are really hard. You're never truly alone — I'm here, and your family cares deeply about you. 💙 Would you like me to call Sarah? Or we could listen to some calming music together.`;
      } else {
        moodResponse = `I'm sorry you're feeling that way, ${name}. You're not alone — I'm here with you. Would you like to listen to some calming music, or talk about what's on your mind? 💙`;
      }
    } else if (/anxious|worried|scared|nervous|stressed|afraid|panic/.test(lower)) {
      sentiment = 'negative'; triggers = ['anxiety', 'stress'];
      moodResponse = `I understand, ${name}. Let's try something that might help. Take a slow breath in for 4 counts, hold for 4, and breathe out for 6 counts. I'll count with you. Would you like to try a breathing exercise together? 🍃`;
    } else if (/angry|frustrated|mad|upset|irritated/.test(lower)) {
      sentiment = 'negative'; triggers = ['frustration'];
      moodResponse = `I can see you're frustrated, ${name}. That's completely valid. Would you like to talk about it, or would you prefer a calming distraction like a story or some music?`;
    } else {
      moodResponse = `I've noted your mood, ${name}. How you feel matters — would you like to tell me more? I'm listening. 💛`;
    }
    return { intent: 'mood_log', response: moodResponse, action: 'log_mood', data: { sentiment, triggers, userText: text } };
  }

  // === NEW INTERACTIVE GAMES (navigate to games tab) ===
  if (/memory\s*match|match\s*(the\s*)?cards|find\s*(the\s*)?pairs|matching\s*game/.test(lower)) {
    return { intent: 'open_game', response: `Let's play Memory Match, ${name}! 🃏 Tap cards to find matching pairs. Take your time!`, action: 'navigate_games', data: { game: 'memory' } };
  }
  if (/word\s*clue|guess\s*the\s*word|word\s*game/.test(lower)) {
    return { intent: 'open_game', response: `Let's play Word Clue, ${name}! 📝 Listen to the clue and say the word!`, action: 'navigate_games', data: { game: 'word' } };
  }
  if (/color|colour|coloring|painting|draw|fill/.test(lower)) {
    return { intent: 'open_game', response: `Let's do some coloring, ${name}! 🎨 Pick a color and tap to fill!`, action: 'navigate_games', data: { game: 'coloring' } };
  }
  if (/club|friends|community|group|together|join\s*room/.test(lower)) {
    return { intent: 'open_club', response: `Opening the Senior Club, ${name}! 👥 Join a room to play with friends!`, action: 'navigate_games', data: { game: 'club' } };
  }

  // === EXISTING GAMES (quiz, memory sequence, word scramble) ===
  if (/memory\s*game|play\s*(a\s*)?memory/.test(lower)) {
    return { intent: 'start_game', response: `Let's play a memory game, ${name}! 🧠 I'll show you a sequence of items. Memorize them, and then tell me what you saw in order. Ready? Here we go!`, action: 'start_game', data: { gameType: 'memory' } };
  }
  if (/quiz|trivia|knowledge|test\s*me/.test(lower)) {
    return { intent: 'start_game', response: `Let's play a quiz, ${name}! 🧩 I'll ask you 5 questions. Say the answer or the letter (A, B, C, or D). Let's see how many you get right!`, action: 'start_game', data: { gameType: 'quiz' } };
  }
  if (/word\s*(puzzle|scramble)|unscramble|spelling/.test(lower)) {
    return { intent: 'start_game', response: `Let's play a word puzzle, ${name}! 🔤 I'll give you scrambled letters. Unscramble them to find the word. I'll give you hints too!`, action: 'start_game', data: { gameType: 'word' } };
  }
  if (/game|play\s*(a\s*)?game|brain|puzzle|riddle/.test(lower)) {
    if (/play\s*again|another|one\s*more/.test(lower)) {
      return { intent: 'start_game', response: `Let's go again, ${name}! Which game? Memory Match, Word Clue, Coloring, Quiz, or join the Senior Club?`, action: 'navigate_games' };
    }
    return { intent: 'show_games', response: `Great choice, ${name}! 🎮 I have games for you: Memory Match, Word Clue, Coloring, Quiz, Word Puzzle, and the Senior Club! Say a name or I'll open the games menu.`, action: 'navigate_games' };
  }

  // === MUSIC (enhanced with genres, artists, controls) ===
  if (/music|song|play\s*(some|a|me)?\s*(music|song|tune)|listen\s*to\s*(music|song)/.test(lower)) {
    if (/devotional|spiritual|prayer|bhajan|hymn/.test(lower)) {
      return { intent: 'play_music', response: `Playing soothing devotional music for you, ${name}. 🙏🎵 Let the peace flow through you.`, action: 'play_music', data: { genre: 'devotional' } };
    }
    if (/classical|piano|instrument|beethoven|mozart|debussy/.test(lower)) {
      return { intent: 'play_music', response: `Playing beautiful classical music, ${name}. 🎻 Close your eyes and enjoy.`, action: 'play_music', data: { genre: 'classical' } };
    }
    if (/nature|rain|ocean|bird|forest/.test(lower)) {
      return { intent: 'play_music', response: `Playing calming nature sounds for you, ${name}. 🌿🎵 Let nature soothe you.`, action: 'play_music', data: { genre: 'nature' } };
    }
    if (/old|retro|classic\s*hits|golden|frank\s*sinatra|louis\s*armstrong|oldies/.test(lower)) {
      return { intent: 'play_music', response: `Playing some golden oldies for you, ${name}! 🎶 The classics never get old.`, action: 'play_music', data: { genre: 'oldies' } };
    }
    if (/folk|country|john\s*denver/.test(lower)) {
      return { intent: 'play_music', response: `Playing some beautiful folk music, ${name}! 🎸 Enjoy the melodies.`, action: 'play_music', data: { genre: 'folk' } };
    }
    if (/calm|relax|peaceful|soft|gentle|soothing/.test(lower)) {
      return { intent: 'play_music', response: `Playing calming music for you, ${name}. 🧘 Let yourself relax.`, action: 'play_music', data: { genre: 'calm' } };
    }
    return { intent: 'play_music', response: `Playing some lovely music for you, ${name}. 🎵 Sit back and enjoy! Say "next" for the next track, "pause" to pause, or "stop music" to end.`, action: 'play_music', data: { genre: 'calm' } };
  }

  // === JOKES ===
  if (/joke|funny|make\s*me\s*laugh|humor/.test(lower)) {
    const jokes = [
      "Why don't scientists trust atoms? Because they make up everything! 😄",
      "What do you call a bear with no teeth? A gummy bear! 🐻",
      "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾",
      "What do you call a fish without eyes? A fsh! 🐟",
      "Why don't eggs tell jokes? They'd crack each other up! 🥚",
      "What did the ocean say to the beach? Nothing, it just waved! 🌊",
      "Why do cows wear bells? Because their horns don't work! 🐄",
    ];
    const joke = jokes[Math.floor(Math.random() * jokes.length)];
    return { intent: 'joke', response: `Here's one for you, ${name}: ${joke} Want to hear another?`, action: 'show_entertainment' };
  }

  // === EXERCISE ===
  if (/exercise|stretch|walk|move|mobility|yoga/.test(lower)) {
    return { intent: 'start_exercise', response: `Great idea, ${name}! Let's start with some gentle stretches. Roll your shoulders slowly 5 times, then stretch your arms above your head. Ready when you are! 🧘 You'll earn 5 stars when you finish.`, action: 'start_exercise' };
  }

  // === STORIES (enhanced) ===
  if (/story|stories|tell\s*me\s*(a|some)/.test(lower)) {
    if (/motivational|inspiring|courage/.test(lower)) {
      return { intent: 'story', response: `Here's a motivational story, ${name}: A 90-year-old woman was asked her secret to happiness. She said, "I wake up every morning and decide — today I will find joy in small things." She painted her first masterpiece at 87 and wrote a book at 92. She said, "Age is a number. Passion has no expiry date." 🌟 You are never too old to dream, ${name}!`, action: 'show_entertainment' };
    }
    if (/spiritual|moral|wisdom/.test(lower)) {
      return { intent: 'story', response: `Here's a spiritual story, ${name}: A king asked a wise sage, "What is the most important moment?" The sage replied, "Now. The most important person is whoever you're with. The most important thing is to do good." The king understood: happiness is not in the future — it's in this very moment. 🙏 You are doing beautifully, ${name}.`, action: 'show_entertainment' };
    }
    if (/bedtime|sleep|night/.test(lower)) {
      return { intent: 'story', response: `Once upon a time, ${name}, in a cozy village by the sea, there lived a grandmother who could talk to the stars. Every night, she'd sit on her porch and whisper stories to the sky. The stars would twinkle back, keeping her company. One night, a little star fell right into her garden, and they became the best of friends... 🌙✨ Sweet dreams, ${name}.`, action: 'show_entertainment' };
    }
    return { intent: 'story', response: `Here's a lovely story, ${name}: A man planted a small seed and watered it every day. For weeks, nothing happened. He nearly gave up, but one morning, a tiny green shoot appeared. Within months, it became a magnificent tree that gave shade to the whole neighborhood. 🌳 Patience and love always bear fruit. Want to hear another story — maybe motivational, spiritual, or a bedtime story?`, action: 'show_entertainment' };
  }

  // === GENERAL FUN / BORED ===
  if (/bored|fun|entertain|something\s*to\s*do|nothing\s*to\s*do/.test(lower)) {
    return { intent: 'engagement', response: `Let's fix that, ${name}! I can tell you a story, play music, share a joke, or we can play a game — Memory, Quiz, or Word Puzzle! What sounds good? 😊`, action: 'show_entertainment' };
  }

  // === SURPRISE ME ===
  if (/surprise\s*me|anything|whatever|your\s*choice/.test(lower)) {
    const surprises = [
      { intent: 'joke', response: `Why do bicycles fall over? Because they're two-tired! 😂 Want more jokes or something else?` },
      { intent: 'fact', response: `Did you know that sea otters hold hands while they sleep so they don't drift apart? 🦦 Isn't that adorable?` },
      { intent: 'story', response: `Here's a quick one: A little girl asked her grandfather, "Why do you garden every day?" He smiled and said, "Because the flowers remind me that beautiful things need patience." 🌷` },
    ];
    const s = surprises[Math.floor(Math.random() * surprises.length)];
    return { intent: s.intent, response: s.response, action: 'show_entertainment' };
  }

  // === BREATHING EXERCISE ===
  if (/breath|breathing|calm\s*down|relax/.test(lower)) {
    return { intent: 'breathing', response: `Let's do a calming breathing exercise, ${name}. Breathe in slowly through your nose for 4 counts... hold for 4... now breathe out through your mouth for 6 counts. Let's repeat this 3 times. You're doing great! 🍃`, action: 'start_exercise' };
  }

  // === SMART HOME ===
  if (/light|lamp|lock|door|thermostat|temperature|home\s*(control|device)/.test(lower)) {
    if (/turn\s*(on|off)\s*(all\s*)?(the\s*)?light|all\s*light.*(on|off)/.test(lower)) {
      return { intent: 'smart_home', response: `Done! I've toggled all the lights for you, ${name}. 💡`, action: 'toggle_all_lights_on' };
    }
    if (/turn\s*(on|off).*light|light.*(on|off)/.test(lower)) {
      return { intent: 'smart_home', response: `Done! I've toggled the lights for you, ${name}. 💡`, action: 'toggle_lights' };
    }
    if (/lock|unlock/.test(lower)) {
      return { intent: 'smart_home', response: `I've updated the door lock for you, ${name}. Stay safe! 🔒`, action: 'toggle_lock' };
    }
    if (/what.*status|how.*home|home\s*status/.test(lower)) {
      const devices = context?.smartDevices || [];
      const lights = devices.filter(d => d.type === 'light');
      const locks = devices.filter(d => d.type === 'lock');
      const onLights = lights.filter(d => d.status === 'on').length;
      const lockedDoors = locks.filter(d => d.status === 'locked').length;
      return { intent: 'smart_home', response: `Your home status, ${name}: ${onLights} of ${lights.length} lights are on, ${lockedDoors} of ${locks.length} doors are locked. Everything looks good! Would you like to change anything?`, action: 'navigate_home' };
    }
    return { intent: 'smart_home', response: `Your home is all set, ${name}. Would you like to control any specific device? You can say things like "turn on the lights" or "lock the door."`, action: 'navigate_home' };
  }

  // === SOS / EMERGENCY (enhanced) ===
  if (/help\s*me|emergency|sos|i\s*(fell|fallen|am falling)|i\s*am\s*(hurt|not\s*feeling\s*well|sick|in\s*pain)|chest\s*pain|can't\s*breathe|dizzy|i\s*need\s*help|somebody\s*help|please\s*help/.test(lower)) {
    if (/chest\s*pain|can't\s*breathe|heart\s*(attack|problem)|stroke|i\s*(fell|fallen|am falling)/.test(lower)) {
      return { intent: 'emergency_critical', response: `🚨 This is urgent, ${name}! I'm triggering an emergency alert right now. Stay as calm as you can. Help is being notified immediately. I'm contacting all your emergency contacts and your caregiver Maria. Don't try to move.`, action: 'trigger_sos_critical', data: { severity: 'critical', alertAll: true } };
    }
    if (/not\s*feeling\s*well|sick|hurt|pain|dizzy/.test(lower)) {
      return { intent: 'emergency_moderate', response: `I hear you, ${name}. I'm sending an alert to Sarah and your caregiver Maria right now. Stay where you are and try to stay calm. Help is on the way. 🚨 Would you like me to call someone?`, action: 'trigger_sos', data: { severity: 'high', suggestCall: true } };
    }
    return { intent: 'emergency', response: `I'm sending an alert right now, ${name}! Stay calm — help is on the way. I'm notifying Sarah and all your emergency contacts. 🚨`, action: 'trigger_sos' };
  }

  // === CALL FAMILY (enhanced with contact matching) ===
  if (/call|phone|ring|dial|reach|connect\s*(me\s*)?(to|with)?|talk\s*to|speak\s*(to|with)|contact/.test(lower)) {
    if (/cancel|stop|hang\s*up|end|nevermind|never\s*mind/.test(lower)) {
      return { intent: 'cancel_call', response: `Call cancelled, ${name}. Is there anything else you need?`, action: 'cancel_call' };
    }
    if (/retry|again|try\s*again|call\s*(them\s*)?again|redial/.test(lower)) {
      return { intent: 'retry_call', response: `Trying the call again, ${name}. One moment...`, action: 'retry_call' };
    }
    const contacts = context?.familyContacts || [];
    let matchedContact: FamilyContact | undefined;
    for (const contact of contacts) {
      if (contact.aliases.some(alias => lower.includes(alias))) { matchedContact = contact; break; }
    }
    if (!matchedContact && /family|everyone|somebody|someone/.test(lower)) {
      matchedContact = contacts.find(c => c.isPrimary && c.available);
    }
    if (matchedContact) {
      if (!matchedContact.available) {
        const alternative = contacts.find(c => c.available && c.id !== matchedContact!.id);
        const altMsg = alternative ? ` Would you like me to call ${alternative.name} (${alternative.relationship}) instead?` : ' Would you like me to try again later?';
        return { intent: 'call_unavailable', response: `I'm sorry, ${name}. ${matchedContact.name} isn't available right now.${altMsg}`, action: 'call_unavailable', data: { contactId: matchedContact.id, alternativeId: alternative?.id } };
      }
      return { intent: 'call_family', response: `Calling your ${matchedContact.relationship.toLowerCase()}, ${matchedContact.name}, now. 📞 Please hold on...`, action: 'initiate_call', data: { contactId: matchedContact.id, contactName: matchedContact.name } };
    }
    return { intent: 'call_who', response: `Who would you like me to call, ${name}? You can say your daughter Sarah, son Michael, granddaughter Emily, Doctor Williams, or caregiver Maria.`, action: 'ask_call_target' };
  }

  // === WATER / HYDRATION ===
  if (/water|drink|hydrat|thirst/.test(lower)) {
    return { intent: 'hydration', response: `Great reminder to stay hydrated, ${name}! Have a glass of water. I'll mark your hydration reminder as done. 💧 You've earned 2 wellness stars!`, action: 'mark_hydration' };
  }

  // === STATUS / SUMMARY ===
  if (/what.*time|time\s*is\s*it|today|date|summary|status|overview/.test(lower)) {
    const now = new Date();
    const upcoming = context?.reminders?.filter(r => r.status === 'upcoming') || [];
    const missed = context?.reminders?.filter(r => r.status === 'missed') || [];
    return { intent: 'status', response: `It's ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} on ${now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}. You have ${upcoming.length} upcoming reminder${upcoming.length !== 1 ? 's' : ''} and ${missed.length} missed. Your health looks ${context?.vitals?.some(v => v.status !== 'normal') ? 'mostly good with some items to watch' : 'great'}. How can I help?` };
  }

  // === THANK YOU ===
  if (/thank|thanks/.test(lower)) {
    return { intent: 'gratitude', response: `You're very welcome, ${name}! I'm always here for you. Is there anything else you'd like to do? 😊` };
  }

  // === GOODBYE ===
  if (/bye|goodbye|good\s*night|sleep|rest/.test(lower)) {
    const devices = context?.smartDevices || [];
    const onLights = devices.filter(d => d.type === 'light' && d.status === 'on').length;
    let extra = '';
    if (onLights > 0) extra = ` I notice you have ${onLights} light${onLights > 1 ? 's' : ''} still on. Would you like me to turn them off?`;
    return { intent: 'farewell', response: `Good night, ${name}! Sleep well and sweet dreams. I'll be here whenever you need me. 🌙${extra}` };
  }

  // === YES / CONFIRM ===
  if (/^(yes|yeah|sure|okay|ok|please|go ahead|do it|affirmative|correct|right)/i.test(lower)) {
    return { intent: 'confirmation', response: `Got it, ${name}! Done. Anything else I can help with? 😊` };
  }

  // === NO / DECLINE ===
  if (/^(no|nah|not now|maybe later|never mind|skip|cancel)/i.test(lower)) {
    return { intent: 'decline', response: `No problem, ${name}. Just let me know whenever you need anything. I'm right here! 😊` };
  }

  // === GENERAL KNOWLEDGE / FALLBACK ===
  return { intent: 'conversation', response: generateFallback(text, name, context) };
}

// Smarter fallback that actually attempts to address general eldercare,
// health, navigation, emotional, and small-talk questions instead of giving
// the same generic "I hear you" response.
function generateFallback(text: string, name: string, context?: IntentContext): string {
  const lower = text.toLowerCase().trim();

  // App navigation help
  if (/(how|where).*(open|find|use|get to|navigate)/.test(lower) || /^help( me)?$/.test(lower) || /what can you do|what do you do|features?/.test(lower)) {
    return `I can help you with a lot, ${name}. Try saying things like "show my reminders", "how is my health", "play music", "call my daughter", "open senior club", "play a game", "I feel lonely", or "I need help". You can also tap any card on the screen.`;
  }

  // Eldercare / general health questions
  if (/(blood\s*pressure|hypertension|bp)/.test(lower)) {
    return `Healthy blood pressure for most adults is around 120 over 80, ${name}. Take readings at the same time each day, sit calmly for five minutes first, and share unusual values with your doctor. Want me to open your vitals?`;
  }
  if (/diabet|sugar|glucose/.test(lower)) {
    return `For most people, fasting blood sugar between 70 and 100 mg/dL is healthy, ${name}. Eat balanced meals, walk a little after eating, and stay hydrated. I can show your latest glucose reading if you'd like.`;
  }
  if (/sleep|insomnia|can'?t sleep|trouble sleeping/.test(lower)) {
    return `Good sleep is so important, ${name}. Try a quiet routine: dim the lights an hour before bed, avoid screens, sip warm water, and breathe slowly. Would you like a bedtime story or some calming music?`;
  }
  if (/diet|eat|nutrition|food|meal/.test(lower)) {
    return `Eating well makes a big difference, ${name}. Aim for vegetables, whole grains, lentils or fish, and plenty of water. Smaller, regular meals are easier on digestion. Want me to set a hydration reminder?`;
  }
  if (/exercise|walk|fit|active|movement/.test(lower)) {
    return `Gentle movement is wonderful, ${name}. A 15-minute walk, light stretching, or chair yoga can lift your mood and keep joints healthy. Shall we start a short stretching session together?`;
  }
  if (/headache|head\s*ache|dizzy|nausea|fever|cough|cold/.test(lower)) {
    return `I'm sorry you're not feeling well, ${name}. Rest, sip warm water, and check your temperature. If it gets worse or doesn't ease in a day, please call your doctor. Want me to alert your caregiver?`;
  }
  if (/medicine|medication|pill|tablet|prescription/.test(lower) && /what|when|how|why/.test(lower)) {
    return `Always follow the dose your doctor prescribed, ${name}. Take medicines at the same time each day with water, and don't skip without asking. I can show today's reminders if you'd like.`;
  }

  // Emotional / companionship
  if (/lonely|alone|miss|sad|crying|empty/.test(lower)) {
    return `I hear you, ${name}, and I'm glad you told me. You're not alone — I'm right here. Would you like to join the Senior Club to chat with friends, or call your family?`;
  }
  if (/scared|afraid|worried|anxious|nervous/.test(lower)) {
    return `That feeling is real and it will pass, ${name}. Let's slow down together — breathe in for 4, hold for 4, breathe out for 6. I can also play calming music or call someone for you.`;
  }
  if (/happy|good day|great day|feeling well|grateful/.test(lower)) {
    return `That makes me so happy to hear, ${name}! 🌼 Hold on to that feeling. Would you like to share it with the Senior Club or call a loved one?`;
  }

  // Small talk / identity
  if (/your name|who are you|what are you/.test(lower)) {
    return `I'm your ConnectedCare companion, ${name} — here to help with reminders, health, family calls, music, games, and a friendly chat any time.`;
  }
  if (/how (are )?you|how('?s| is) it going/.test(lower)) {
    return `I'm doing well, thank you for asking, ${name}! I'm always here whenever you need me. How are you feeling today?`;
  }
  if (/weather|raining|sunny|hot|cold outside/.test(lower)) {
    return `I can't check live weather just yet, ${name}, but it's always wise to dress in layers and keep water nearby. Would you like me to remind you to drink water?`;
  }
  if (/news|today.*news|happening/.test(lower)) {
    return `I don't have today's news right now, ${name}, but I can read you a story, share a fun fact, or open the Senior Club so you can chat with friends.`;
  }
  if (/^(why|what|when|where|who|how)\b/.test(lower)) {
    return `That's a thoughtful question, ${name}. I may not have a perfect answer for everything, but I can help with your reminders, health, family, music, games, or just keep you company. Would you like to try one of those?`;
  }

  // Generic supportive fallback (varied, never identical twice in a row)
  const supportive = [
    `I'm listening, ${name}. Tell me a little more, or try saying "play music", "call my family", "open senior club", or "how is my health".`,
    `I'm here for you, ${name}. You can ask me about your medicines, your health, your family, or just talk — I love a good chat.`,
    `Thank you for sharing that, ${name}. If you'd like, we can play a game, listen to music, or check your reminders together.`,
    `I may not have caught that perfectly, ${name}, but I'm right here. Try "I feel lonely", "show my health", "play a game", or "call my daughter".`,
  ];
  return supportive[Math.floor(Math.random() * supportive.length)];
}
