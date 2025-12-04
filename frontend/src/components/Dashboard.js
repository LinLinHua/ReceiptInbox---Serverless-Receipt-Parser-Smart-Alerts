import React, { useState } from "react";
import { Tabs } from "antd";
import axios from "axios";

import Statistic from "./Statistic";
import UploadPostButton from "./UploadPostButton";

const { TabPane } = Tabs;

function Dashboard(props) {
  const [activeTab, setActiveTab] = useState("statistic");
  // TODO: more tabs?

  const showPost = (type) => {
    setActiveTab(type);
  };

  return (
    <div className="home">
      <div className="display">
        <Tabs
          onChange={(key) => setActiveTab(key)}
          defaultActiveKey="statistic"
          activeKey={activeTab}
          tabBarExtraContent={<UploadPostButton onShowPost={showPost} />}
        >
          <TabPane
            tab={
              <span style={{ fontSize: "18px", fontWeight: "bold" }}>
                Statistic
              </span>
            }
            key="statistic"
          >
            <Statistic></Statistic>
          </TabPane>
        </Tabs>
      </div>
    </div>
  );
}

export default Dashboard;
