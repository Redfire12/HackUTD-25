import { useState } from "react";
import axios from "axios";

function App() {
  const [feedback, setFeedback] = useState("");
  const [sentiment, setSentiment] = useState(null);
  const [story, setStory] = useState(null);
  const [insights, setInsights] = useState(null);

  const analyzeFeedback = async () => {
    const res = await axios.post("http://127.0.0.1:8000/analyze", { text: feedback });
    setSentiment(res.data);
  };

  const generateStory = async () => {
    const res = await axios.post("http://127.0.0.1:8000/generate-story", { text: feedback });
    setStory(res.data.story);
  };

  const getInsights = async () => {
    const res = await axios.get("http://127.0.0.1:8000/insights/current");
    setInsights(res.data);
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h2>AI Product Insights Dashboard</h2>

      <textarea
        rows="3"
        cols="50"
        placeholder="Enter feedback here..."
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
      />
      <br />
      <button onClick={analyzeFeedback}>Analyze</button>
      <button onClick={generateStory} style={{ marginLeft: "0.5rem" }}>
        Generate Story
      </button>
      <button onClick={getInsights} style={{ marginLeft: "0.5rem" }}>
        View Insights
      </button>

      {sentiment && (
        <div style={{ marginTop: "1rem" }}>
          <p><b>Sentiment:</b> {sentiment.sentiment.toFixed(2)}</p>
          <p><b>Label:</b> {sentiment.label}</p>
        </div>
      )}

      {story && (
        <div style={{ marginTop: "1rem" }}>
          <h3>User Story</h3>
          <p>{story}</p>
        </div>
      )}

      {insights && (
        <div style={{ marginTop: "1rem" }}>
          <h3>Insights</h3>
          <pre>{JSON.stringify(insights, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
