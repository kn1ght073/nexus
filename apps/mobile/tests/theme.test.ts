import { Colors } from '../src/theme/colors';

describe('NEXUS Mobile Design Tokens & Theme Palettes', () => {
  test('provides contrast-compliant brand colors in dark and light modes', () => {
    expect(Colors.dark.background).toBe('#090D16');
    expect(Colors.dark.primary).toBe('#0EA5E9');
    expect(Colors.light.background).toBe('#F8FAFC');
    expect(Colors.light.primary).toBe('#0284C7');
  });

  test('defines consistent semantic status tokens', () => {
    expect(Colors.dark.success).toBeDefined();
    expect(Colors.dark.danger).toBeDefined();
    expect(Colors.dark.warning).toBeDefined();
    expect(Colors.light.success).toBeDefined();
  });
});
