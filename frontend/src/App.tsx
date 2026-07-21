import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { CareerSimulator } from "./pages/CareerSimulator";
import { ClubFinder } from "./pages/ClubFinder";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { NotFound } from "./pages/NotFound";
import { PlayerLayout } from "./pages/PlayerLayout";
import { PlayerOverview } from "./pages/PlayerOverview";
import { SimilarPlayers } from "./pages/SimilarPlayers";
import { SquadAnalyzer } from "./pages/SquadAnalyzer";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="squad" element={<SquadAnalyzer />} />
        <Route path="login" element={<Login />} />
        <Route path="player/:id" element={<PlayerLayout />}>
          <Route index element={<PlayerOverview />} />
          <Route path="similar" element={<SimilarPlayers />} />
          <Route path="clubs" element={<ClubFinder />} />
          <Route path="career" element={<CareerSimulator />} />
        </Route>
        {/* catch-all lives INSIDE Layout so the navbar always survives (CRIT-01) */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
