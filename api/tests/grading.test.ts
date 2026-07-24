import { describe, expect, it } from 'vitest';
import { gradeHitter, gradePitcher } from '../src/services/grading.js';

describe('gradePitcher', () => {
  it('returns N/A when core metrics missing', () => {
    expect(gradePitcher(null, 3, 10, 3, 1.2, 40, 20)[0]).toBe('N/A');
  });

  it('rewards elite control and strikeouts', () => {
    const [grade, pct] = gradePitcher(1.2, 6, 13, 1.8, 0.95, 90, 19);
    expect(grade).toBe('A+');
    expect(typeof pct).toBe('number');
    expect(pct as number).toBeGreaterThanOrEqual(95);
  });
});

describe('gradeHitter', () => {
  it('returns N/A when core metrics missing', () => {
    expect(gradeHitter(null, 10, 0.4, 0.5, 0.9, 20, 200, 20)[0]).toBe('N/A');
  });

  it('rewards elite plate discipline and power', () => {
    const [grade, pct] = gradeHitter(1.6, 35, 0.46, 0.62, 1.08, 25, 220, 19);
    expect(grade).toBe('A+');
    expect(typeof pct).toBe('number');
    expect(pct as number).toBeGreaterThanOrEqual(95);
  });
});
