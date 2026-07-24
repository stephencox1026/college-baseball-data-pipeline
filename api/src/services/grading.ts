/** Port of dashboard.py grade_* / analyze_* — keep thresholds identical. */

export function gradePitcher(
  bbPer9: number | null,
  kPerBb: number | null,
  kPer9: number | null,
  era: number | null,
  whip: number | null,
  inningsPitched: number | null,
  age: number | null,
): [string, number | string] {
  if (bbPer9 === null || kPerBb === null || kPer9 === null) {
    return ['N/A', 'Insufficient data'];
  }

  let score = 0;
  let maxScore = 0;

  if (bbPer9 !== null) {
    if (bbPer9 <= 1.5) score += 25;
    else if (bbPer9 <= 2.5) score += 20;
    else if (bbPer9 <= 3.5) score += 15;
    else if (bbPer9 <= 4.5) score += 10;
    else score += 5;
    maxScore += 25;
  }

  if (kPerBb !== null) {
    if (kPerBb >= 5.0) score += 25;
    else if (kPerBb >= 3.5) score += 20;
    else if (kPerBb >= 2.5) score += 15;
    else if (kPerBb >= 1.5) score += 10;
    else score += 5;
    maxScore += 25;
  }

  if (kPer9 !== null) {
    if (kPer9 >= 12.0) score += 20;
    else if (kPer9 >= 10.0) score += 16;
    else if (kPer9 >= 8.0) score += 12;
    else if (kPer9 >= 6.0) score += 8;
    else score += 4;
    maxScore += 20;
  }

  if (era !== null) {
    if (era <= 2.0) score += 15;
    else if (era <= 3.0) score += 12;
    else if (era <= 4.0) score += 9;
    else if (era <= 5.0) score += 6;
    else score += 3;
    maxScore += 15;
  }

  if (whip !== null) {
    if (whip <= 1.0) score += 15;
    else if (whip <= 1.2) score += 12;
    else if (whip <= 1.4) score += 9;
    else if (whip <= 1.6) score += 6;
    else score += 3;
    maxScore += 15;
  }

  if (inningsPitched !== null) {
    if (inningsPitched >= 80) score += 5;
    else if (inningsPitched >= 50) score += 3;
    else if (inningsPitched >= 30) score += 1;
    maxScore += 5;
  }

  if (age !== null) {
    if (age <= 19) score += 5;
    else if (age <= 20) score += 3;
    else if (age <= 21) score += 1;
    maxScore += 5;
  }

  const percentage = maxScore > 0 ? (score / maxScore) * 100 : 0;
  return [percentageToGrade(percentage), percentage];
}

export function analyzePitcherUpsideDownside(
  bbPer9: number | null,
  kPerBb: number | null,
  kPer9: number | null,
  era: number | null,
  whip: number | null,
  inningsPitched: number | null,
  age: number | null,
): [string, string] {
  const upsideParts: string[] = [];
  const downsideParts: string[] = [];

  if (kPer9 !== null && kPer9 >= 10) upsideParts.push('High strikeout rate');
  if (kPerBb !== null && kPerBb >= 3.5) upsideParts.push('Excellent command');
  if (bbPer9 !== null && bbPer9 <= 2.5) upsideParts.push('Strong control');
  if (age !== null && age <= 20) upsideParts.push('Young age with development potential');
  if (inningsPitched !== null && inningsPitched >= 50) upsideParts.push('Proven workload');

  if (bbPer9 !== null) {
    if (bbPer9 > 4.5) downsideParts.push('Very high walk rate (hurts grade significantly)');
    else if (bbPer9 > 3.5) downsideParts.push('High walk rate');
    else if (bbPer9 > 2.5) downsideParts.push('Above-average walk rate');
  }

  if (kPerBb !== null) {
    if (kPerBb < 1.8) downsideParts.push('Poor strikeout-to-walk ratio (major concern)');
    else if (kPerBb < 2.5) downsideParts.push('Below-average strikeout-to-walk ratio');
    else if (kPerBb < 3.5) downsideParts.push('Moderate strikeout-to-walk ratio');
  }

  if (kPer9 !== null) {
    if (kPer9 < 6.0) downsideParts.push('Low strikeout rate (limits upside)');
    else if (kPer9 < 8.0) downsideParts.push('Below-average strikeout rate');
    else if (kPer9 < 10.0) downsideParts.push('Moderate strikeout rate');
  }

  if (era !== null) {
    if (era > 5.5) downsideParts.push('Very high ERA');
    else if (era > 4.5) downsideParts.push('High ERA');
    else if (era > 3.5) downsideParts.push('Above-average ERA');
  }

  if (whip !== null) {
    if (whip > 1.6) downsideParts.push('Very high WHIP');
    else if (whip > 1.4) downsideParts.push('High WHIP');
    else if (whip > 1.2) downsideParts.push('Above-average WHIP');
  }

  if (inningsPitched !== null) {
    if (inningsPitched < 10) downsideParts.push('Very limited sample size (unreliable stats)');
    else if (inningsPitched < 20) downsideParts.push('Limited sample size');
    else if (inningsPitched < 30) downsideParts.push('Small sample size');
    else if (inningsPitched < 50) downsideParts.push('Moderate sample size');
  }

  if (age !== null) {
    if (age >= 24) downsideParts.push('Older prospect (less development time)');
    else if (age >= 23) downsideParts.push('Older age for prospect');
  }

  const upside = upsideParts.length ? upsideParts.join(', ') : 'Limited upside indicators';
  const downside = downsideParts.length
    ? downsideParts.join('. ')
    : 'Average across all metrics (no major weaknesses)';

  return [upside, downside];
}

export function gradeHitter(
  bbPerK: number | null,
  walkStrikeoutDiff: number | null,
  obp: number | null,
  slg: number | null,
  ops: number | null,
  doubles: number | null,
  atBats: number | null,
  age: number | null,
): [string, number | string] {
  if (bbPerK === null || obp === null || slg === null || ops === null) {
    return ['N/A', 'Insufficient data'];
  }

  let score = 0;
  let maxScore = 0;

  if (bbPerK !== null) {
    if (bbPerK >= 1.5) score += 20;
    else if (bbPerK >= 1.2) score += 16;
    else if (bbPerK >= 1.0) score += 12;
    else if (bbPerK >= 0.8) score += 8;
    else score += 4;
    maxScore += 20;
  }

  if (walkStrikeoutDiff !== null) {
    if (walkStrikeoutDiff >= 30) score += 15;
    else if (walkStrikeoutDiff >= 20) score += 12;
    else if (walkStrikeoutDiff >= 10) score += 9;
    else if (walkStrikeoutDiff >= 0) score += 6;
    else score += 3;
    maxScore += 15;
  }

  if (obp !== null) {
    if (obp >= 0.45) score += 20;
    else if (obp >= 0.4) score += 16;
    else if (obp >= 0.37) score += 12;
    else if (obp >= 0.34) score += 8;
    else score += 4;
    maxScore += 20;
  }

  if (slg !== null) {
    if (slg >= 0.6) score += 20;
    else if (slg >= 0.55) score += 16;
    else if (slg >= 0.5) score += 12;
    else if (slg >= 0.45) score += 8;
    else score += 4;
    maxScore += 20;
  }

  if (ops !== null) {
    if (ops >= 1.0) score += 15;
    else if (ops >= 0.9) score += 12;
    else if (ops >= 0.8) score += 9;
    else if (ops >= 0.7) score += 6;
    else score += 3;
    maxScore += 15;
  }

  if (doubles !== null && atBats !== null && atBats > 0) {
    const doublesPerAb = doubles / atBats;
    if (doublesPerAb >= 0.1) score += 5;
    else if (doublesPerAb >= 0.08) score += 4;
    else if (doublesPerAb >= 0.06) score += 3;
    else score += 1;
    maxScore += 5;
  }

  if (atBats !== null) {
    if (atBats >= 200) score += 3;
    else if (atBats >= 150) score += 2;
    else if (atBats >= 100) score += 1;
    maxScore += 3;
  }

  if (age !== null) {
    if (age <= 19) score += 2;
    else if (age <= 20) score += 1;
    maxScore += 2;
  }

  const percentage = maxScore > 0 ? (score / maxScore) * 100 : 0;
  return [percentageToGrade(percentage), percentage];
}

export function analyzeHitterUpsideDownside(
  bbPerK: number | null,
  walkStrikeoutDiff: number | null,
  obp: number | null,
  slg: number | null,
  ops: number | null,
  doubles: number | null,
  atBats: number | null,
  age: number | null,
): [string, string] {
  const upsideParts: string[] = [];
  const downsideParts: string[] = [];

  if (walkStrikeoutDiff !== null && walkStrikeoutDiff > 20) {
    upsideParts.push('Excellent plate discipline');
  }
  if (bbPerK !== null && bbPerK >= 1.2) upsideParts.push('Strong walk-to-strikeout ratio');
  if (ops !== null && ops >= 0.9) upsideParts.push('High OPS');
  if (slg !== null && slg >= 0.55) upsideParts.push('Good power');
  if (obp !== null && obp >= 0.4) upsideParts.push('High on-base ability');
  if (age !== null && age <= 20) upsideParts.push('Young age with development potential');

  if (bbPerK !== null) {
    if (bbPerK < 0.8) downsideParts.push('Poor walk-to-strikeout ratio (major concern)');
    else if (bbPerK < 1.0) downsideParts.push('Below-average walk-to-strikeout ratio');
    else if (bbPerK < 1.2) downsideParts.push('Moderate walk-to-strikeout ratio');
  }

  if (walkStrikeoutDiff !== null) {
    if (walkStrikeoutDiff < -10) downsideParts.push('Many more strikeouts than walks (hurts grade)');
    else if (walkStrikeoutDiff < 0) downsideParts.push('More strikeouts than walks');
    else if (walkStrikeoutDiff < 10) downsideParts.push('Minimal walk advantage');
  }

  if (obp !== null) {
    if (obp < 0.32) downsideParts.push('Very low on-base percentage');
    else if (obp < 0.34) downsideParts.push('Low on-base percentage');
    else if (obp < 0.37) downsideParts.push('Below-average on-base percentage');
  }

  if (slg !== null) {
    if (slg < 0.4) downsideParts.push('Very limited power');
    else if (slg < 0.45) downsideParts.push('Limited power');
    else if (slg < 0.5) downsideParts.push('Below-average power');
  }

  if (ops !== null) {
    if (ops < 0.7) downsideParts.push('Very low OPS');
    else if (ops < 0.8) downsideParts.push('Low OPS');
    else if (ops < 0.9) downsideParts.push('Below-average OPS');
  }

  if (doubles !== null && atBats !== null && atBats > 0) {
    if (doubles / atBats < 0.06) {
      downsideParts.push('Low doubles rate (limited extra-base power)');
    }
  }

  if (atBats !== null) {
    if (atBats < 100) downsideParts.push('Very limited sample size (unreliable stats)');
    else if (atBats < 150) downsideParts.push('Limited sample size');
    else if (atBats < 200) downsideParts.push('Moderate sample size');
  }

  if (age !== null) {
    if (age >= 24) downsideParts.push('Older prospect (less development time)');
    else if (age >= 23) downsideParts.push('Older age for prospect');
  }

  const upside = upsideParts.length ? upsideParts.join(', ') : 'Limited upside indicators';
  const downside = downsideParts.length
    ? downsideParts.join('. ')
    : 'Average across all metrics (no major weaknesses)';

  return [upside, downside];
}

function percentageToGrade(percentage: number): string {
  if (percentage >= 95) return 'A+';
  if (percentage >= 90) return 'A';
  if (percentage >= 85) return 'A-';
  if (percentage >= 80) return 'B+';
  if (percentage >= 75) return 'B';
  if (percentage >= 70) return 'B-';
  if (percentage >= 65) return 'C+';
  if (percentage >= 60) return 'C';
  if (percentage >= 55) return 'C-';
  if (percentage >= 50) return 'D+';
  if (percentage >= 45) return 'D';
  if (percentage >= 40) return 'D-';
  return 'F';
}
