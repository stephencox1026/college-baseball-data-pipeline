export type MinIpRange = '0-10' | '11-20' | '20+';

export interface Conference {
  id: number;
  name: string;
}

export interface PitcherResult {
  rank: number;
  name: string;
  school: string;
  age: number | null;
  conference_name: string;
  drafted: boolean | null;
  draft_team: string;
  draft_round: number | null;
  draft_pick: number | null;
  season: number;
  games: number | null;
  games_started: number | null;
  wins: number | null;
  losses: number | null;
  strikeouts: number;
  walks: number;
  innings_pitched: number | null;
  era: number | null;
  whip: number | null;
  bb_per_9: number | null;
  k_per_bb: number | null;
  k_per_9: number | null;
  score: number | null;
  explanation: string;
  grade: string;
  upside: string;
  downside: string;
}

export interface HitterResult {
  rank: number;
  name: string;
  school: string | null;
  age: number | null;
  conference_name: string | null;
  drafted: boolean | null;
  draft_team: string;
  draft_round: number | null;
  draft_pick: number | null;
  season: number;
  games: number | null;
  at_bats: number | null;
  hits: number | null;
  doubles: number;
  triples: number;
  home_runs: number;
  rbi: number;
  walks: number;
  strikeouts: number;
  avg: number | null;
  obp: number | null;
  slg: number | null;
  ops: number | null;
  stolen_bases: number;
  bb_per_k: number | null;
  walk_strikeout_diff: number;
  explanation: string;
  grade: string;
  upside: string;
  downside: string;
}

export interface RankingFilters {
  limit: number;
  conferenceId?: number[];
  drafted?: string[];
  season?: number[];
  age?: number[];
}
