/**
 * Chemical Saver - Corva UI Entry Point
 * Developer: PRABHAT
 */

import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';
import './styles/App.css';

// Corva UI wrapper
const ChemicalSaverApp = (props) => {
  return <App {...props} />;
};

// Export for Corva
export default ChemicalSaverApp;

// For local development
if (process.env.NODE_ENV === 'development') {
  const rootElement = document.getElementById('root');
  if (rootElement) {
    ReactDOM.render(
      <React.StrictMode>
        <ChemicalSaverApp />
      </React.StrictMode>,
      rootElement
    );
  }
}
