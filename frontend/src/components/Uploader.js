import React from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { InboxOutlined } from "@ant-design/icons";
import { Upload, message } from "antd";
import { BASE_URL } from "../constants";

const { Dragger } = Upload;

const Uploader = () => {
  const navigate = useNavigate();

  const uploadToBackend = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${BASE_URL}/`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      message.success(`${file.name} uploaded successfully. Redirecting to dashboard...`);

      // Redirect to dashboard after 1 second
      setTimeout(() => {
        navigate("/dashboard");
      }, 1000);

      return response;
    } catch (error) {
      console.error("Upload error:", error);
      console.error("Error response:", error.response?.data);
      console.error("Error status:", error.response?.status);
      message.error(`Failed to upload ${file.name}. ${error.response?.data?.detail || error.message}`);
      return null;
    }
  };

  const attributes = {
    name: "file",
    multiple: true,
    accept: "image/jpeg,image/jpg,image/png",
    customRequest: async ({ file, onSuccess, onError }) => {
      const response = await uploadToBackend(file);

      if (response && response.status === 200) {
        onSuccess(response.data);
      } else {
        onError(new Error("Upload failed"));
      }
    },
    onChange(info) {
      const { status } = info.file;

      if (status !== "uploading") {
        console.log(info.file, info.fileList);
      }
      if (status === "done") {
        console.log(`${info.file.name} uploaded successfully.`);
      } else if (status === "error") {
        console.log(`Failed to upload ${info.file.name}.`);
      }
    },
    onDrop(e) {
      console.log("Dropped files", e.dataTransfer.files);
    },
  };

  return (
    <div className="dragger-window">
      <Dragger {...attributes}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">
          Click or drag receipt image to this area to upload
        </p>
        <p className="ant-upload-hint">Support for JPEG, JPG, and PNG images.</p>
      </Dragger>
    </div>
  );
};

export default Uploader;
