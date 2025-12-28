import React from "react";
import Statistic from "./Statistic";

function Dashboard(props) {
  return (
    <div className="home">
      <div className="display">
        <Statistic></Statistic>
      </div>
    </div>
  );
}

export default Dashboard;
