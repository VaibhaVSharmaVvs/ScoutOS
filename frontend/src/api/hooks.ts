// React Query hooks — one per endpoint. Predictions cache long (model outputs
// are stable); search is short-lived.

import { useQuery } from "@tanstack/react-query";

import { api } from "./client";
import type {
  CareerSimulation,
  ClubFitResponse,
  ClubHit,
  Explanation,
  MarketValuePoint,
  PlayerHit,
  PlayerProfile,
  PositionPrediction,
  PotentialPrediction,
  RadarResponse,
  SimilarResponse,
  SquadAnalysis,
  ValuePrediction,
} from "./types";

const LONG = 1000 * 60 * 10; // model outputs are stable within a session

export function usePlayerSearch(q: string) {
  return useQuery({
    queryKey: ["search", q],
    queryFn: () => api.get<PlayerHit[]>(`/players/search?q=${encodeURIComponent(q)}&limit=10`),
    enabled: q.trim().length >= 2,
    staleTime: 1000 * 30,
  });
}

export function usePlayer(id: number) {
  return useQuery({
    queryKey: ["player", id],
    queryFn: () => api.get<PlayerProfile>(`/players/${id}`),
  });
}

export function useRadar(id: number) {
  return useQuery({
    queryKey: ["radar", id],
    queryFn: () => api.get<RadarResponse>(`/players/${id}/radar`),
    staleTime: LONG,
  });
}

export function useMarketValues(id: number) {
  return useQuery({
    queryKey: ["market-values", id],
    queryFn: () => api.get<MarketValuePoint[]>(`/players/${id}/market-values`),
    staleTime: LONG,
  });
}

export function useValue(id: number) {
  return useQuery({
    queryKey: ["value", id],
    queryFn: () => api.get<ValuePrediction>(`/players/${id}/predict/value`),
    staleTime: LONG,
  });
}

export function usePotential(id: number, horizon = 3) {
  return useQuery({
    queryKey: ["potential", id, horizon],
    queryFn: () => api.get<PotentialPrediction>(`/players/${id}/predict/potential?horizon=${horizon}`),
    staleTime: LONG,
    retry: false, // 422 when no market value — don't hammer
  });
}

export function usePosition(id: number) {
  return useQuery({
    queryKey: ["position", id],
    queryFn: () => api.get<PositionPrediction>(`/players/${id}/predict/position`),
    staleTime: LONG,
  });
}

export function useSimilar(id: number, mode: "current" | "career") {
  return useQuery({
    queryKey: ["similar", id, mode],
    queryFn: () => api.get<SimilarResponse>(`/players/${id}/similar?mode=${mode}&k=12`),
    staleTime: LONG,
  });
}

export function useClubFit(id: number) {
  return useQuery({
    queryKey: ["club-fit", id],
    queryFn: () => api.get<ClubFitResponse>(`/players/${id}/club-fit?top=12`),
    staleTime: LONG,
  });
}

export function useCareerSim(id: number) {
  return useQuery({
    queryKey: ["career", id],
    queryFn: () => api.get<CareerSimulation>(`/players/${id}/career-simulation`),
    staleTime: LONG,
    retry: false,
  });
}

export function useExplain(id: number) {
  return useQuery({
    queryKey: ["explain", id],
    queryFn: () => api.get<Explanation>(`/players/${id}/explain`),
    staleTime: LONG,
    retry: false,
  });
}

export function useClubSearch(q: string) {
  return useQuery({
    queryKey: ["club-search", q],
    queryFn: () => api.get<ClubHit[]>(`/clubs?q=${encodeURIComponent(q)}&limit=10`),
    enabled: q.trim().length >= 2,
    staleTime: 1000 * 30,
  });
}

export function useSquadAnalysis(clubId: number | null) {
  return useQuery({
    queryKey: ["squad", clubId],
    queryFn: () => api.get<SquadAnalysis>(`/clubs/${clubId}/squad-analysis`),
    enabled: clubId != null,
    staleTime: LONG,
  });
}
