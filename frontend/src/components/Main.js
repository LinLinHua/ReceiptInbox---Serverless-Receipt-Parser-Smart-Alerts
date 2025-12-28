import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import Login from "./Login";
import Register from "./Register";
import Dashboard from "./Dashboard";
import Uploader from "./Uploader";

function Main(props) {
  const { isLoggedIn, handleLoggedIn } = props;

  const showLogin = () => {
    return isLoggedIn ? (
      <Navigate to="/dashboard" />
    ) : (
      <Login handleLoggedIn={handleLoggedIn} />
    );
  };

  const showRegister = () => {
    return isLoggedIn ? <Navigate to="/dashboard" /> : <Register />;
  };

  const showDashboard = () => {
    return isLoggedIn ? <Dashboard /> : <Navigate to="/login" />;
  };

  const showUploader = () => {
    return isLoggedIn ? <Uploader /> : <Navigate to="/login" />;
  };

  const showHome = () => {
    return isLoggedIn ? <Navigate to="/dashboard" /> : <Navigate to="/login" />;
  };

  return (
    <div className="main">
      <Routes>
        <Route path="/" exact element={showHome()} />
        <Route path="/login" element={showLogin()} />
        <Route path="/register" element={showRegister()} />
        <Route path="/dashboard" element={showDashboard()} />
        <Route path="/upload" element={showUploader()} />
        <Route path="*" element={showHome()} />
      </Routes>
    </div>
  );
}

export default Main;
