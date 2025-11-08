import { useState } from 'react';

export default function Counter({ initial = 0 }) {
  const [count, setCount] = useState(initial);

  return (
    <div className="counter">
      <p className="counter__value">
        Counter value:
        <span>{count}</span>
      </p>
      <div className="counter__controls">
        <button type="button" onClick={() => setCount((value) => value - 1)}>
          -1
        </button>
        <button type="button" onClick={() => setCount(initial)}>
          Reset
        </button>
        <button type="button" onClick={() => setCount((value) => value + 1)}>
          +1
        </button>
      </div>
    </div>
  );
}

