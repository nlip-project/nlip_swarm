type RGB = { r: number; g: number; b: number };

function clampChannel(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function parseHexColor(input: string): RGB | null {
  const value = input.trim().replace('#', '');

  if (value.length === 3) {
    const r = Number.parseInt(value[0] + value[0], 16);
    const g = Number.parseInt(value[1] + value[1], 16);
    const b = Number.parseInt(value[2] + value[2], 16);
    if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return null;
    return { r, g, b };
  }

  if (value.length === 6 || value.length === 8) {
    const r = Number.parseInt(value.slice(0, 2), 16);
    const g = Number.parseInt(value.slice(2, 4), 16);
    const b = Number.parseInt(value.slice(4, 6), 16);
    if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return null;
    return { r, g, b };
  }

  return null;
}

function parseRgbColor(input: string): RGB | null {
  const match = input.trim().match(/^rgba?\(([^)]+)\)$/i);
  if (!match) return null;

  const parts = match[1].split(',').map((part) => part.trim());
  if (parts.length < 3) return null;

  const r = Number(parts[0]);
  const g = Number(parts[1]);
  const b = Number(parts[2]);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return null;

  return { r: clampChannel(r), g: clampChannel(g), b: clampChannel(b) };
}

function parseColor(input: string): RGB | null {
  if (!input) return null;
  if (input.startsWith('#')) return parseHexColor(input);
  if (/^rgba?\(/i.test(input)) return parseRgbColor(input);
  return null;
}

function toLinear(value: number): number {
  const channel = value / 255;
  if (channel <= 0.03928) return channel / 12.92;
  return ((channel + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance(color: RGB): number {
  const r = toLinear(color.r);
  const g = toLinear(color.g);
  const b = toLinear(color.b);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrastRatio(colorA: RGB, colorB: RGB): number {
  const lighter = Math.max(relativeLuminance(colorA), relativeLuminance(colorB));
  const darker = Math.min(relativeLuminance(colorA), relativeLuminance(colorB));
  return (lighter + 0.05) / (darker + 0.05);
}

export function getContrastingTextColor(
  backgroundColor: string,
  lightTextColor = '#FFFFFF',
  darkTextColor = '#11181C'
): string {
  const background = parseColor(backgroundColor);
  if (!background) return lightTextColor;

  const light = parseColor(lightTextColor);
  const dark = parseColor(darkTextColor);
  if (!light || !dark) {
    return relativeLuminance(background) > 0.53 ? darkTextColor : lightTextColor;
  }

  return contrastRatio(background, dark) >= contrastRatio(background, light)
    ? darkTextColor
    : lightTextColor;
}
