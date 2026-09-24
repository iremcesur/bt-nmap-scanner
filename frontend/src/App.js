import React, { useState } from 'react';
import './App.css';
import AdvancedNmap from './AdvancedNmap';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Bluetooth Nmap-Style Fingerprinting</h1>
      </header>
      <main>
        <AdvancedNmap />
      </main>
    </div>
  );
}

export default App;
