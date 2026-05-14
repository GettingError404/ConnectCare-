export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  correctIndex: number;
  category: 'general' | 'history' | 'nature' | 'health';
}

export interface MemoryCard {
  id: string;
  emoji: string;
  label: string;
}

export interface WordPuzzle {
  id: string;
  scrambled: string;
  answer: string;
  hint: string;
}

export const quizQuestions: QuizQuestion[] = [
  { id: 'qq1', question: 'What is the largest planet in our solar system?', options: ['Mars', 'Jupiter', 'Saturn', 'Earth'], correctIndex: 1, category: 'general' },
  { id: 'qq2', question: 'Which flower is known as the symbol of love?', options: ['Lily', 'Daisy', 'Rose', 'Tulip'], correctIndex: 2, category: 'nature' },
  { id: 'qq3', question: 'How many bones does the adult human body have?', options: ['186', '206', '256', '176'], correctIndex: 1, category: 'health' },
  { id: 'qq4', question: 'Which country is famous for the Eiffel Tower?', options: ['Italy', 'Spain', 'France', 'Germany'], correctIndex: 2, category: 'general' },
  { id: 'qq5', question: 'What vitamin does sunlight help your body produce?', options: ['Vitamin A', 'Vitamin C', 'Vitamin D', 'Vitamin B'], correctIndex: 2, category: 'health' },
  { id: 'qq6', question: 'What is the largest ocean on Earth?', options: ['Atlantic', 'Indian', 'Arctic', 'Pacific'], correctIndex: 3, category: 'nature' },
  { id: 'qq7', question: 'Who painted the Mona Lisa?', options: ['Picasso', 'Da Vinci', 'Van Gogh', 'Monet'], correctIndex: 1, category: 'history' },
  { id: 'qq8', question: 'What is the smallest continent?', options: ['Europe', 'Antarctica', 'Australia', 'South America'], correctIndex: 2, category: 'general' },
  { id: 'qq9', question: 'Which fruit is known as the king of fruits?', options: ['Apple', 'Mango', 'Banana', 'Grape'], correctIndex: 1, category: 'nature' },
  { id: 'qq10', question: 'How many days are in a leap year?', options: ['364', '365', '366', '367'], correctIndex: 2, category: 'general' },
  { id: 'qq11', question: 'What color are emeralds?', options: ['Red', 'Blue', 'Green', 'Purple'], correctIndex: 2, category: 'general' },
  { id: 'qq12', question: 'Which animal is called the ship of the desert?', options: ['Horse', 'Camel', 'Elephant', 'Donkey'], correctIndex: 1, category: 'nature' },
];

export const memoryPairs: MemoryCard[] = [
  { id: 'mc1', emoji: '🌸', label: 'Flower' },
  { id: 'mc2', emoji: '🌟', label: 'Star' },
  { id: 'mc3', emoji: '🎵', label: 'Music' },
  { id: 'mc4', emoji: '🦋', label: 'Butterfly' },
  { id: 'mc5', emoji: '🌈', label: 'Rainbow' },
  { id: 'mc6', emoji: '☀️', label: 'Sun' },
  { id: 'mc7', emoji: '🍎', label: 'Apple' },
  { id: 'mc8', emoji: '🐦', label: 'Bird' },
];

export const wordPuzzles: WordPuzzle[] = [
  { id: 'wp1', scrambled: 'PLPAE', answer: 'APPLE', hint: 'A fruit that keeps the doctor away' },
  { id: 'wp2', scrambled: 'NESUSHI', answer: 'SUNSHINE', hint: 'What makes the day bright' },
  { id: 'wp3', scrambled: 'LOWFER', answer: 'FLOWER', hint: 'It blooms in a garden' },
  { id: 'wp4', scrambled: 'YAFMLI', answer: 'FAMILY', hint: 'The people who love you most' },
  { id: 'wp5', scrambled: 'PAPHYESNIS', answer: 'HAPPINESS', hint: 'The best feeling in the world' },
  { id: 'wp6', scrambled: 'USMCI', answer: 'MUSIC', hint: 'You listen to it for joy' },
  { id: 'wp7', scrambled: 'GRNADE', answer: 'GARDEN', hint: 'Where flowers grow' },
  { id: 'wp8', scrambled: 'RETAW', answer: 'WATER', hint: 'You drink it to stay healthy' },
];

export interface MusicTrack {
  id: string;
  title: string;
  artist: string;
  genre: 'devotional' | 'classical' | 'oldies' | 'nature' | 'calm' | 'folk';
  duration: number; // seconds
}

export const musicLibrary: MusicTrack[] = [
  { id: 'mt1', title: 'Morning Raaga', artist: 'Classical Collection', genre: 'devotional', duration: 240 },
  { id: 'mt2', title: 'Peaceful Hymns', artist: 'Sacred Songs', genre: 'devotional', duration: 300 },
  { id: 'mt3', title: 'Moonlight Sonata', artist: 'Beethoven', genre: 'classical', duration: 360 },
  { id: 'mt4', title: 'Clair de Lune', artist: 'Debussy', genre: 'classical', duration: 300 },
  { id: 'mt5', title: 'What a Wonderful World', artist: 'Louis Armstrong', genre: 'oldies', duration: 180 },
  { id: 'mt6', title: 'Fly Me to the Moon', artist: 'Frank Sinatra', genre: 'oldies', duration: 210 },
  { id: 'mt7', title: 'Unchained Melody', artist: 'Righteous Brothers', genre: 'oldies', duration: 220 },
  { id: 'mt8', title: 'Ocean Waves', artist: 'Nature Sounds', genre: 'nature', duration: 600 },
  { id: 'mt9', title: 'Forest Rain', artist: 'Nature Sounds', genre: 'nature', duration: 600 },
  { id: 'mt10', title: 'Morning Birds', artist: 'Nature Sounds', genre: 'nature', duration: 480 },
  { id: 'mt11', title: 'Peaceful Piano', artist: 'Calm Collection', genre: 'calm', duration: 300 },
  { id: 'mt12', title: 'Gentle Strings', artist: 'Calm Collection', genre: 'calm', duration: 360 },
  { id: 'mt13', title: 'Country Roads', artist: 'John Denver', genre: 'folk', duration: 200 },
  { id: 'mt14', title: 'Scarborough Fair', artist: 'Simon & Garfunkel', genre: 'folk', duration: 210 },
];
