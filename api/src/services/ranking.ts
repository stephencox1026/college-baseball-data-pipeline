import { query } from '../db.js';
import {
  analyzeHitterUpsideDownside,
  analyzePitcherUpsideDownside,
  gradeHitter,
  gradePitcher,
} from './grading.js';
import { metaCache } from './cache.js';
import type {
  Conference,
  HitterResult,
  MinIpRange,
  PitcherResult,
  RankingFilters,
} from '../types.js';

function toNum(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function round(value: number | null, digits: number): number | null {
  if (value === null) return null;
  const f = 10 ** digits;
  return Math.round(value * f) / f;
}

export async function getConferences(): Promise<Conference[]> {
  const cached = metaCache.get<Conference[]>('conferences');
  if (cached) return cached;

  const result = await query<{ id: number; name: string }>(
    'SELECT id, name FROM conferences ORDER BY name',
  );
  const rows = result.rows.map((r) => ({ id: r.id, name: r.name }));
  metaCache.set('conferences', rows);
  return rows;
}

export async function getSeasons(): Promise<number[]> {
  const cached = metaCache.get<number[]>('seasons');
  if (cached) return cached;

  const result = await query<{ season: number }>(`
    SELECT DISTINCT season FROM hitting_stats
    WHERE season IS NOT NULL
    UNION
    SELECT DISTINCT season FROM pitching_stats
    WHERE season IS NOT NULL
    ORDER BY season DESC
  `);
  const seasons = result.rows.map((r) => r.season);
  metaCache.set('seasons', seasons);
  return seasons;
}

function ipFilterSql(minIp: MinIpRange): string {
  if (minIp === '0-10') return 'pi.innings_pitched >= 0 AND pi.innings_pitched <= 10';
  if (minIp === '11-20') return 'pi.innings_pitched >= 11 AND pi.innings_pitched <= 20';
  return 'pi.innings_pitched >= 20';
}

export async function getTopPitchers(
  filters: RankingFilters & { minIp: MinIpRange },
): Promise<PitcherResult[]> {
  const params: unknown[] = [];
  const conditions: string[] = [ipFilterSql(filters.minIp)];
  conditions.push('pi.walks IS NOT NULL', 'pi.strikeouts IS NOT NULL');

  if (filters.conferenceId?.length) {
    params.push(filters.conferenceId);
    conditions.push(`p.conference_id = ANY($${params.length}::int[])`);
  }

  if (filters.drafted?.length) {
    const draftedConds: string[] = [];
    for (const d of filters.drafted) {
      if (d === 'drafted') draftedConds.push('p.drafted = TRUE');
      else if (d === 'not_drafted') draftedConds.push('p.drafted = FALSE');
      else if (d === 'true' || d === 'false') {
        params.push(d === 'true');
        draftedConds.push(`p.drafted = $${params.length}`);
      }
    }
    if (draftedConds.length) conditions.push(`(${draftedConds.join(' OR ')})`);
  }

  if (filters.season?.length) {
    params.push(filters.season);
    conditions.push(`pi.season = ANY($${params.length}::int[])`);
  }

  if (filters.age?.length) {
    params.push(filters.age);
    conditions.push(`p.age = ANY($${params.length}::int[])`);
  }

  params.push(filters.limit);
  const limitParam = `$${params.length}`;

  const sql = `
    SELECT
      p.id,
      p.name,
      p.school,
      p.age,
      c.name as conference_name,
      p.drafted,
      p.draft_team,
      p.draft_round,
      p.draft_pick,
      pi.season,
      pi.games,
      pi.games_started,
      pi.wins,
      pi.losses,
      pi.strikeouts,
      pi.walks,
      pi.innings_pitched,
      pi.era,
      pi.whip,
      CASE
        WHEN pi.innings_pitched > 0 THEN (pi.walks::numeric / NULLIF(pi.innings_pitched, 0)) * 9
        ELSE NULL
      END as bb_per_9,
      CASE
        WHEN pi.walks > 0 THEN pi.strikeouts::numeric / NULLIF(pi.walks, 0)
        WHEN pi.strikeouts > 0 THEN 999
        ELSE NULL
      END as k_per_bb,
      CASE
        WHEN pi.innings_pitched > 0 THEN (pi.strikeouts::numeric / NULLIF(pi.innings_pitched, 0)) * 9
        ELSE NULL
      END as k_per_9
    FROM pitching_stats pi
    JOIN players p ON pi.player_id = p.id
    LEFT JOIN conferences c ON p.conference_id = c.id
    WHERE ${conditions.join('\n      AND ')}
    ORDER BY
      bb_per_9 ASC NULLS LAST,
      k_per_bb DESC NULLS LAST,
      k_per_9 DESC NULLS LAST
    LIMIT ${limitParam}
  `;

  const result = await query(sql, params);
  return result.rows.map((row, index) => {
    const innings = toNum(row.innings_pitched) ?? 0;
    const walks = toNum(row.walks) ?? 0;
    const strikeouts = toNum(row.strikeouts) ?? 0;

    const bbPer9 = innings > 0 ? walks / innings * 9 : null;
    const kPerBb = walks > 0 ? strikeouts / walks : strikeouts > 0 ? 999 : null;
    const kPer9 = innings > 0 ? strikeouts / innings * 9 : null;
    const era = toNum(row.era);
    const whip = toNum(row.whip);
    const age = toNum(row.age);

    let score: number | null = null;
    if (bbPer9 !== null && kPerBb !== null && kPer9 !== null) {
      const bbScore = Math.max(0, 10 - bbPer9) * 0.4;
      const kBbScore = Math.min(kPerBb / 10, 1) * 0.4;
      const k9Score = Math.min(kPer9 / 15, 1) * 0.2;
      score = bbScore + kBbScore + k9Score;
    }

    const explanationParts: string[] = [];
    if (bbPer9 !== null) {
      if (bbPer9 < 2.0) explanationParts.push(`Excellent control with ${bbPer9.toFixed(2)} BB/9`);
      else if (bbPer9 < 3.0) explanationParts.push(`Good control with ${bbPer9.toFixed(2)} BB/9`);
      else explanationParts.push(`BB/9 of ${bbPer9.toFixed(2)}`);
    }
    if (kPerBb !== null) {
      if (kPerBb > 5.0) explanationParts.push(`outstanding ${kPerBb.toFixed(1)}:1 K/BB ratio`);
      else if (kPerBb > 3.0) explanationParts.push(`strong ${kPerBb.toFixed(1)}:1 K/BB ratio`);
      else explanationParts.push(`${kPerBb.toFixed(1)}:1 K/BB ratio`);
    }
    if (kPer9 !== null) {
      explanationParts.push(`${kPer9.toFixed(1)} K/9`);
    }
    const explanation = `${explanationParts.join('. ')}.`;

    let grade = 'N/A';
    let upside = 'Error calculating';
    let downside = 'Error calculating';
    try {
      [grade] = gradePitcher(bbPer9, kPerBb, kPer9, era, whip, innings || null, age);
      [upside, downside] = analyzePitcherUpsideDownside(
        bbPer9,
        kPerBb,
        kPer9,
        era,
        whip,
        innings || null,
        age,
      );
    } catch {
      // keep defaults
    }

    return {
      rank: index + 1,
      name: String(row.name),
      school: (row.school as string | null) || 'Unknown',
      age,
      conference_name: (row.conference_name as string | null) || 'Unknown',
      drafted: row.drafted as boolean | null,
      draft_team: (row.draft_team as string | null) || '',
      draft_round: toNum(row.draft_round),
      draft_pick: toNum(row.draft_pick),
      season: Number(row.season),
      games: toNum(row.games),
      games_started: toNum(row.games_started),
      wins: toNum(row.wins),
      losses: toNum(row.losses),
      strikeouts,
      walks,
      innings_pitched: innings ? innings : null,
      era,
      whip,
      bb_per_9: round(bbPer9, 2),
      k_per_bb: round(kPerBb, 2),
      k_per_9: round(kPer9, 2),
      score: round(score, 3),
      explanation,
      grade,
      upside,
      downside,
    };
  });
}

export async function getTopHitters(
  filters: RankingFilters & { minAb: number },
): Promise<HitterResult[]> {
  const params: unknown[] = [filters.minAb];
  const conditions: string[] = [
    'h.at_bats >= $1',
    'h.walks IS NOT NULL',
    'h.strikeouts IS NOT NULL',
    'h.obp IS NOT NULL',
    'h.slg IS NOT NULL',
  ];

  if (filters.conferenceId?.length) {
    params.push(filters.conferenceId);
    conditions.push(`p.conference_id = ANY($${params.length}::int[])`);
  }

  if (filters.drafted?.length) {
    const draftedConds: string[] = [];
    for (const d of filters.drafted) {
      if (d === 'drafted') draftedConds.push('p.drafted = TRUE');
      else if (d === 'not_drafted') {
        draftedConds.push('(p.drafted = FALSE OR p.drafted IS NULL)');
      } else if (d === 'true' || d === 'false') {
        params.push(d === 'true');
        draftedConds.push(`p.drafted = $${params.length}`);
      }
    }
    if (draftedConds.length) conditions.push(`(${draftedConds.join(' OR ')})`);
  }

  if (filters.season?.length) {
    params.push(filters.season);
    conditions.push(`h.season = ANY($${params.length}::int[])`);
  }

  if (filters.age?.length) {
    params.push(filters.age);
    conditions.push(`p.age = ANY($${params.length}::int[])`);
  }

  params.push(filters.limit);
  const limitParam = `$${params.length}`;

  const sql = `
    SELECT
      p.id,
      p.name,
      p.school,
      p.age,
      c.name as conference_name,
      p.drafted,
      p.draft_team,
      p.draft_round,
      p.draft_pick,
      h.season,
      h.games,
      h.at_bats,
      h.hits,
      h.doubles,
      h.triples,
      h.home_runs,
      h.rbi,
      h.walks,
      h.strikeouts,
      h.avg,
      h.obp,
      h.slg,
      h.ops,
      h.stolen_bases,
      CASE
        WHEN h.strikeouts > 0 THEN h.walks::numeric / NULLIF(h.strikeouts, 0)
        WHEN h.walks > 0 THEN 999
        ELSE NULL
      END as bb_per_k,
      CASE
        WHEN h.strikeouts > 0 THEN h.walks::numeric - h.strikeouts
        ELSE h.walks
      END as walk_strikeout_diff
    FROM hitting_stats h
    JOIN players p ON h.player_id = p.id
    LEFT JOIN conferences c ON p.conference_id = c.id
    WHERE ${conditions.join('\n      AND ')}
    ORDER BY
      walk_strikeout_diff DESC NULLS LAST,
      bb_per_k DESC NULLS LAST,
      h.ops DESC NULLS LAST,
      h.doubles DESC NULLS LAST,
      h.slg DESC NULLS LAST
    LIMIT ${limitParam}
  `;

  const result = await query(sql, params);
  return result.rows.map((row, index) => {
    const walks = toNum(row.walks) ?? 0;
    const strikeouts = toNum(row.strikeouts) ?? 0;
    const doubles = toNum(row.doubles) ?? 0;
    const atBats = toNum(row.at_bats);
    const age = toNum(row.age);

    const bbPerK = strikeouts > 0 ? walks / strikeouts : walks > 0 ? 999 : null;
    const walkStrikeoutDiff = walks - strikeouts;

    const obpRaw = toNum(row.obp);
    const slgRaw = toNum(row.slg);
    const storedOps = toNum(row.ops);
    const calculatedOps =
      obpRaw !== null || slgRaw !== null ? (obpRaw ?? 0) + (slgRaw ?? 0) : null;
    let opsValue: number | null = null;
    if (storedOps !== null && storedOps >= 0 && storedOps <= 2.5) opsValue = storedOps;
    else if (calculatedOps !== null) opsValue = calculatedOps;

    const explanationParts: string[] = [];
    if (walkStrikeoutDiff > 20) {
      explanationParts.push(
        `Excellent plate discipline with ${walkStrikeoutDiff >= 0 ? '+' : ''}${walkStrikeoutDiff} walk/strikeout differential`,
      );
    } else if (walkStrikeoutDiff > 0) {
      explanationParts.push(`More walks (${walks}) than strikeouts (${strikeouts})`);
    } else if (walkStrikeoutDiff > -10) {
      explanationParts.push(
        `Good plate discipline with ${walkStrikeoutDiff >= 0 ? '+' : ''}${walkStrikeoutDiff} differential`,
      );
    } else {
      explanationParts.push(
        `${walkStrikeoutDiff >= 0 ? '+' : ''}${walkStrikeoutDiff} walk/strikeout differential`,
      );
    }

    if (obpRaw !== null) {
      if (obpRaw > 0.45) explanationParts.push(`elite ${obpRaw.toFixed(3)} OBP`);
      else if (obpRaw > 0.4) explanationParts.push(`strong ${obpRaw.toFixed(3)} OBP`);
      else explanationParts.push(`${obpRaw.toFixed(3)} OBP`);
    }
    if (slgRaw !== null) {
      if (slgRaw > 0.6) explanationParts.push(`elite ${slgRaw.toFixed(3)} slugging`);
      else if (slgRaw > 0.5) explanationParts.push(`strong ${slgRaw.toFixed(3)} slugging`);
      else explanationParts.push(`${slgRaw.toFixed(3)} slugging`);
    }
    if (opsValue !== null && opsValue > 0.9) {
      explanationParts.push(`${opsValue.toFixed(3)} OPS`);
    }
    if (doubles > 15) explanationParts.push(`${doubles} doubles`);

    const explanation = `${explanationParts.join('. ')}.`;

    const obpRounded = round(obpRaw, 3);
    const slgRounded = round(slgRaw, 3);
    const opsRounded = round(opsValue, 3);

    let grade = 'N/A';
    let upside = 'Error calculating';
    let downside = 'Error calculating';
    try {
      [grade] = gradeHitter(
        bbPerK,
        walkStrikeoutDiff,
        obpRounded,
        slgRounded,
        opsRounded,
        doubles,
        atBats,
        age,
      );
      [upside, downside] = analyzeHitterUpsideDownside(
        bbPerK,
        walkStrikeoutDiff,
        obpRounded,
        slgRounded,
        opsRounded,
        doubles,
        atBats,
        age,
      );
    } catch {
      // keep defaults
    }

    return {
      rank: index + 1,
      name: String(row.name),
      school: (row.school as string | null) || null,
      age,
      conference_name: (row.conference_name as string | null) || null,
      drafted: row.drafted as boolean | null,
      draft_team: (row.draft_team as string | null) || '',
      draft_round: toNum(row.draft_round),
      draft_pick: toNum(row.draft_pick),
      season: Number(row.season),
      games: toNum(row.games),
      at_bats: atBats,
      hits: toNum(row.hits),
      doubles,
      triples: toNum(row.triples) ?? 0,
      home_runs: toNum(row.home_runs) ?? 0,
      rbi: toNum(row.rbi) ?? 0,
      walks,
      strikeouts,
      avg: round(toNum(row.avg), 3),
      obp: obpRounded,
      slg: slgRounded,
      ops: opsRounded,
      stolen_bases: toNum(row.stolen_bases) ?? 0,
      bb_per_k: round(bbPerK, 2),
      walk_strikeout_diff: walkStrikeoutDiff,
      explanation,
      grade,
      upside,
      downside,
    };
  });
}
