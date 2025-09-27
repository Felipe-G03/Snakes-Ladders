import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";

import Game from "./pages/game";
import Tutorial from "./pages/tutorial";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Game />} />
        <Route path="/tutorial" element={<Tutorial />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
