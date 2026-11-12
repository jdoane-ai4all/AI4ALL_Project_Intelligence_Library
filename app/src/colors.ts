// AI4ALL-branded categorical palettes, one per theme. Hues lead with the brand (plum, sunshine, mint, then coral,
// with blue/teal/violet as supporting hues), stepped into each theme's lightness band. Both orders pass the dataviz
// checks (lightness band, chroma floor, adjacent colorblind separation, normal-vision floor) against their surface.
export type Theme = "dark" | "light";
const PALETTES: Record<Theme, string[]> = {
  // Charcoal surface #191919: same hue order at higher chroma (OKLCH C<=0.2, L 0.58-0.67); passes lightness band,
  // chroma floor, adjacent CVD separation (worst deutan dE 8.5), normal-vision floor and >= 3:1 contrast
  dark: ["#dd4796", "#a17000", "#20b339", "#008af6", "#e13d53", "#00a8a2", "#a167f1"],
  // white/Miami surface: sunshine, teal and blue sit below 3:1, so the legend always labels them
  light: ["#9f366c", "#de9d16", "#226929", "#08b6af", "#663e9e", "#70aff4", "#b5414d"],
};
export const palette = (t: Theme) => PALETTES[t];
// Status-like scales use the brand's own meanings: mint = fine, sunshine = caution, coral = serious.
const STATUS: Record<Theme, Record<string, string>> = {
  dark: { good: "#ACE4AA", warn: "#FFB200", bad: "#FF5C86", none: "#8FA898" },
  light: { good: "#2F6B3F", warn: "#B07A00", bad: "#D10045", none: "#7C8C82" },
};
const KEY: Record<string, keyof typeof STATUS.dark> = {
  Beginner: "good", Intermediate: "warn", Advanced: "bad", Unknown: "none",
  "No major issues": "good", "Use with caution": "warn", "Withheld for review": "bad",
};
export const colorFor = (k: string, t: Theme = "dark") => STATUS[t][KEY[k] ?? "none"];
export const neutral = (t: Theme) => STATUS[t].none;
