import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router';
import Layout from './components/Layout';
import HomePage from './components/HomePage';
import HistoryPage from './components/HistoryPage';
import ConversationPage from './components/ConversationPage';
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/conversation" element={<ConversationPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
