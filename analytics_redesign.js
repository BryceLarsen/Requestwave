// ANALYTICS TAB REDESIGN - All Requirements Implementation
// This file contains the complete redesigned Analytics tab code to replace the existing implementation

const AnalyticsTabRedesigned = () => {
  // NEW: Analytics state management for redesign
  const [analyticsPeriod, setAnalyticsPeriod] = useState('last7days');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [topSongsLimit, setTopSongsLimit] = useState(10);
  const [topRequestersLimit, setTopRequestersLimit] = useState(10);

  // Period options for dropdown
  const periodOptions = [
    { value: 'today', label: 'Today', days: 1 },
    { value: 'last7days', label: 'Last 7 days', days: 7 },
    { value: 'last30days', label: 'Last 30 days', days: 30 },
    { value: 'last3months', label: 'Last 3 months', days: 90 },
    { value: 'lastyear', label: 'Last Year', days: 365 },
    { value: 'alltime', label: 'All time', days: null }
  ];

  // Fetch analytics data with new period system
  const fetchAnalyticsData = async (period = analyticsPeriod) => {
    setAnalyticsLoading(true);
    try {
      const selectedPeriod = periodOptions.find(p => p.value === period);
      const days = selectedPeriod?.days;
      
      const response = await axios.get(`${API}/analytics/daily`, {
        params: { days: days },
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      setAnalyticsData(response.data);
      
      // Log telemetry
      console.log('analytics_data_fetch_success', {
        period: period,
        total_requests: response.data?.totals?.total_requests || 0,
        unique_requesters: response.data?.totals?.unique_requesters || 0,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      console.error('Error fetching analytics:', error);
      console.log('analytics_data_fetch_error', {
        period: period,
        error: error.message,
        timestamp: new Date().toISOString()
      });
    } finally {
      setAnalyticsLoading(false);
    }
  };

  // Handle period change
  const handlePeriodChange = (newPeriod) => {
    setAnalyticsPeriod(newPeriod);
    // Persist in localStorage
    localStorage.setItem('analytics_period', newPeriod);
    fetchAnalyticsData(newPeriod);
  };

  // Calculate digital tip percentage
  const calculateDigitalTipPercentage = () => {
    if (!analyticsData || !analyticsData.totals) return { percentage: 0, count: 0, total: 0 };
    
    // Count requests with digital tips (> 0 tip_amount)
    const totalRequests = analyticsData.totals.total_requests || 0;
    const requestsWithTips = analyticsData.totals.requests_with_tips || 0;
    
    const percentage = totalRequests > 0 ? Math.round((requestsWithTips / totalRequests) * 100) : 0;
    
    return {
      percentage: percentage,
      count: requestsWithTips,
      total: totalRequests
    };
  };

  // Export CSV functionality
  const exportAnalyticsCSV = async () => {
    try {
      console.log('analytics_csv_export_start', {
        period: analyticsPeriod,
        timestamp: new Date().toISOString()
      });
      
      const response = await axios.get(`${API}/analytics/export-requesters`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `requesters-analytics-${new Date().toISOString().split('T')[0]}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
      
      console.log('analytics_csv_export_success', {
        period: analyticsPeriod,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      console.error('Error exporting CSV:', error);
      console.log('analytics_csv_export_error', {
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  };

  // Load saved period preference
  useEffect(() => {
    const savedPeriod = localStorage.getItem('analytics_period');
    if (savedPeriod && periodOptions.find(p => p.value === savedPeriod)) {
      setAnalyticsPeriod(savedPeriod);
    }
  }, []);

  // Fetch data when period changes or tab becomes active
  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchAnalyticsData(analyticsPeriod);
    }
  }, [activeTab, analyticsPeriod]);

  const tipData = calculateDigitalTipPercentage();

  return (
    <div className="space-y-6">
      {/* NEW: Redesigned Analytics Header with Period Dropdown */}
      <div className="bg-gray-800 rounded-xl p-6">
        <p className="text-gray-300 mb-4">Insights into your audience and performance</p>
        
        {/* NEW: Period Dropdown (replaces Daily/Weekly/Monthly buttons) */}
        <div className="mb-6">
          <label className="block text-gray-300 text-sm font-bold mb-2">Period</label>
          <select
            value={analyticsPeriod}
            onChange={(e) => handlePeriodChange(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:ring-purple-500 focus:border-purple-500"
          >
            {periodOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Analytics Summary Cards with Export CSV */}
        {analyticsData && (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-gray-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300">Total Requests</h3>
                <p className="text-2xl font-bold text-purple-400">{analyticsData.totals.total_requests}</p>
              </div>
              <div className="bg-gray-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300">Unique Requesters</h3>
                <p className="text-2xl font-bold text-blue-400">{analyticsData.totals.unique_requesters}</p>
              </div>
              <div className="bg-gray-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300">Period</h3>
                <p className="text-lg font-bold text-gray-300">{periodOptions.find(p => p.value === analyticsPeriod)?.label}</p>
              </div>
              {/* NEW: Digital Tip Percentage Metric */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-300">Digital Tips</h3>
                <p className="text-2xl font-bold text-green-400">{tipData.percentage}%</p>
                <p className="text-xs text-gray-400">({tipData.count} of {tipData.total} requests)</p>
              </div>
            </div>
            
            {/* NEW: Export CSV Button at Bottom of First Analytics Box */}
            <div className="flex justify-end">
              <button
                onClick={exportAnalyticsCSV}
                className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-medium transition duration-300 flex items-center space-x-2"
              >
                <span>📊</span>
                <span>Export CSV</span>
              </button>
            </div>
          </div>
        )}

        {analyticsLoading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400 mx-auto"></div>
            <p className="text-gray-400 mt-2">Loading analytics...</p>
          </div>
        )}
      </div>

      {/* Analytics Charts Section - Redesigned */}
      {analyticsData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Most Requested Songs with Top 10/20/50 Dropdown */}
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">🎵 Most Requested Songs</h3>
              {/* NEW: Top N Dropdown */}
              <select
                value={topSongsLimit}
                onChange={(e) => setTopSongsLimit(parseInt(e.target.value))}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
              >
                <option value={10}>Top 10</option>
                <option value={20}>Top 20</option>
                <option value={50}>Top 50</option>
              </select>
            </div>
            <div className="space-y-3">
              {analyticsData.top_songs.slice(0, topSongsLimit).map((item, index) => (
                <div key={index} className="flex justify-between items-center">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{item.song}</p>
                  </div>
                  <div className="text-right">
                    <span className="bg-purple-600 px-2 py-1 rounded-full text-xs">
                      {item.count}
                    </span>
                  </div>
                </div>
              ))}
              
              {analyticsData.top_songs.length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  <p>No requests yet in this period</p>
                </div>
              )}
            </div>
          </div>

          {/* Most Active Requesters with Top 10/20/50 Dropdown */}
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">👥 Most Active Requesters</h3>
              {/* NEW: Top N Dropdown */}
              <select
                value={topRequestersLimit}
                onChange={(e) => setTopRequestersLimit(parseInt(e.target.value))}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
              >
                <option value={10}>Top 10</option>
                <option value={20}>Top 20</option>
                <option value={50}>Top 50</option>
              </select>
            </div>
            <div className="space-y-3">
              {analyticsData.top_requesters.slice(0, topRequestersLimit).map((item, index) => (
                <div key={index} className="flex justify-between items-center">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{item.requester_name}</p>
                    <p className="text-gray-400 text-xs">{item.email}</p>
                  </div>
                  <div className="text-right">
                    <span className="bg-blue-600 px-2 py-1 rounded-full text-xs">
                      {item.request_count}
                    </span>
                    {item.total_tips > 0 && (
                      <p className="text-green-400 text-xs mt-1">${item.total_tips}</p>
                    )}
                  </div>
                </div>
              ))}
              
              {analyticsData.top_requesters.length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  <p>No requesters yet in this period</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Audience Requesters Box - REMOVED per requirements */}
      {/* This section has been completely removed as requested */}
    </div>
  );
};

// Additional state needed for Analytics redesign
const [analyticsPeriod, setAnalyticsPeriod] = useState('last7days');
const [topSongsLimit, setTopSongsLimit] = useState(10);
const [topRequestersLimit, setTopRequestersLimit] = useState(10);

// Telemetry functions for show management
const logShowArchiveStart = (showId, showName) => {
  console.log('show_archive_start', {
    show_id: showId,
    show_name: showName,
    timestamp: new Date().toISOString()
  });
};

const logShowArchiveSuccess = (showId, showName) => {
  console.log('show_archive_success', {
    show_id: showId,
    show_name: showName,
    timestamp: new Date().toISOString()
  });
};

const logShowArchiveError = (showId, showName, error) => {
  console.log('show_archive_error', {
    show_id: showId,
    show_name: showName,
    error: error.message,
    timestamp: new Date().toISOString()
  });
};

const logShowRestoreStart = (showId, showName) => {
  console.log('show_restore_start', {
    show_id: showId,
    show_name: showName,
    timestamp: new Date().toISOString()
  });
};

const logShowRestoreSuccess = (showId, showName) => {
  console.log('show_restore_success', {
    show_id: showId,
    show_name: showName,
    timestamp: new Date().toISOString()
  });
};

const logShowRestoreError = (showId, showName, error) => {
  console.log('show_restore_error', {
    show_id: showId,
    show_name: showName,
    error: error.message,
    timestamp: new Date().toISOString()
  });
};

// Updated show management handlers with telemetry
const handleArchiveShowWithTelemetry = async (showId, showName) => {
  logShowArchiveStart(showId, showName);
  
  if (confirm(`Archive show "${showName}"? The show and its requests will be moved to the archived section.`)) {
    try {
      await axios.put(`${API}/shows/${showId}/archive`);
      fetchGroupedRequests();
      fetchShows();
      fetchCurrentShow();
      alert(`Show "${showName}" archived successfully!`);
      
      logShowArchiveSuccess(showId, showName);
    } catch (error) {
      console.error('Error archiving show:', error);
      alert('Error archiving show. Please try again.');
      logShowArchiveError(showId, showName, error);
    }
  }
};

const handleRestoreShowWithTelemetry = async (showId, showName) => {
  logShowRestoreStart(showId, showName);
  
  if (confirm(`Restore show "${showName}" from archive? It will be moved back to the active shows section.`)) {
    try {
      await axios.put(`${API}/shows/${showId}/restore`);
      fetchGroupedRequests();
      fetchShows();
      fetchCurrentShow();
      alert(`Show "${showName}" restored successfully!`);
      
      logShowRestoreSuccess(showId, showName);
    } catch (error) {
      console.error('Error restoring show:', error);
      alert('Error restoring show. Please try again.');
      logShowRestoreError(showId, showName, error);
    }
  }
};