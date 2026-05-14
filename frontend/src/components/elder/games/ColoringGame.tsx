'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Volume2, X, RotateCcw, Palette } from 'lucide-react';

const COLORS = [
  { name: 'red', value: 'hsl(0, 84%, 60%)', label: '🔴' },
  { name: 'blue', value: 'hsl(210, 100%, 52%)', label: '🔵' },
  { name: 'green', value: 'hsl(142, 71%, 45%)', label: '🟢' },
  { name: 'yellow', value: 'hsl(38, 92%, 50%)', label: '🟡' },
  { name: 'purple', value: 'hsl(270, 60%, 55%)', label: '🟣' },
  { name: 'orange', value: 'hsl(25, 95%, 53%)', label: '🟠' },
  { name: 'pink', value: 'hsl(330, 80%, 65%)', label: '💗' },
];

interface ShapeArea {
  id: string;
  path: string;
  label: string;
  defaultColor: string;
}

interface Drawing {
  name: string;
  emoji: string;
  areas: ShapeArea[];
  viewBox: string;
}

const DRAWINGS: Drawing[] = [
  {
    name: 'Flower',
    emoji: '🌸',
    viewBox: '0 0 200 200',
    areas: [
      { id: 'petal1', path: 'M100,40 C120,20 140,30 130,55 C145,45 155,65 135,75 C155,80 150,100 130,95 C140,115 120,120 110,100 C100,120 80,115 70,95 C50,100 45,80 65,75 C45,65 55,45 70,55 C60,30 80,20 100,40Z', label: 'petals', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'center', path: 'M100,65 A15,15 0 1,1 100,95 A15,15 0 1,1 100,65Z', label: 'center', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'stem', path: 'M96,100 L96,170 L104,170 L104,100Z', label: 'stem', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'leaf1', path: 'M96,130 C80,120 70,135 85,145Z', label: 'left leaf', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'leaf2', path: 'M104,140 C120,130 130,145 115,155Z', label: 'right leaf', defaultColor: 'hsl(210, 15%, 93%)' },
    ],
  },
  {
    name: 'House',
    emoji: '🏠',
    viewBox: '0 0 200 200',
    areas: [
      { id: 'roof', path: 'M100,30 L170,90 L30,90Z', label: 'roof', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'wall', path: 'M45,90 L155,90 L155,170 L45,170Z', label: 'walls', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'door', path: 'M85,120 L115,120 L115,170 L85,170Z', label: 'door', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'window1', path: 'M55,100 L75,100 L75,115 L55,115Z', label: 'left window', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'window2', path: 'M125,100 L145,100 L145,115 L125,115Z', label: 'right window', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'chimney', path: 'M130,30 L145,30 L145,70 L130,70Z', label: 'chimney', defaultColor: 'hsl(210, 15%, 93%)' },
    ],
  },
  {
    name: 'Butterfly',
    emoji: '🦋',
    viewBox: '0 0 200 200',
    areas: [
      { id: 'wingTL', path: 'M100,80 C80,40 30,30 40,80 C45,95 80,95 100,80Z', label: 'top left wing', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'wingTR', path: 'M100,80 C120,40 170,30 160,80 C155,95 120,95 100,80Z', label: 'top right wing', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'wingBL', path: 'M100,100 C85,110 40,130 55,100 C65,90 85,90 100,100Z', label: 'bottom left wing', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'wingBR', path: 'M100,100 C115,110 160,130 145,100 C135,90 115,90 100,100Z', label: 'bottom right wing', defaultColor: 'hsl(210, 15%, 93%)' },
      { id: 'body', path: 'M97,60 L103,60 L104,140 L96,140Z', label: 'body', defaultColor: 'hsl(210, 15%, 93%)' },
    ],
  },
];

interface ColoringGameProps {
  onExit: () => void;
  onSpeak: (text: string) => void;
}

const ColoringGame: React.FC<ColoringGameProps> = ({ onExit, onSpeak }) => {
  const [drawingIndex, setDrawingIndex] = useState(0);
  const [selectedColor, setSelectedColor] = useState(COLORS[0]);
  const [areaColors, setAreaColors] = useState<Record<string, string>>({});
  const [lastTapped, setLastTapped] = useState('');

  const drawing = DRAWINGS[drawingIndex];

  const initDrawing = useCallback((idx: number) => {
    setDrawingIndex(idx);
    setAreaColors({});
    setLastTapped('');
  }, []);

  useEffect(() => {
    onSpeak('Pick a color, then tap a part of the picture to fill it in! Have fun!');
  }, []);

  const handleAreaTap = (area: ShapeArea) => {
    setAreaColors(prev => ({ ...prev, [area.id]: selectedColor.value }));
    setLastTapped(area.label);
    onSpeak(`Colored the ${area.label} ${selectedColor.name}!`);
  };

  const handleColorByVoice = useCallback((command: string) => {
    const lower = command.toLowerCase().trim();
    // Check for color selection
    const color = COLORS.find(c => lower.includes(c.name));
    if (color) {
      setSelectedColor(color);
      onSpeak(`Selected ${color.name}!`);
      return;
    }
    // Check for area tap
    const area = drawing.areas.find(a => lower.includes(a.label.toLowerCase()));
    if (area) {
      setAreaColors(prev => ({ ...prev, [area.id]: selectedColor.value }));
      setLastTapped(area.label);
      onSpeak(`Colored the ${area.label} ${selectedColor.name}!`);
      return;
    }
    if (/next|change|different/.test(lower)) {
      const next = (drawingIndex + 1) % DRAWINGS.length;
      initDrawing(next);
      onSpeak(`Here's a ${DRAWINGS[next].name}! Pick a color and start coloring!`);
    } else if (/clear|reset|restart/.test(lower)) {
      setAreaColors({});
      onSpeak('Cleared! Start fresh!');
    } else if (/exit|quit|stop|back/.test(lower)) {
      onExit();
    } else if (/repeat|instruction|help/.test(lower)) {
      onSpeak('Pick a color, then tap a part of the picture to fill it in!');
    }
  }, [drawing, selectedColor, drawingIndex, initDrawing, onExit, onSpeak]);

  useEffect(() => {
    type WindowWithColoringCommand = Window & {
      __coloringCommand?: (command: string) => void;
    };

    (window as WindowWithColoringCommand).__coloringCommand = handleColorByVoice;
    return () => {
      delete (window as WindowWithColoringCommand).__coloringCommand;
    };
  }, [handleColorByVoice]);


  return (
    <div className="flex flex-col items-center gap-4 p-4 animate-fade-in">
      <div className="flex items-center justify-between w-full max-w-md">
        <h2 className="text-xl font-bold text-foreground">🎨 Coloring</h2>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={() => onSpeak('Pick a color then tap a shape to fill it!')}>
            <Volume2 className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onExit}>
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">{drawing.emoji} {drawing.name} {lastTapped && `• Last: ${lastTapped}`}</p>

      {/* Color palette */}
      <div className="flex gap-2 flex-wrap justify-center">
        {COLORS.map(color => (
          <button
            key={color.name}
            onClick={() => { setSelectedColor(color); onSpeak(`Selected ${color.name}`); }}
            className={`w-12 h-12 rounded-full border-4 transition-all active:scale-90 ${
              selectedColor.name === color.name ? 'border-foreground scale-110 shadow-lg' : 'border-border'
            }`}
            style={{ backgroundColor: color.value }}
            aria-label={color.name}
          />
        ))}
      </div>

      {/* SVG Drawing */}
      <div className="bg-card rounded-2xl border border-border p-4 w-full max-w-md">
        <svg viewBox={drawing.viewBox} className="w-full h-auto" style={{ maxHeight: '280px' }}>
          {drawing.areas.map(area => (
            <path
              key={area.id}
              d={area.path}
              fill={areaColors[area.id] || area.defaultColor}
              stroke="hsl(215, 25%, 15%)"
              strokeWidth="1.5"
              className="cursor-pointer transition-all duration-300 hover:opacity-80"
              onClick={() => handleAreaTap(area)}
            />
          ))}
        </svg>
      </div>

      {/* Controls */}
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => { setAreaColors({}); onSpeak('Cleared!'); }} className="rounded-xl">
          <RotateCcw className="w-4 h-4 mr-1" /> Clear
        </Button>
        <Button variant="outline" onClick={() => {
          const next = (drawingIndex + 1) % DRAWINGS.length;
          initDrawing(next);
          onSpeak(`Here's a ${DRAWINGS[next].name}!`);
        }} className="rounded-xl">
          <Palette className="w-4 h-4 mr-1" /> Next Drawing
        </Button>
      </div>
    </div>
  );
};

export default ColoringGame;

