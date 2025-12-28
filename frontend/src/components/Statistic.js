import React, { useState, useEffect } from "react";
import {
  Card,
  Tag,
  Spin,
  Alert,
  Row,
  Col,
  Statistic,
  Badge,
  Empty,
  Button,
  Modal,
  Descriptions,
  Tabs,
  Popconfirm,
  Input,
  message as antMessage,
} from "antd";
import {
  DollarOutlined,
  ShopOutlined,
  CalendarOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
  PieChartOutlined,
  BarChartOutlined,
  LineChartOutlined,
  DeleteOutlined,
  CheckOutlined,
  MailOutlined,
  BellOutlined,
} from "@ant-design/icons";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import axios from "axios";
import { BASE_URL } from "../constants";
import "./Dashboard.css";

const { TabPane } = Tabs;

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8", "#82CA9D", "#FFC658", "#FF6B9D"];

function Dashboard(props) {
  const [receipts, setReceipts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedReceipt, setSelectedReceipt] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [emailModalVisible, setEmailModalVisible] = useState(false);
  const [stats, setStats] = useState({ total: 0, completed: 0, processing: 0, anomalies: 0 });
  const [analytics, setAnalytics] = useState({
    byCategory: [],
    byMerchant: [],
    overTime: [],
    totalSpent: 0,
  });
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);
  const [subscribing, setSubscribing] = useState(false);

  useEffect(() => {
    fetchReceipts();
    // Removed auto-refresh - use manual Refresh button instead
  }, []);

  const fetchReceipts = async () => {
    try {
      const response = await axios.get(`${BASE_URL}/receipts`);
      const receiptsData = response.data.receipts || [];
      setReceipts(receiptsData);

      const completed = receiptsData.filter((r) => r.status === "COMPLETED").length;
      const processing = receiptsData.filter((r) => r.status === "PROCESSING").length;
      const anomalies = receiptsData.filter((r) => r.alerts && r.alerts.length > 0).length;

      setStats({
        total: receiptsData.length,
        completed,
        processing,
        anomalies,
      });

      calculateAnalytics(receiptsData);
    } catch (error) {
      console.error("Error fetching receipts:", error);
    } finally {
      setLoading(false);
    }
  };

  const calculateAnalytics = (receiptsData) => {
    const completedReceipts = receiptsData.filter(
      (r) => r.status === "COMPLETED" && r.total_amount
    );

    const totalSpent = completedReceipts.reduce(
      (sum, r) => sum + parseFloat(r.total_amount || 0),
      0
    );

    const categoryMap = {};
    completedReceipts.forEach((r) => {
      const category = r.category || "Other";
      categoryMap[category] = (categoryMap[category] || 0) + parseFloat(r.total_amount || 0);
    });
    const byCategory = Object.entries(categoryMap).map(([name, value]) => ({
      name,
      value: parseFloat(value.toFixed(2)),
    }));

    const merchantMap = {};
    completedReceipts.forEach((r) => {
      const merchant = r.merchant_name || "Unknown";
      merchantMap[merchant] = (merchantMap[merchant] || 0) + parseFloat(r.total_amount || 0);
    });
    const byMerchant = Object.entries(merchantMap)
      .map(([name, value]) => ({
        name,
        value: parseFloat(value.toFixed(2)),
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5);

    const dateMap = {};
    completedReceipts.forEach((r) => {
      const date = r.purchase_date || new Date(r.created_at).toISOString().split("T")[0];
      dateMap[date] = (dateMap[date] || 0) + parseFloat(r.total_amount || 0);
    });
    const overTime = Object.entries(dateMap)
      .map(([date, amount]) => ({
        date,
        amount: parseFloat(amount.toFixed(2)),
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date));

    setAnalytics({
      byCategory,
      byMerchant,
      overTime,
      totalSpent: parseFloat(totalSpent.toFixed(2)),
    });
  };

  const getCategoryColor = (category) => {
    const colors = {
      "Food & Dining": "magenta",
      Groceries: "green",
      Shopping: "blue",
      Transportation: "orange",
      Entertainment: "purple",
      Healthcare: "red",
      Utilities: "cyan",
      Other: "default",
    };
    return colors[category] || "default";
  };

  const showReceiptDetails = (receipt) => {
    setSelectedReceipt(receipt);
    setModalVisible(true);
  };

  const completeReceipt = async (receiptId) => {
    try {
      await axios.post(`${BASE_URL}/admin/complete-receipt/${receiptId}`);
      antMessage.success("Receipt completed successfully!");
      fetchReceipts();
    } catch (error) {
      console.error("Error completing receipt:", error);
      antMessage.error("Failed to complete receipt");
    }
  };

  const clearAllReceipts = async () => {
    try {
      await axios.delete(`${BASE_URL}/admin/clear-all-receipts`);
      antMessage.success("All receipts cleared!");
      fetchReceipts();
    } catch (error) {
      console.error("Error clearing receipts:", error);
      antMessage.error("Failed to clear receipts");
    }
  };

  const subscribeToAlerts = async () => {
    if (!email || !email.includes("@")) {
      antMessage.error("Please enter a valid email address");
      return;
    }

    setSubscribing(true);
    try {
      const response = await axios.post(
        `${BASE_URL}/admin/subscribe-anomaly-alerts?email=${encodeURIComponent(email)}`
      );
      antMessage.success("Confirmation email sent! Check your inbox and confirm the subscription.");
      setSubscribed(true);
    } catch (error) {
      console.error("Error subscribing:", error);
      antMessage.error("Failed to subscribe. Please try again.");
    } finally {
      setSubscribing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "100px" }}>
        <Spin size="large" tip="Loading receipts..." />
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>📊 Receipt Dashboard</h1>
        <div style={{ marginLeft: "auto", display: "flex", gap: "8px" }}>
          <Button
            icon={<BellOutlined />}
            onClick={() => setEmailModalVisible(true)}
            type={subscribed ? "primary" : "default"}
          >
            {subscribed ? "Alerts On" : "Alert Settings"}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchReceipts}>
            Refresh
          </Button>
          <Popconfirm
            title="Clear all receipts?"
            description="This will delete all uploaded receipts. Are you sure?"
            onConfirm={clearAllReceipts}
            okText="Yes"
            cancelText="No"
          >
            <Button icon={<DeleteOutlined />} danger>
              Clear All
            </Button>
          </Popconfirm>
        </div>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="Total Receipts"
              value={stats.total}
              prefix={<ShopOutlined />}
              valueStyle={{ color: "#1890ff" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="Total Spent"
              value={analytics.totalSpent}
              prefix={<DollarOutlined />}
              precision={2}
              valueStyle={{ color: "#52c41a" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="Processing"
              value={stats.processing}
              prefix={<SyncOutlined spin={stats.processing > 0} />}
              valueStyle={{ color: "#faad14" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="Anomalies"
              value={stats.anomalies}
              prefix={<WarningOutlined />}
              valueStyle={{ color: stats.anomalies > 0 ? "#ff4d4f" : "#52c41a" }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs defaultActiveKey="receipts" style={{ marginBottom: "24px" }}>
        <TabPane
          tab={
            <span>
              <ShopOutlined /> Receipts
            </span>
          }
          key="receipts"
        >
          {receipts.length === 0 ? (
            <Empty description="No receipts uploaded yet" style={{ marginTop: "50px" }} />
          ) : (
            <Row gutter={[16, 16]}>
              {receipts.map((receipt) => (
                <Col xs={24} sm={12} lg={8} xl={6} key={receipt.receipt_id}>
                  <Badge.Ribbon
                    text={receipt.status}
                    color={
                      receipt.status === "COMPLETED"
                        ? "green"
                        : receipt.status === "PROCESSING"
                          ? "blue"
                          : "orange"
                    }
                  >
                    <Card
                      className="receipt-card"
                      hoverable
                      onClick={() => showReceiptDetails(receipt)}
                      style={{
                        borderLeft:
                          receipt.alerts && receipt.alerts.length > 0
                            ? "4px solid #ff4d4f"
                            : "4px solid #52c41a",
                        cursor: "pointer",
                      }}
                      actions={
                        receipt.status === "PROCESSING"
                          ? [
                            <Button
                              type="link"
                              icon={<CheckOutlined />}
                              onClick={(e) => {
                                e.stopPropagation();
                                completeReceipt(receipt.receipt_id);
                              }}
                            >
                              Complete
                            </Button>,
                          ]
                          : []
                      }
                    >
                      {receipt.alerts && receipt.alerts.length > 0 && (
                        <Alert
                          message={`⚠️ ${receipt.alerts.length} Anomal${receipt.alerts.length > 1 ? 'ies' : 'y'}`}
                          description={receipt.alerts.map(a => a.type.replace(/_/g, ' ')).join(", ")}
                          type="warning"
                          showIcon
                          icon={<WarningOutlined />}
                          style={{ marginBottom: "12px" }}
                        />
                      )}

                      <div className="receipt-merchant">
                        <ShopOutlined style={{ marginRight: "8px", fontSize: "18px" }} />
                        <strong>{receipt.merchant_name || "Processing..."}</strong>
                      </div>

                      <div className="receipt-total">
                        <DollarOutlined
                          style={{ marginRight: "8px", fontSize: "24px", color: "#52c41a" }}
                        />
                        <span className="amount">
                          {receipt.total_amount ? `$${parseFloat(receipt.total_amount).toFixed(2)}` : "—"}
                        </span>
                      </div>

                      {receipt.category && (
                        <div style={{ marginTop: "12px" }}>
                          <Tag color={getCategoryColor(receipt.category)} style={{ fontSize: "14px" }}>
                            {receipt.category}
                          </Tag>
                        </div>
                      )}

                      <div className="receipt-date">
                        <CalendarOutlined style={{ marginRight: "8px" }} />
                        <span>
                          {receipt.purchase_date || new Date(receipt.created_at).toLocaleDateString()}
                        </span>
                      </div>

                      <div className="receipt-id">ID: {receipt.receipt_id?.substring(0, 8)}...</div>
                    </Card>
                  </Badge.Ribbon>
                </Col>
              ))}
            </Row>
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <PieChartOutlined /> By Category
            </span>
          }
          key="category"
        >
          {analytics.byCategory.length > 0 ? (
            <Card>
              <h3>Spending by Category</h3>
              <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                  <Pie
                    data={analytics.byCategory}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {analytics.byCategory.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Empty description="No completed receipts with categories yet. Click 'Complete' on processing receipts to see charts." />
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <BarChartOutlined /> Top Merchants
            </span>
          }
          key="merchants"
        >
          {analytics.byMerchant.length > 0 ? (
            <Card>
              <h3>Top 5 Merchants by Spending</h3>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={analytics.byMerchant}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                  <Legend />
                  <Bar dataKey="value" fill="#8884d8" name="Amount Spent" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Empty description="No completed receipts with merchant data yet" />
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <LineChartOutlined /> Spending Trends
            </span>
          }
          key="trends"
        >
          {analytics.overTime.length > 0 ? (
            <Card>
              <h3>Spending Over Time</h3>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={analytics.overTime}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                  <Legend />
                  <Line type="monotone" dataKey="amount" stroke="#8884d8" name="Daily Spending" />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Empty description="No completed receipts with dates yet" />
          )}
        </TabPane>
      </Tabs>

      <Modal
        title="Receipt Details"
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {selectedReceipt && (
          <div>
            <ReceiptImage receiptId={selectedReceipt.receipt_id} />

            <Descriptions bordered column={1} style={{ marginTop: "16px" }}>
              <Descriptions.Item label="Receipt ID">{selectedReceipt.receipt_id}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag
                  color={
                    selectedReceipt.status === "COMPLETED"
                      ? "green"
                      : selectedReceipt.status === "PROCESSING"
                        ? "blue"
                        : "orange"
                  }
                >
                  {selectedReceipt.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Merchant">{selectedReceipt.merchant_name || "—"}</Descriptions.Item>
              <Descriptions.Item label="Total Amount">
                {selectedReceipt.total_amount ? `$${parseFloat(selectedReceipt.total_amount).toFixed(2)}` : "—"}
              </Descriptions.Item>
              <Descriptions.Item label="Category">
                {selectedReceipt.category ? (
                  <Tag color={getCategoryColor(selectedReceipt.category)}>{selectedReceipt.category}</Tag>
                ) : (
                  "—"
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Purchase Date">
                {selectedReceipt.purchase_date || new Date(selectedReceipt.created_at).toLocaleDateString()}
              </Descriptions.Item>
              <Descriptions.Item label="Upload Date">
                {new Date(selectedReceipt.created_at).toLocaleString()}
              </Descriptions.Item>
              {selectedReceipt.anomalies && selectedReceipt.anomalies.length > 0 && (
                <Descriptions.Item label="Anomalies">
                  <Alert
                    message="Anomalies Detected"
                    description={selectedReceipt.anomalies.join(", ")}
                    type="warning"
                    showIcon
                  />
                </Descriptions.Item>
              )}
              {selectedReceipt.confidence && (
                <Descriptions.Item label="ML Confidence">
                  {(selectedReceipt.confidence * 100).toFixed(1)}%
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* Display Anomaly Alerts */}
            {selectedReceipt.alerts && selectedReceipt.alerts.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <Alert
                  message={`⚠️ ${selectedReceipt.alerts.length} Anomal${selectedReceipt.alerts.length > 1 ? 'ies' : 'y'} Detected`}
                  description={
                    <ul style={{ marginBottom: 0, paddingLeft: "20px" }}>
                      {selectedReceipt.alerts.map((alert, index) => (
                        <li key={index} style={{ marginBottom: "8px" }}>
                          <strong>{alert.type.replace(/_/g, ' ')}:</strong> {alert.message}
                        </li>
                      ))}
                    </ul>
                  }
                  type="warning"
                  showIcon
                />
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Email Subscription Modal */}
      <Modal
        title={
          <span>
            <BellOutlined style={{ marginRight: "8px" }} />
            Anomaly Alert Notifications
          </span>
        }
        open={emailModalVisible}
        onCancel={() => setEmailModalVisible(false)}
        footer={null}
        width={500}
      >
        <div style={{ marginBottom: "16px", color: "#666" }}>
          Get instant email notifications when suspicious activity is detected on your receipts.
        </div>

        {subscribed ? (
          <div>
            <Alert
              message="Alerts Enabled"
              description={`Notifications will be sent to: ${email}`}
              type="success"
              showIcon
              style={{ marginBottom: "16px" }}
            />
            <Button
              block
              onClick={() => {
                setSubscribed(false);
                setEmail("");
                antMessage.info("You can now enter a new email address");
              }}
            >
              Change Email
            </Button>
          </div>
        ) : (
          <div>
            <Input
              size="large"
              placeholder="Enter your email address"
              prefix={<MailOutlined />}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onPressEnter={subscribeToAlerts}
              style={{ marginBottom: "12px" }}
            />
            <Button
              type="primary"
              size="large"
              block
              icon={<BellOutlined />}
              onClick={subscribeToAlerts}
              loading={subscribing}
            >
              Subscribe to Alerts
            </Button>
            {subscribing && (
              <Alert
                message="Sending confirmation..."
                type="info"
                showIcon
                style={{ marginTop: "12px" }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

function ReceiptImage({ receiptId }) {
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchImage = async () => {
      try {
        const response = await axios.get(`${BASE_URL}/receipts/${receiptId}/image`);
        console.log("Image URL received:", response.data.image_url);
        setImageUrl(response.data.image_url);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching receipt image URL:", err);
        setError("Could not get image URL from server");
        setLoading(false);
      }
    };

    fetchImage();
  }, [receiptId]);

  const handleImageError = () => {
    console.error("Image failed to load from S3");
    setError("Could not load image from S3 (CORS or access issue)");
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "20px" }}>
        <Spin tip="Loading receipt image..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Image Not Available"
        description={error}
        type="info"
        showIcon
        style={{ marginBottom: "16px" }}
      />
    );
  }

  return (
    <div style={{ textAlign: "center", marginBottom: "16px" }}>
      <img
        src={imageUrl}
        alt="Receipt"
        onError={handleImageError}
        style={{
          maxWidth: "100%",
          maxHeight: "400px",
          border: "1px solid #d9d9d9",
          borderRadius: "8px",
        }}
      />
    </div>
  );
}

export default Dashboard;
