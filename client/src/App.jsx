import { useState } from 'react';
import Counter from './components/Counter.jsx';

export default function App() {
  const [message, setMessage] = useState('Hello from your base frontend!');

  return (
    <div className="app">
      <header className="app__header">
        <h1>{message}</h1>
        <p>Start tweaking by editing `client/src/App.jsx`.</p>
      </header>
      <main className="app__main">
        <section className="app__card">
          <h2>Counter</h2>
          <Counter />
        </section>
      </main>
      <footer className="app__footer">
        <button type="button" onClick={() => setMessage('You just customized this!')}>
          Update Message
        </button>
      </footer>
    </div>
  );
}

