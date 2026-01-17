import { useState, useEffect } from "react";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetch("/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  return (
    <div style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>Szymon</h1>
      <p>Personal assistant gateway</p>
      <p>
        API Status: <strong>{health?.status ?? "loading..."}</strong>
      </p>
    </div>
  );
}
