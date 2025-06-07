import React, { useState } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [file, setFile] = useState(null);
  const [vouchers, setVouchers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (selectedFile) => {
    setFile(selectedFile);
    setVouchers([]);
    setStatus("");
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls')) {
        handleFileChange(droppedFile);
      } else {
        setStatus("Please select an Excel file (.xlsx or .xls)");
      }
    }
  };

  const uploadFile = async () => {
    if (!file) {
      setStatus("Please select a file first");
      return;
    }

    setLoading(true);
    setStatus("Parsing Excel file...");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(`${API}/upload-excel`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setVouchers(response.data.vouchers);
      setStatus(`Successfully parsed ${response.data.vouchers.length} voucher records`);
    } catch (error) {
      console.error("Error uploading file:", error);
      setStatus(`Error: ${error.response?.data?.detail || "Failed to process file"}`);
    } finally {
      setLoading(false);
    }
  };

  const generateVouchers = async () => {
    if (vouchers.length === 0) {
      setStatus("No voucher data available. Please upload an Excel file first.");
      return;
    }

    setLoading(true);
    setStatus("Generating PDF vouchers...");

    try {
      const response = await axios.post(`${API}/generate-vouchers`, vouchers, {
        responseType: 'blob',
        headers: {
          'Accept': 'application/zip'
        }
      });

      console.log('Response received:', response);
      console.log('Response headers:', response.headers);
      console.log('Response data type:', typeof response.data);
      console.log('Response data size:', response.data.size);

      // Check if we actually got a blob
      if (response.data && response.data.size > 0) {
        // Method 1: Try direct download
        try {
          const blob = new Blob([response.data], { type: 'application/zip' });
          const url = window.URL.createObjectURL(blob);
          
          // Generate filename with timestamp
          const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
          const filename = `hotel_vouchers_${timestamp}.zip`;
          
          // Try using the download attribute
          const link = document.createElement('a');
          link.style.display = 'none';
          link.href = url;
          link.download = filename;
          
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          
          // Cleanup after a short delay
          setTimeout(() => {
            window.URL.revokeObjectURL(url);
          }, 1000);

          setStatus(`Successfully generated and downloaded ${vouchers.length} vouchers as ${filename}`);
          
        } catch (downloadError) {
          console.error('Direct download failed, trying alternative method:', downloadError);
          
          // Method 2: Alternative download method
          try {
            const blob = new Blob([response.data], { type: 'application/zip' });
            
            // For browsers that don't support download attribute
            if (window.navigator && window.navigator.msSaveOrOpenBlob) {
              // IE/Edge
              window.navigator.msSaveOrOpenBlob(blob, `hotel_vouchers_${Date.now()}.zip`);
            } else {
              // Modern browsers with URL.createObjectURL
              const url = URL.createObjectURL(blob);
              window.open(url, '_blank');
              setTimeout(() => URL.revokeObjectURL(url), 1000);
            }
            
            setStatus(`Successfully generated ${vouchers.length} vouchers. Check your downloads folder.`);
          } catch (altError) {
            console.error('Alternative download method also failed:', altError);
            setStatus(`Vouchers generated successfully, but automatic download failed. Please try again or contact support.`);
          }
        }
      } else {
        throw new Error('Received empty response from server');
      }
    } catch (error) {
      console.error("Error generating vouchers:", error);
      console.error("Error details:", error.response);
      
      // More detailed error handling
      if (error.response) {
        if (error.response.data instanceof Blob) {
          // If error response is a blob, try to read it as text
          const errorText = await error.response.data.text();
          setStatus(`Error: ${errorText}`);
        } else {
          setStatus(`Error: ${error.response.data?.detail || error.response.statusText || "Failed to generate vouchers"}`);
        }
      } else if (error.request) {
        setStatus("Error: No response from server. Please check your connection.");
      } else {
        setStatus(`Error: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-yellow-50">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-block bg-gradient-to-r from-red-600 to-yellow-500 text-white px-8 py-4 rounded-xl shadow-lg mb-4">
              <h1 className="text-3xl font-bold">LGT HOTEL STAYS</h1>
              <p className="text-red-100 mt-1">Voucher Generator</p>
            </div>
            <p className="text-gray-600 text-lg">
              Upload your Excel file to generate professional hotel booking confirmation vouchers
            </p>
          </div>

          {/* File Upload Area */}
          <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Step 1: Upload Excel File</h2>
            
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 ${
                dragActive
                  ? "border-red-500 bg-red-50"
                  : "border-gray-300 hover:border-red-400 hover:bg-gray-50"
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <div className="space-y-4">
                <div className="text-4xl text-gray-400">📁</div>
                <div>
                  <p className="text-lg text-gray-600 mb-2">
                    Drag and drop your Excel file here, or
                  </p>
                  <label className="inline-block bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-3 rounded-lg cursor-pointer hover:from-red-600 hover:to-red-700 transition-all duration-200 shadow-md hover:shadow-lg">
                    Choose File
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={(e) => handleFileChange(e.target.files[0])}
                      className="hidden"
                    />
                  </label>
                </div>
                {file && (
                  <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-green-700 font-medium">
                      ✓ Selected: {file.name}
                    </p>
                    <p className="text-green-600 text-sm">
                      Size: {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6 flex gap-4">
              <button
                onClick={uploadFile}
                disabled={!file || loading}
                className="flex-1 bg-gradient-to-r from-yellow-500 to-yellow-600 text-white px-6 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:from-yellow-600 hover:to-yellow-700 transition-all duration-200 shadow-md hover:shadow-lg"
              >
                {loading ? "Processing..." : "Parse Excel File"}
              </button>
            </div>
          </div>

          {/* Voucher Preview */}
          {vouchers.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Step 2: Review Parsed Data</h2>
              
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <p className="text-gray-700">
                  <span className="font-semibold text-green-600">{vouchers.length}</span> voucher records found
                </p>
              </div>

              <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left">#</th>
                      <th className="px-4 py-2 text-left">Confirmation Number</th>
                      <th className="px-4 py-2 text-left">Guest Name</th>
                      <th className="px-4 py-2 text-left">Hotel</th>
                      <th className="px-4 py-2 text-left">Check-in</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vouchers.map((voucher, index) => (
                      <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-2">{voucher.row_number}</td>
                        <td className="px-4 py-2">
                          {voucher.data.confirmation_number || voucher.data.booking_id || 'N/A'}
                        </td>
                        <td className="px-4 py-2">
                          {voucher.data.lead_passenger_name || voucher.data.guest_name || voucher.data.name || 'N/A'}
                        </td>
                        <td className="px-4 py-2">
                          {voucher.data.hotel_name || voucher.data.hotel || 'N/A'}
                        </td>
                        <td className="px-4 py-2">
                          {voucher.data.check_in_date || voucher.data.checkin_date || 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Generate Vouchers */}
          {vouchers.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Step 3: Generate PDF Vouchers</h2>
              
              <div className="space-y-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-blue-700">
                    Ready to generate <span className="font-semibold">{vouchers.length}</span> professional hotel vouchers in PDF format.
                    All vouchers will be packaged in a single ZIP file for easy download.
                  </p>
                </div>

                <button
                  onClick={generateVouchers}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-red-600 to-red-700 text-white px-6 py-4 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:from-red-700 hover:to-red-800 transition-all duration-200 shadow-md hover:shadow-lg text-lg"
                >
                  {loading ? "Generating PDFs..." : `Generate ${vouchers.length} PDF Vouchers`}
                </button>
                
                {/* Debug download button */}
                <button
                  onClick={async () => {
                    try {
                      // Direct API call for testing
                      const response = await fetch(`${API}/generate-vouchers`, {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(vouchers)
                      });
                      
                      if (response.ok) {
                        const blob = await response.blob();
                        console.log('Blob size:', blob.size);
                        
                        // Create download using fetch API
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `vouchers_${Date.now()}.zip`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        
                        setStatus('Direct download attempted via fetch API');
                      } else {
                        setStatus(`Direct download failed: ${response.status}`);
                      }
                    } catch (err) {
                      console.error('Direct download error:', err);
                      setStatus(`Direct download error: ${err.message}`);
                    }
                  }}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-blue-500 to-blue-600 text-white px-6 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-md hover:shadow-lg"
                >
                  Test Direct Download (Debug)
                </button>
              </div>
            </div>
          )}

          {/* Status Messages */}
          {status && (
            <div className={`mt-6 p-4 rounded-lg ${
              status.includes('Error') ? 'bg-red-50 border border-red-200 text-red-700' :
              status.includes('Successfully') ? 'bg-green-50 border border-green-200 text-green-700' :
              'bg-blue-50 border border-blue-200 text-blue-700'
            }`}>
              <p className="font-medium">{status}</p>
            </div>
          )}

          {/* Instructions */}
          <div className="mt-8 bg-gray-50 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Excel File Requirements</h3>
            <div className="text-gray-600 space-y-2 text-sm">
              <p>• Your Excel file should contain the following columns (case-insensitive):</p>
              <div className="grid grid-cols-2 gap-2 ml-4">
                <span>• Confirmation Number</span>
                <span>• Hotel Name</span>
                <span>• Guest/Lead Passenger Name</span>
                <span>• Address</span>
                <span>• Check-in Date</span>
                <span>• Check-out Date</span>
                <span>• Room Type</span>
                <span>• Number of Rooms/Adults/Children</span>
              </div>
              <p>• Column names are flexible - the system will try to match common variations</p>
              <p>• Each row represents one booking/voucher</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
