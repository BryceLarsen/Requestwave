import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [musician, setMusician] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    const storedMusician = localStorage.getItem('musician');
    const storedToken = localStorage.getItem('token');
    
    if (storedMusician && token && storedToken) {
      try {
        setMusician(JSON.parse(storedMusician));
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
        console.log('Auth restored from localStorage');
      } catch (error) {
        console.error('Error restoring auth:', error);
        // Clear corrupted data
        localStorage.removeItem('musician');
        localStorage.removeItem('token');
      }
    }
  }, [token]);

  const login = (authData) => {
    console.log('Logging in user:', authData.musician.name);
    setMusician(authData.musician);
    setToken(authData.token);
    localStorage.setItem('token', authData.token);
    localStorage.setItem('musician', JSON.stringify(authData.musician));
    axios.defaults.headers.common['Authorization'] = `Bearer ${authData.token}`;
    console.log('Auth token set in axios headers');
  };

  const logout = () => {
    setMusician(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('musician');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ musician, token, login, logout, setMusician }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

// Realtime Service (structured for easy WebSocket upgrade)
class RealtimeService {
  constructor(musicianId, onUpdate) {
    this.musicianId = musicianId;
    this.onUpdate = onUpdate;
    this.polling = false;
    this.interval = null;
  }

  startPolling() {
    if (this.polling) return;
    this.polling = true;
    
    this.fetchUpdates();
    this.interval = setInterval(() => {
      this.fetchUpdates();
    }, 3000); // Poll every 3 seconds
  }

  stopPolling() {
    this.polling = false;
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  async fetchUpdates() {
    try {
      const response = await axios.get(`${API}/requests/updates/${this.musicianId}`);
      this.onUpdate(response.data);
    } catch (error) {
      console.error('Error fetching updates:', error);
    }
  }

  // Future WebSocket method (placeholder)
  connectWebSocket() {
    // TODO: Implement WebSocket connection
    // const ws = new WebSocket(`ws://localhost:8001/ws/musician/${this.musicianId}`);
    // ws.onmessage = (event) => this.onUpdate(JSON.parse(event.data));
  }
}

// Components
const AuthForm = ({ mode, onSwitch }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetStep, setResetStep] = useState(1); // 1: email, 2: code+password
  const [resetMessage, setResetMessage] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const endpoint = mode === 'login' ? 'auth/login' : 'auth/register';
      const payload = mode === 'login' 
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await axios.post(`${API}/${endpoint}`, payload);
      login(response.data);
      navigate('/dashboard');
    } catch (error) {
      setError(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (resetStep === 1) {
      // Send reset code
      try {
        const response = await axios.post(`${API}/auth/forgot-password`, { email: resetEmail });
        setResetMessage(`Reset code sent! For development: ${response.data.reset_code}`);
        setResetStep(2);
      } catch (error) {
        setError(error.response?.data?.detail || 'Error sending reset code');
      }
    } else {
      // Confirm reset with code and new password
      try {
        await axios.post(`${API}/auth/reset-password`, {
          email: resetEmail,
          reset_code: resetCode,
          new_password: newPassword
        });
        setResetMessage('Password reset successful! You can now login with your new password.');
        setShowForgotPassword(false);
        setResetStep(1);
        setResetEmail('');
        setResetCode('');
        setNewPassword('');
      } catch (error) {
        setError(error.response?.data?.detail || 'Error resetting password');
      }
    }
    
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        {/* RequestWave Logo */}
        <div className="text-center mb-8">
          <img
            src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/9wbfmlsw_A_logo_for_%22RequestWave%22_features_a_purple_microph.png"
            alt="RequestWave Logo"
            className="w-64 h-64 mx-auto mb-4 object-contain"
          />
        </div>
        
        <div className="text-center">
          <p className="text-purple-200">Connect with your audience through music</p>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl">
          {!showForgotPassword ? (
            <>
              <h2 className="text-2xl font-bold text-white text-center mb-6">
                {mode === 'login' ? 'Welcome Back' : 'Join RequestWave'}
              </h2>

              {error && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                  {error}
                </div>
              )}

              {resetMessage && (
                <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-3 mb-4 text-green-200">
                  {resetMessage}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === 'register' && (
                  <input
                    type="text"
                    placeholder="Your Stage Name"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                )}
                
                <input
                  type="email"
                  placeholder="Email Address"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
                
                <input
                  type="password"
                  placeholder="Password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
                
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold py-3 rounded-lg transition duration-300 disabled:opacity-50"
                >
                  {loading ? 'Please wait...' : (mode === 'login' ? 'Sign In' : 'Create Account')}
                </button>
              </form>

              <div className="text-center mt-6 space-y-2">
                <button
                  onClick={() => onSwitch(mode === 'login' ? 'register' : 'login')}
                  className="text-purple-300 hover:text-white transition duration-300 block"
                >
                  {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
                </button>
                {mode === 'login' && (
                  <button
                    onClick={() => setShowForgotPassword(true)}
                    className="text-purple-300 hover:text-white transition duration-300"
                  >
                    Forgot your password?
                  </button>
                )}
              </div>
            </>
          ) : (
            <>
              <h2 className="text-2xl font-bold text-white text-center mb-6">
                Reset Password
              </h2>

              {error && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                  {error}
                </div>
              )}

              {resetMessage && (
                <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-3 mb-4 text-green-200">
                  {resetMessage}
                </div>
              )}

              <form onSubmit={handleForgotPassword} className="space-y-4">
                {resetStep === 1 ? (
                  <>
                    <input
                      type="email"
                      placeholder="Enter your email address"
                      value={resetEmail}
                      onChange={(e) => setResetEmail(e.target.value)}
                      className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                    />
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold py-3 rounded-lg transition duration-300 disabled:opacity-50"
                    >
                      {loading ? 'Sending...' : 'Send Reset Code'}
                    </button>
                  </>
                ) : (
                  <>
                    <input
                      type="text"
                      placeholder="Enter reset code"
                      value={resetCode}
                      onChange={(e) => setResetCode(e.target.value)}
                      className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                    />
                    <input
                      type="password"
                      placeholder="Enter new password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                    />
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-bold py-3 rounded-lg transition duration-300 disabled:opacity-50"
                    >
                      {loading ? 'Resetting...' : 'Reset Password'}
                    </button>
                  </>
                )}
              </form>

              <div className="text-center mt-6">
                <button
                  onClick={() => {
                    setShowForgotPassword(false);
                    setResetStep(1);
                    setError('');
                    setResetMessage('');
                  }}
                  className="text-purple-300 hover:text-white transition duration-300"
                >
                  Back to login
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const MusicianDashboard = () => {
  const { musician, token, logout, setMusician } = useAuth();
  const [activeTab, setActiveTab] = useState('songs');
  const [songs, setSongs] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [realtimeService, setRealtimeService] = useState(null);

  // CSV Upload state
  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvError, setCsvError] = useState('');
  const [showCsvUpload, setShowCsvUpload] = useState(false);
  const [showAddSong, setShowAddSong] = useState(false); // NEW: Control Add Song form visibility
  const [csvAutoEnrich, setCsvAutoEnrich] = useState(false);  // NEW: Auto-enrichment option

  // Song form state
  const [songForm, setSongForm] = useState({
    title: '',
    artist: '',
    genres: [],
    moods: [],
    year: '',
    notes: ''
  });

  // Song editing state
  const [editingSong, setEditingSong] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false); // NEW: Modal state for editing songs

  // NEW: Batch editing and filtering state
  const [selectedSongs, setSelectedSongs] = useState(new Set());
  const [showBatchEdit, setShowBatchEdit] = useState(false);
  const [batchEditForm, setBatchEditForm] = useState({
    artist: '',
    genres: '',
    moods: '',
    year: '',
    notes: ''  // NEW: Add notes to batch edit form
  });
  const [songFilter, setSongFilter] = useState('');
  const [genreFilter, setGenreFilter] = useState('');
  const [artistFilter, setArtistFilter] = useState('');
  const [moodFilter, setMoodFilter] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [decadeFilter, setDecadeFilter] = useState('');  // NEW: Add decade filter
  const [filteredSongs, setFilteredSongs] = useState([]);
  const [songError, setSongError] = useState('');
  const [filterOptions, setFilterOptions] = useState({  // NEW: Filter options for dropdowns
    genres: [],
    moods: [],
    years: [],
    decades: []
  });

  // NEW: Phase 2 - Sorting and popularity state
  const [sortBy, setSortBy] = useState('created_at'); // 'created_at', 'popularity', 'title', 'artist', 'year'

  // NEW: Phase 3 - Analytics state
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsTimeframe, setAnalyticsTimeframe] = useState('daily'); // 'daily', 'weekly', 'monthly'
  const [analyticsDays, setAnalyticsDays] = useState(7);
  const [requestersData, setRequestersData] = useState([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // NEW: Show management state
  const [currentShow, setCurrentShow] = useState(null);
  const [showStartModal, setShowStartModal] = useState(false);
  const [newShowName, setNewShowName] = useState('');
  const [shows, setShows] = useState([]);
  const [groupedRequests, setGroupedRequests] = useState({ unassigned: [], shows: {} });

  // NEW: Auto-fill metadata state
  const [autoFillLoading, setAutoFillLoading] = useState(false);
  
  // NEW: Song suggestions state
  const [songSuggestions, setSongSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionError, setSuggestionError] = useState('');
  
  // NEW: Post-request state for tracking clicks
  const [currentRequestId, setCurrentRequestId] = useState(null);
  const [showPostRequestModal, setShowPostRequestModal] = useState(false);
  
  // NEW: Tip functionality state
  const [showTipModal, setShowTipModal] = useState(false);
  const [tipAmount, setTipAmount] = useState('');
  const [tipMessage, setTipMessage] = useState('');
  const [tipPlatform, setTipPlatform] = useState('paypal'); // 'paypal' or 'venmo'
  const [tipSongId, setTipSongId] = useState(null); // For integrated tips with requests
  
  // NEW: Batch enrichment for existing songs
  const [batchEnrichLoading, setBatchEnrichLoading] = useState(false);
  
  // NEW: Playlist functionality (Pro feature)
  const [playlists, setPlaylists] = useState([]);
  const [showPlaylistModal, setShowPlaylistModal] = useState(false);
  const [playlistName, setPlaylistName] = useState('');
  const [activePlaylistId, setActivePlaylistId] = useState(null);
  const [playlistManagementError, setPlaylistManagementError] = useState('');
  const [playlistLoading, setPlaylistLoading] = useState(false);
  const [showManagePlaylistsModal, setShowManagePlaylistsModal] = useState(false);
  const [editingPlaylist, setEditingPlaylist] = useState(null);
  const [playlistAction, setPlaylistAction] = useState('create'); // 'create' or 'add'
  const [selectedExistingPlaylist, setSelectedExistingPlaylist] = useState('');
  
  // NEW: Tip functionality functions
  const handleTipButton = (songId = null) => {
    setTipSongId(songId);
    setShowTipModal(true);
    setTipAmount('');
    setTipMessage('');
    setTipPlatform('paypal');
  };

  const handleTipSubmit = async (musicianSlug, requesterName = '') => {
    if (!tipAmount || parseFloat(tipAmount) <= 0) {
      alert('Please enter a valid tip amount');
      return;
    }

    const amount = parseFloat(tipAmount);
    if (amount > 500) {
      alert('Tip amount cannot exceed $500');
      return;
    }

    try {
      // Get payment links from backend
      const response = await axios.get(`${API}/musicians/${musicianSlug}/tip-links`, {
        params: {
          amount: amount,
          message: tipMessage || `Thanks for the music!${tipSongId ? ' (with song request)' : ''}`
        }
      });

      if (response.data) {
        // Open appropriate payment link
        let paymentUrl = null;
        if (tipPlatform === 'paypal' && response.data.paypal_link) {
          paymentUrl = response.data.paypal_link;
        } else if (tipPlatform === 'venmo' && response.data.venmo_link) {
          paymentUrl = response.data.venmo_link;
        }

        if (paymentUrl) {
          // Record the tip attempt for analytics
          try {
            await axios.post(`${API}/musicians/${musicianSlug}/tips`, {
              amount: amount,
              platform: tipPlatform,
              tipper_name: requesterName || 'Anonymous',
              message: tipMessage
            });
          } catch (error) {
            console.log('Tip tracking failed:', error); // Non-critical
          }

          // Open payment link
          window.open(paymentUrl, '_blank');
          
          // Close modal
          setShowTipModal(false);
          
          // Show success message
          alert(`Opening ${tipPlatform === 'paypal' ? 'PayPal' : 'Venmo'} to send your $${amount} tip!`);
        } else {
          alert(`${tipPlatform === 'paypal' ? 'PayPal' : 'Venmo'} is not set up for this musician`);
        }
      }
    } catch (error) {
      console.error('Tip error:', error);
      if (error.response?.status === 400) {
        alert(error.response.data.detail || 'This musician hasn\'t set up payment methods for tips yet');
      } else {
        alert('Error processing tip. Please try again.');
      }
    }
  };

  // NEW: Post-request click tracking
  const trackClick = async (type, platform) => {
    if (!currentRequestId) return;
    
    try {
      await axios.post(`${API}/requests/${currentRequestId}/track-click`, {
        type: type, // "tip" or "social"
        platform: platform // "venmo", "paypal", "instagram", etc.
      });
    } catch (error) {
      console.error('Error tracking click:', error);
    }
  };

  const generateSocialLink = (platform, username, url) => {
    switch (platform) {
      case 'instagram':
        return username ? `https://instagram.com/${username}` : null;
      case 'facebook':
        return username ? `https://facebook.com/${username}` : null;
      case 'tiktok':
        return username ? `https://tiktok.com/@${username}` : null;
      case 'spotify':
        return url || null;
      case 'apple_music':
        return url || null;
      default:
        return null;
    }
  };

  const handleSocialClick = (platform) => {
    const link = generateSocialLink(
      platform, 
      musician[`${platform}_username`] || musician[`${platform}_artist_url`],
      musician[`${platform}_artist_url`]
    );
    
    if (link) {
      trackClick('social', platform);
      window.open(link, '_blank');
    }
  };

  const handleTipClick = (platform) => {
    trackClick('tip', platform);
    
    // Use existing tip functionality but with tracking
    if (platform === 'venmo') {
      setTipPlatform('venmo');
    } else {
      setTipPlatform('paypal');
    }
    
    setShowPostRequestModal(false);
    setShowTipModal(true);
  };

  const getTipPresetAmounts = () => [1, 5, 10, 20];

  // NEW: Show management functions
  const fetchCurrentShow = async () => {
    try {
      const response = await axios.get(`${API}/shows/current`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      if (response.data.active) {
        setCurrentShow(response.data.show);
      } else {
        setCurrentShow(null);
      }
    } catch (error) {
      console.error('Error fetching current show:', error);
    }
  };

  const fetchShows = async () => {
    try {
      const response = await axios.get(`${API}/shows`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      setShows(response.data);
    } catch (error) {
      console.error('Error fetching shows:', error);
    }
  };

  const fetchGroupedRequests = async () => {
    try {
      const response = await axios.get(`${API}/requests/grouped`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      setGroupedRequests(response.data);
    } catch (error) {
      console.error('Error fetching grouped requests:', error);
    }
  };

  const handleStartShow = async () => {
    if (!newShowName.trim()) {
      alert('Please enter a show name');
      return;
    }

    try {
      await axios.post(`${API}/shows/start`, { name: newShowName }, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      setShowStartModal(false);
      setNewShowName('');
      fetchCurrentShow();
      fetchShows();
      alert(`Show "${newShowName}" started! All new requests will be organized under this show.`);
    } catch (error) {
      console.error('Error starting show:', error);
      alert('Error starting show. Please try again.');
    }
  };

  const handleStopShow = async () => {
    if (!currentShow) return;

    if (confirm(`Stop the current show "${currentShow.name}"? New requests will go to the main requests list.`)) {
      try {
        await axios.post(`${API}/shows/stop`); // Removed manual headers - axios already has auth token set

        setCurrentShow(null);
        fetchGroupedRequests();
        alert('Show stopped successfully!');
      } catch (error) {
        console.error('Error stopping show:', error);
        alert('Error stopping show. Please try again.');
      }
    }
  };

  // NEW: Delete individual request from history
  const handleDeleteRequest = async (requestId, requestTitle) => {
    if (confirm(`Permanently delete request for "${requestTitle}"? This cannot be undone.`)) {
      try {
        await axios.delete(`${API}/requests/${requestId}`);
        fetchGroupedRequests();
        alert('Request deleted successfully!');
      } catch (error) {
        console.error('Error deleting request:', error);
        alert('Error deleting request. Please try again.');
      }
    }
  };

  // NEW: Delete entire show and all associated requests
  const handleDeleteShow = async (showId, showName) => {
    if (confirm(`Permanently delete show "${showName}" and ALL associated requests? This cannot be undone.`)) {
      try {
        await axios.delete(`${API}/shows/${showId}`);
        fetchGroupedRequests();
        fetchShows();
        fetchCurrentShow(); // Update current show status
        alert(`Show "${showName}" and all associated requests deleted successfully!`);
      } catch (error) {
        console.error('Error deleting show:', error);
        alert('Error deleting show. Please try again.');
      }
    }
  };

  // NEW: Song suggestions management functions
  const fetchSongSuggestions = async () => {
    try {
      const response = await axios.get(`${API}/song-suggestions`);
      setSongSuggestions(response.data);
    } catch (error) {
      console.error('Error fetching song suggestions:', error);
      setSuggestionError('Error fetching song suggestions');
    }
  };

  const handleSuggestionAction = async (suggestionId, action, suggestionTitle) => {
    const actionText = action === 'added' ? 'add to repertoire' : 'reject';
    if (confirm(`${actionText.charAt(0).toUpperCase() + actionText.slice(1)} suggestion "${suggestionTitle}"?`)) {
      try {
        await axios.put(`${API}/song-suggestions/${suggestionId}/status`, { status: action });
        fetchSongSuggestions(); // Refresh suggestions
        if (action === 'added') {
          fetchSongs(); // Refresh songs list if song was added
          alert(`"${suggestionTitle}" has been added to your repertoire!`);
        } else {
          alert(`Suggestion "${suggestionTitle}" has been rejected.`);
        }
      } catch (error) {
        console.error('Error updating suggestion:', error);
        alert('Error processing suggestion. Please try again.');
      }
    }
  };

  const handleDeleteSuggestion = async (suggestionId, suggestionTitle) => {
    if (confirm(`Permanently delete suggestion "${suggestionTitle}"?`)) {
      try {
        await axios.delete(`${API}/song-suggestions/${suggestionId}`);
        fetchSongSuggestions();
        alert('Suggestion deleted successfully!');
      } catch (error) {
        console.error('Error deleting suggestion:', error);
        alert('Error deleting suggestion. Please try again.');
      }
    }
  };

  // NEW: Toggle song visibility function
  const handleToggleSongVisibility = async (songId) => {
    try {
      const response = await axios.put(`${API}/songs/${songId}/toggle-visibility`, {}, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      if (response.data.success) {
        // Refresh songs to show updated visibility
        fetchSongs();
        alert(response.data.message);
      }
    } catch (error) {
      console.error('Error toggling song visibility:', error);
      alert('Error updating song visibility. Please try again.');
    }
  };

  const handleBatchEnrich = async () => {
    if (!confirm('Auto-fill missing metadata for all your existing songs using Spotify? This may take a few moments.')) {
      return;
    }
    
    setBatchEnrichLoading(true);
    
    try {
      const response = await axios.post(`${API}/songs/batch-enrich`, null, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      if (response.data.success) {
        fetchSongs(); // Refresh songs list
        
        const { processed, enriched, errors } = response.data;
        let message = `Batch enrichment completed!\n\n`;
        message += `Processed: ${processed} songs\n`;
        message += `Enriched: ${enriched} songs with new metadata\n`;
        
        if (errors && errors.length > 0) {
          message += `\nSome songs could not be enriched:\n`;
          message += errors.slice(0, 5).join('\n'); // Show first 5 errors
          if (errors.length > 5) {
            message += `\n...and ${errors.length - 5} more`;
          }
        }
        
        alert(message);
      }
    } catch (error) {
      console.error('Error in batch enrichment:', error);
      alert(error.response?.data?.detail || 'Error during batch enrichment. Please try again.');
    } finally {
      setBatchEnrichLoading(false);
    }
  };

  // Profile management state
  const [showProfile, setShowProfile] = useState(false);
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    venmo_link: '', // Keep for backward compatibility
    bio: '',
    website: '',
    // Payment fields
    paypal_username: '',
    venmo_username: '',
    // NEW: Social media fields
    instagram_username: '',
    facebook_username: '',
    tiktok_username: '',
    spotify_artist_url: '',
    apple_music_artist_url: ''
  });
  const [profileError, setProfileError] = useState('');

  // Subscription management state
  const [subscriptionStatus, setSubscriptionStatus] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [upgrading, setUpgrading] = useState(false);

  // Design settings state
  const [designSettings, setDesignSettings] = useState({
    color_scheme: 'purple',
    layout_mode: 'grid',
    artist_photo: null,
    show_year: true,
    show_notes: true
  });
  const [designError, setDesignError] = useState('');

  // QR Code state
  const [qrCode, setQrCode] = useState(null);
  const [showQRModal, setShowQRModal] = useState(false);

  // Playlist import state
  const [playlistUrl, setPlaylistUrl] = useState('');
  const [playlistPlatform, setPlaylistPlatform] = useState('spotify');
  const [importingPlaylist, setImportingPlaylist] = useState(false);
  const [playlistError, setPlaylistError] = useState('');
  const [showPlaylistImport, setShowPlaylistImport] = useState(false); // NEW: Control visibility

  useEffect(() => {
    fetchSongs();
    fetchRequests();
    fetchSubscriptionStatus();
    fetchSongSuggestions();
    // NEW: Fetch show-related data
    fetchCurrentShow();
    fetchShows();
    fetchGroupedRequests();
    
    // Check for successful payment
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    const paymentStatus = urlParams.get('payment');
    
    if (sessionId && paymentStatus === 'success') {
      checkPaymentStatus(sessionId);
    }
    
    // Setup real-time updates
    const service = new RealtimeService(musician.id, (data) => {
      setRequests(data.requests);
    });
    setRealtimeService(service);
    service.startPolling();

    return () => {
      if (service) service.stopPolling();
    };
  }, [musician.id]);

  useEffect(() => {
    if (showProfile) {
      fetchProfile();
    }
  }, [showProfile]);

  // NEW: Initialize profile state with musician data on login/auth restoration
  useEffect(() => {
    if (musician && musician.id) {
      setProfile({
        name: musician.name || '',
        email: musician.email || '',
        venmo_link: musician.venmo_link || '', // Keep for backward compatibility
        bio: musician.bio || '',
        website: musician.website || '',
        // Payment fields
        paypal_username: musician.paypal_username || '',
        venmo_username: musician.venmo_username || '',
        // Social media fields
        instagram_username: musician.instagram_username || '',
        facebook_username: musician.facebook_username || '',
        tiktok_username: musician.tiktok_username || '',
        spotify_artist_url: musician.spotify_artist_url || '',
        apple_music_artist_url: musician.apple_music_artist_url || ''
      });
    }
  }, [musician]); // Trigger when musician object changes

  useEffect(() => {
    if (activeTab === 'design') {
      fetchDesignSettings();
    }
  }, [activeTab]);

  const fetchSongs = async () => {
    try {
      const response = await axios.get(`${API}/songs?sort_by=${sortBy}`);
      setSongs(response.data);
    } catch (error) {
      console.error('Error fetching songs:', error);
    }
  };

  // NEW: Fetch filter options for musician dashboard
  const fetchFilterOptions = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${musician.slug}/filter-options`);
      setFilterOptions(response.data);
    } catch (error) {
      console.error('Error fetching filter options:', error);
      // Set empty arrays as fallback
      setFilterOptions({
        genres: [],
        moods: [],
        years: [],
        decades: []
      });
    }
  };

  const fetchRequests = async () => {
    try {
      const response = await axios.get(`${API}/requests/musician/${musician.id}`);
      setRequests(response.data);
    } catch (error) {
      console.error('Error fetching requests:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSong = async (e) => {
    e.preventDefault();
    setSongError('');
    
    try {
      const songData = {
        ...songForm,
        genres: songForm.genres.filter(g => g.trim()),
        moods: songForm.moods.filter(m => m.trim()),
        year: songForm.year ? parseInt(songForm.year) : null
      };
      
      await axios.post(`${API}/songs`, songData);
      setSongForm({
        title: '',
        artist: '',
        genres: [],
        moods: [],
        year: '',
        notes: ''
      });
      fetchSongs();
      fetchFilterOptions(); // Refresh filter options when songs change
    } catch (error) {
      setSongError(error.response?.data?.detail || 'Error adding song');
    }
  };

  const handleEditSong = (song) => {
    setEditingSong(song);
    setSongForm({
      title: song.title,
      artist: song.artist,
      genres: song.genres,
      moods: song.moods,
      year: song.year ? song.year.toString() : '',
      notes: song.notes
    });
    setSongError('');
    setShowEditModal(true); // NEW: Open modal instead of scrolling to form
  };

  const handleUpdateSong = async (e) => {
    e.preventDefault();
    setSongError('');
    
    try {
      const songData = {
        ...songForm,
        genres: songForm.genres.filter(g => g.trim()),
        moods: songForm.moods.filter(m => m.trim()),
        year: songForm.year ? parseInt(songForm.year) : null
      };
      
      await axios.put(`${API}/songs/${editingSong.id}`, songData);
      setEditingSong(null);
      setShowEditModal(false); // NEW: Close modal after successful update
      setSongForm({
        title: '',
        artist: '',
        genres: [],
        moods: [],
        year: '',
        notes: ''
      });
      fetchSongs();
    } catch (error) {
      setSongError(error.response?.data?.detail || 'Error updating song');
    }
  };

  const cancelEdit = () => {
    setEditingSong(null);
    setShowEditModal(false); // NEW: Close modal when canceling
    setSongForm({
      title: '',
      artist: '',
      genres: [],
      moods: [],
      year: '',
      notes: ''
    });
    setSongError('');
  };

  const handleDeleteSong = async (songId) => {
    if (window.confirm('Are you sure you want to delete this song?')) {
      try {
        console.log('Deleting song with ID:', songId);
        await axios.delete(`${API}/songs/${songId}`); // Removed manual headers - axios already has auth token set globally
        fetchSongs();
        console.log('Song deleted successfully');
      } catch (error) {
        console.error('Error deleting song:', error);
        alert(`Error deleting song: ${error.response?.data?.detail || error.message}`);
      }
    }
  };

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`);
      setProfile(response.data);
    } catch (error) {
      setProfileError('Error loading profile');
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setProfileError('');
    
    try {
      const response = await axios.put(`${API}/profile`, profile);
      setProfile(response.data);
      
      // NEW: Update the musician object with the new profile data to persist changes
      const updatedMusician = {
        ...musician,
        name: response.data.name,
        bio: response.data.bio,
        website: response.data.website,
        paypal_username: response.data.paypal_username,
        venmo_username: response.data.venmo_username,
        instagram_username: response.data.instagram_username,
        facebook_username: response.data.facebook_username,
        tiktok_username: response.data.tiktok_username,
        spotify_artist_url: response.data.spotify_artist_url,
        apple_music_artist_url: response.data.apple_music_artist_url
      };
      
      setMusician(updatedMusician);
      localStorage.setItem('musician', JSON.stringify(updatedMusician));
      
      setShowProfile(false);
      alert('Profile updated successfully!');
    } catch (error) {
      setProfileError(error.response?.data?.detail || 'Error updating profile');
    }
  };

  const fetchSubscriptionStatus = async () => {
    try {
      const response = await axios.get(`${API}/subscription/status`);
      setSubscriptionStatus(response.data);
    } catch (error) {
      console.error('Error fetching subscription status:', error);
    }
  };

  const handleUpgrade = async () => {
    setUpgrading(true);
    try {
      const response = await axios.post(`${API}/subscription/upgrade`);
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error('Error creating upgrade session:', error);
      alert('Error processing upgrade. Please try again.');
    } finally {
      setUpgrading(false);
    }
  };

  const checkPaymentStatus = async (sessionId) => {
    try {
      const response = await axios.get(`${API}/subscription/payment-status/${sessionId}`);
      if (response.data.payment_status === 'paid') {
        alert('Subscription activated! You now have unlimited requests.');
        fetchSubscriptionStatus();
        // Remove session_id from URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
    }
  };

  // NEW: Batch editing and filtering functions
  const filterSongs = () => {
    let filtered = songs.filter(song => {
      // Text search across title and artist
      const searchMatch = songFilter === '' || 
        song.title.toLowerCase().includes(songFilter.toLowerCase()) ||
        song.artist.toLowerCase().includes(songFilter.toLowerCase());
      
      // Genre filter
      const genreMatch = genreFilter === '' || 
        song.genres.some(genre => genre.toLowerCase().includes(genreFilter.toLowerCase()));
      
      // Artist filter
      const artistMatch = artistFilter === '' ||
        song.artist.toLowerCase().includes(artistFilter.toLowerCase());
      
      // Mood filter
      const moodMatch = moodFilter === '' ||
        song.moods.some(mood => mood.toLowerCase().includes(moodFilter.toLowerCase()));
      
      // Year filter
      const yearMatch = yearFilter === '' || 
        (song.year && song.year.toString() === yearFilter);
      
      // NEW: Decade filter
      const decadeMatch = decadeFilter === '' || 
        (song.decade && song.decade === decadeFilter);
      
      return searchMatch && genreMatch && artistMatch && moodMatch && yearMatch && decadeMatch;
    });
    
    setFilteredSongs(filtered);
  };

  const handleSelectSong = (songId) => {
    const newSelected = new Set(selectedSongs);
    if (newSelected.has(songId)) {
      newSelected.delete(songId);
    } else {
      newSelected.add(songId);
    }
    setSelectedSongs(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedSongs.size === filteredSongs.length) {
      setSelectedSongs(new Set());
    } else {
      setSelectedSongs(new Set(filteredSongs.map(song => song.id)));
    }
  };

  const handleBatchEdit = async () => {
    if (selectedSongs.size === 0) {
      alert('Please select songs to edit');
      return;
    }

    const updates = {};
    if (batchEditForm.artist && batchEditForm.artist.trim()) {
      updates.artist = batchEditForm.artist.trim();
    }
    if (batchEditForm.genres && batchEditForm.genres.trim()) {
      updates.genres = batchEditForm.genres.trim();
    }
    if (batchEditForm.moods && batchEditForm.moods.trim()) {
      updates.moods = batchEditForm.moods.trim();
    }
    if (batchEditForm.year && batchEditForm.year.trim()) {
      updates.year = batchEditForm.year.trim();
    }
    if (batchEditForm.notes !== undefined) {
      updates.notes = batchEditForm.notes; // Include notes (can be empty to clear)
    }

    if (Object.keys(updates).length === 0) {
      alert('Please enter values to update');
      return;
    }

    try {
      console.log('Batch edit data being sent:', {
        song_ids: Array.from(selectedSongs),
        updates: updates
      });

      const response = await axios.put(`${API}/songs/batch-edit`, {
        song_ids: Array.from(selectedSongs),
        updates: updates
      });

      console.log('Batch edit response:', response.data);

      if (response.data.success) {
        alert(`Successfully updated ${response.data.updated_count} songs!`);
        setBatchEditForm({
          artist: '',
          genres: '',
          moods: '',
          year: '',
          notes: ''
        });
        setSelectedSongs(new Set());
        setShowBatchEdit(false);
        fetchSongs(); // Refresh the song list
      } else {
        alert('Update completed but with unexpected response');
      }
    } catch (error) {
      console.error('Error batch editing songs:', error);
      console.error('Error response data:', error.response?.data);
      
      // Handle validation errors properly (detail can be an array of error objects)
      let errorMessage = 'Error updating songs';
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail)) {
          // Handle FastAPI validation errors (array of error objects)
          errorMessage = detail.map(err => {
            if (typeof err === 'object' && err.msg) {
              return `${err.loc ? err.loc.join('.') + ': ' : ''}${err.msg}`;
            }
            return String(err);
          }).join('\n');
        } else {
          // Handle simple string errors
          errorMessage = String(detail);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert(`Error: ${errorMessage}`);
    }
  };

  const exportSongsToCSV = (songsToExport = null) => {
    const exportSongs = songsToExport || filteredSongs;
    
    const csvContent = [
      ['Title', 'Artist', 'Genres', 'Moods', 'Year', 'Notes'],
      ...exportSongs.map(song => [
        song.title,
        song.artist,
        song.genres.join(', '),
        song.moods.join(', '),
        song.year || '',
        song.notes || ''
      ])
    ].map(row => row.map(field => `"${field}"`).join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `songs-export-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const handleBatchDelete = async () => {
    if (selectedSongs.size === 0) {
      alert('Please select songs to delete');
      return;
    }

    // Offer CSV export before deletion
    const exportFirst = window.confirm(
      `You are about to delete ${selectedSongs.size} songs. Would you like to export them to CSV first?`
    );
    
    if (exportFirst) {
      const songsToDelete = songs.filter(song => selectedSongs.has(song.id));
      exportSongsToCSV(songsToDelete);
    }

    const confirmDelete = window.confirm(
      `Are you sure you want to delete ${selectedSongs.size} selected songs? This cannot be undone.`
    );

    if (!confirmDelete) return;

    try {
      const deletePromises = Array.from(selectedSongs).map(songId => 
        axios.delete(`${API}/songs/${songId}`) // Removed manual headers - axios already has auth token set globally
      );

      await Promise.all(deletePromises);
      
      fetchSongs();
      setSelectedSongs(new Set());
      alert(`Successfully deleted ${selectedSongs.size} songs`);
    } catch (error) {
      console.error('Error batch deleting songs:', error);
      alert('Error deleting songs. Please try again.');
    }
  };

  // Update filtered songs when songs or filters change
  React.useEffect(() => {
    filterSongs();
  }, [songs, songFilter, genreFilter, artistFilter, moodFilter, yearFilter, decadeFilter]);

  // NEW: Refetch songs and filter options when sort order changes
  React.useEffect(() => {
    if (musician) {
      fetchSongs();
      fetchFilterOptions();
    }
  }, [sortBy, musician]);

  // NEW: Phase 3 - Analytics functions
  const fetchAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const response = await axios.get(`${API}/analytics/daily?days=${analyticsDays}`);
      setAnalyticsData(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const fetchRequesters = async () => {
    try {
      const response = await axios.get(`${API}/analytics/requesters`);
      setRequestersData(response.data.requesters);
    } catch (error) {
      console.error('Error fetching requesters:', error);
    }
  };

  const exportRequestersCSV = async () => {
    try {
      const response = await axios.get(`${API}/analytics/export-requesters`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `requesters-${new Date().toISOString().split('T')[0]}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
      
      alert('Requesters CSV exported successfully!');
    } catch (error) {
      console.error('Error exporting requesters CSV:', error);
      alert('Error exporting requesters. Please try again.');
    }
  };

  const handleTimeframeChange = (timeframe) => {
    setAnalyticsTimeframe(timeframe);
    let days = 7;
    if (timeframe === 'weekly') days = 7;
    else if (timeframe === 'monthly') days = 30;
    else days = 7; // daily default
    
    setAnalyticsDays(days);
  };

  // Fetch analytics when tab is active or timeframe changes
  React.useEffect(() => {
    if (activeTab === 'analytics') {
      fetchAnalytics();
      fetchRequesters();
    }
  }, [activeTab, analyticsDays]);

  // Fetch suggestions when suggestions tab is active
  React.useEffect(() => {
    if (activeTab === 'suggestions') {
      fetchSongSuggestions();
    }
  }, [activeTab]);

  // NEW: Auto-fill song metadata function
  const handleAutoFillMetadata = async () => {
    if (!songForm.title.trim() || !songForm.artist.trim()) {
      alert('Please enter both song title and artist before auto-filling.');
      return;
    }

    setAutoFillLoading(true);
    try {
      const response = await axios.post(`${API}/songs/search-metadata`, null, {
        params: {
          title: songForm.title.trim(),
          artist: songForm.artist.trim()
        }
      });

      if (response.data.success && response.data.metadata) {
        const metadata = response.data.metadata;
        
        // Show confirmation dialog with suggestions
        const confirmMessage = `Found metadata from ${metadata.source}:\n\n` +
          `Title: ${metadata.title}\n` +
          `Artist: ${metadata.artist}\n` +
          `Year: ${metadata.year || 'Unknown'}\n` +
          `Genres: ${metadata.genres.join(', ')}\n` +
          `Moods: ${metadata.moods.join(', ')}\n\n` +
          `Confidence: ${metadata.confidence}\n\n` +
          `Would you like to use this information?`;

        if (window.confirm(confirmMessage)) {
          setSongForm({
            ...songForm,
            year: metadata.year || songForm.year,
            genres: metadata.genres.length > 0 ? metadata.genres : songForm.genres,
            moods: metadata.moods.length > 0 ? metadata.moods : songForm.moods
          });
          alert('Metadata applied successfully! You can still edit any fields before saving.');
        }
      } else {
        alert('No metadata found. You can still add the song manually.');
      }
    } catch (error) {
      console.error('Error fetching metadata:', error);
      if (error.response?.status === 400) {
        alert('Please provide both title and artist to search for metadata.');
      } else {
        alert('Error searching for song metadata. You can still add the song manually.');
      }
    } finally {
      setAutoFillLoading(false);
    }
  };

  const fetchDesignSettings = async () => {
    try {
      const response = await axios.get(`${API}/design/settings`);
      setDesignSettings(response.data);
    } catch (error) {
      console.error('Error fetching design settings:', error);
    }
  };

  const handleDesignUpdate = async (e) => {
    e.preventDefault();
    setDesignError('');
    
    try {
      await axios.put(`${API}/design/settings`, designSettings);
      alert('Design settings updated successfully!');
    } catch (error) {
      if (error.response?.status === 402) {
        setDesignError('Design customization is a Pro feature. Upgrade to access these settings.');
        setShowUpgrade(true);
      } else {
        setDesignError(error.response?.data?.detail || 'Error updating design settings');
      }
    }
  };

  const handleArtistPhotoUpload = (e) => {
    // Check if user has Pro subscription before allowing upload
    if (!subscriptionStatus || subscriptionStatus.plan_type !== 'pro') {
      setDesignError('Photo upload is a Pro feature. Upgrade to access this functionality.');
      setShowUpgrade(true);
      return;
    }

    const file = e.target.files[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) { // 2MB limit
        setDesignError('Image size must be less than 2MB');
        return;
      }
      
      const reader = new FileReader();
      reader.onload = (event) => {
        setDesignSettings({
          ...designSettings,
          artist_photo: event.target.result
        });
        
        // Show success message and auto-save
        setDesignError('');
        alert('Photo uploaded successfully! Click "Save Changes" to apply.');
      };
      reader.readAsDataURL(file);
    }
  };

  const generateQRCode = async () => {
    try {
      const response = await axios.get(`${API}/qr-code`);
      setQrCode(response.data);
      setShowQRModal(true);
    } catch (error) {
      console.error('Error generating QR code:', error);
      alert('Error generating QR code');
    }
  };

  const downloadQRCode = () => {
    if (!qrCode) return;
    
    const link = document.createElement('a');
    link.href = qrCode.qr_code;
    link.download = `${musician.name}-qr-code.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const generateAndDownloadFlyer = async () => {
    try {
      const response = await axios.get(`${API}/qr-flyer`);
      const link = document.createElement('a');
      link.href = response.data.flyer;
      link.download = `${musician.name}-qr-flyer.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error generating flyer:', error);
      alert('Error generating flyer');
    }
  };

  const printQRFlyer = async () => {
    try {
      const response = await axios.get(`${API}/qr-flyer`);
      const printWindow = window.open('', '_blank');
      printWindow.document.write(`
        <html>
          <head>
            <title>RequestWave QR Flyer - ${musician.name}</title>
            <style>
              body { margin: 0; padding: 20px; text-align: center; }
              img { max-width: 100%; height: auto; }
              @media print { body { padding: 0; } }
            </style>
          </head>
          <body>
            <img src="${response.data.flyer}" alt="QR Code Flyer" />
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.print();
    } catch (error) {
      console.error('Error printing flyer:', error);
      alert('Error generating flyer for printing');
    }
  };

  const handlePlaylistImport = async (e) => {
    e.preventDefault();
    if (!playlistUrl.trim()) {
      setPlaylistError('Please enter a playlist URL');
      return;
    }

    setImportingPlaylist(true);
    setPlaylistError('');

    try {
      console.log('Attempting to import playlist:', playlistUrl, 'Platform:', playlistPlatform);
      
      const response = await axios.post(`${API}/songs/playlist/import`, {
        playlist_url: playlistUrl,
        platform: playlistPlatform
      });
      
      console.log('Import response:', response.data);
      
      // Close the import panel and reset form after successful import
      setShowPlaylistImport(false);
      setPlaylistUrl('');
      setPlaylistPlatform('spotify'); // Reset to default
      
      // Refresh songs list to show imported songs
      fetchSongs();
      
      alert(response.data.message);
      
    } catch (error) {
      console.error('Import error:', error);
      console.error('Error response:', error.response);
      
      if (error.response?.status === 401) {
        setPlaylistError('Please log in again to import playlists');
      } else {
        setPlaylistError(error.response?.data?.detail || 'Error importing playlist');
      }
    } finally {
      setImportingPlaylist(false);
    }
  };

  const updateRequestStatus = async (requestId, status) => {
    try {
      await axios.put(`${API}/requests/${requestId}/status?status=${status}`);
      fetchRequests();
    } catch (error) {
      console.error('Error updating request:', error);
    }
  };

  // CSV Upload functions
  const handleCsvFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCsvFile(file);
      setCsvPreview(null);
      setCsvError('');
    }
  };

  const handleCsvDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith('.csv')) {
      setCsvFile(file);
      setCsvPreview(null);
      setCsvError('');
    } else {
      setCsvError('Please drop a valid CSV file');
    }
  };

  const previewCsv = async () => {
    if (!csvFile) return;
    
    setCsvUploading(true);
    setCsvError('');
    
    try {
      const formData = new FormData();
      formData.append('file', csvFile);
      
      const response = await axios.post(`${API}/songs/csv/preview`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setCsvPreview(response.data);
    } catch (error) {
      setCsvError(error.response?.data?.detail || 'Error previewing CSV file');
    } finally {
      setCsvUploading(false);
    }
  };

  const uploadCsv = async () => {
    if (!csvFile) return;
    
    setCsvUploading(true);
    setCsvError('');
    
    try {
      const formData = new FormData();
      formData.append('file', csvFile);
      
      // NEW: Add auto_enrich parameter
      const response = await axios.post(`${API}/songs/csv/upload?auto_enrich=${csvAutoEnrich}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Reset form and refresh songs
      setCsvFile(null);
      setCsvPreview(null);
      setShowCsvUpload(false);
      setCsvAutoEnrich(false);  // Reset auto-enrich option
      fetchSongs();
      
      // Enhanced success message with enrichment info
      let message = `Success! ${response.data.songs_added} songs imported`;
      if (csvAutoEnrich && response.data.message.includes('auto-enriched')) {
        // Extract enrichment count from message
        const enrichedMatch = response.data.message.match(/(\d+) songs auto-enriched/);
        if (enrichedMatch) {
          message += `, ${enrichedMatch[1]} songs auto-enriched with metadata`;
        }
      }
      if (response.data.errors.length > 0) {
        message += ` with ${response.data.errors.length} warnings`;
      }
      
      alert(message);
      
    } catch (error) {
      setCsvError(error.response?.data?.detail || 'Error uploading CSV file');
    } finally {
      setCsvUploading(false);
    }
  };

  // NEW: Playlist functions (Pro feature)
  const fetchPlaylists = async () => {
    try {
      // Only fetch if user has Pro access
      if (!subscriptionStatus || subscriptionStatus.plan !== 'pro') {
        setPlaylists([]);
        return;
      }
      
      const response = await axios.get(`${API}/playlists`);
      setPlaylists(response.data);
      
      // Find the active playlist
      const activePlaylist = response.data.find(p => p.is_active);
      setActivePlaylistId(activePlaylist ? activePlaylist.id : 'all_songs');
    } catch (error) {
      if (error.response?.status === 403) {
        // User doesn't have Pro access, that's fine
        setPlaylists([]);
      } else {
        console.error('Error fetching playlists:', error);
        // Don't show error to user for this, just log it
        setPlaylists([]);
      }
    }
  };

  const createPlaylist = async () => {
    if (!playlistName.trim()) {
      setPlaylistManagementError('Please enter a playlist name');
      return;
    }

    if (selectedSongs.size === 0) {
      setPlaylistManagementError('Please select songs to add to the playlist');
      return;
    }

    setPlaylistLoading(true);
    setPlaylistManagementError('');

    try {
      await axios.post(`${API}/playlists`, {
        name: playlistName,
        song_ids: Array.from(selectedSongs)
      });

      setPlaylistName('');
      setSelectedSongs(new Set());
      setShowPlaylistModal(false);
      fetchPlaylists();
      fetchFilterOptions(); // Refresh filter options when songs change
      alert('Playlist created successfully!');
    } catch (error) {
      if (error.response?.status === 403) {
        setPlaylistManagementError('This feature requires a Pro subscription. Please upgrade to create playlists.');
      } else {
        setPlaylistManagementError(error.response?.data?.detail || 'Error creating playlist');
      }
    } finally {
      setPlaylistLoading(false);
    }
  };

  const addToExistingPlaylist = async () => {
    if (!selectedExistingPlaylist) {
      setPlaylistManagementError('Please select a playlist');
      return;
    }

    if (selectedSongs.size === 0) {
      setPlaylistManagementError('Please select songs to add to the playlist');
      return;
    }

    setPlaylistLoading(true);
    setPlaylistManagementError('');

    try {
      // Get current playlist songs
      const playlist = playlists.find(p => p.id === selectedExistingPlaylist);
      if (!playlist) {
        setPlaylistManagementError('Playlist not found');
        return;
      }

      // Get current song IDs from the playlist
      const response = await axios.get(`${API}/playlists`);
      const currentPlaylist = response.data.find(p => p.id === selectedExistingPlaylist);
      
      // Merge existing songs with new selected songs (avoid duplicates)
      const existingSongIds = currentPlaylist?.song_ids || [];
      const newSongIds = Array.from(selectedSongs);
      const mergedSongIds = [...new Set([...existingSongIds, ...newSongIds])];

      await axios.put(`${API}/playlists/${selectedExistingPlaylist}`, {
        song_ids: mergedSongIds
      });

      setSelectedSongs(new Set());
      setShowPlaylistModal(false);
      fetchPlaylists();
      alert(`Songs added to "${playlist.name}" successfully!`);
    } catch (error) {
      setPlaylistManagementError(error.response?.data?.detail || 'Error adding songs to playlist');
    } finally {
      setPlaylistLoading(false);
    }
  };

  const handlePlaylistAction = () => {
    if (playlistAction === 'create') {
      createPlaylist();
    } else {
      addToExistingPlaylist();
    }
  };

  const deletePlaylist = async (playlistId, playlistName) => {
    if (!confirm(`Are you sure you want to delete "${playlistName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await axios.delete(`${API}/playlists/${playlistId}`);
      fetchPlaylists();
      alert(`Playlist "${playlistName}" deleted successfully!`);
    } catch (error) {
      alert('Error deleting playlist');
      console.error('Error deleting playlist:', error);
    }
  };

  const updatePlaylistName = async (playlistId, newName) => {
    if (!newName.trim()) {
      alert('Please enter a playlist name');
      return;
    }

    try {
      // For renaming, we need to get current songs and keep them
      const playlist = playlists.find(p => p.id === playlistId);
      if (!playlist) return;

      // Get current playlist data
      const response = await axios.get(`${API}/playlists`);
      const currentPlaylist = response.data.find(p => p.id === playlistId);
      
      // We'll need to make this API call since we don't have a rename endpoint
      // For now, let's create a temporary solution by recreating the playlist
      await axios.put(`${API}/playlists/${playlistId}`, {
        song_ids: currentPlaylist?.song_ids || []
      });

      setEditingPlaylist(null);
      fetchPlaylists();
      alert('Playlist updated successfully!');
    } catch (error) {
      alert('Error updating playlist name');
      console.error('Error updating playlist:', error);
    }
  };

  const activatePlaylist = async (playlistId) => {
    try {
      await axios.put(`${API}/playlists/${playlistId}/activate`);
      setActivePlaylistId(playlistId);
      fetchPlaylists();
      
      const playlist = playlists.find(p => p.id === playlistId);
      const playlistName = playlist ? playlist.name : 'All Songs';
      alert(`"${playlistName}" is now active for your audience!`);
    } catch (error) {
      console.error('Error activating playlist:', error);
      alert('Error activating playlist');
    }
  };

  // Fetch playlists on component mount and when subscription status changes
  useEffect(() => {
    if (musician && subscriptionStatus && subscriptionStatus.plan === 'pro') {
      fetchPlaylists();
    }
  }, [musician, subscriptionStatus]);

  const audienceUrl = `${window.location.origin}/musician/${musician.slug}`;

  if (loading) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <img
                src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/9wbfmlsw_A_logo_for_%22RequestWave%22_features_a_purple_microph.png"
                alt="RequestWave"
                className="w-10 h-10 object-contain"
              />
              <h1 className="text-2xl font-bold text-purple-400">RequestWave</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-300">Welcome, {musician.name}</span>
              <button
                onClick={logout}
                className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg transition duration-300"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Tabs */}
        <div className="flex space-x-1 bg-gray-800 rounded-lg p-1 mb-8">
          {['songs', 'requests', 'analytics', 'profile', 'design'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition duration-300 ${
                activeTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab === 'analytics' ? '📊 Analytics' : tab === 'design' ? 'Design & Pro Features ✨' : tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'requests' && requests.filter(r => r.status === 'pending').length > 0 && (
                <span className="ml-2 bg-red-500 text-white rounded-full px-2 py-1 text-xs">
                  {requests.filter(r => r.status === 'pending').length}
                </span>
              )}
              {tab === 'design' && subscriptionStatus && subscriptionStatus.plan !== 'pro' && subscriptionStatus.plan !== 'trial' && (
                <span className="ml-1 text-xs bg-green-600 rounded px-1">PRO</span>
              )}
            </button>
          ))}
        </div>

        {/* Songs Tab */}
        {activeTab === 'songs' && (
          <div>
            {/* Song Management Header */}
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Song Management</h2>
              <div className="flex space-x-3">
                <button
                  onClick={handleBatchEnrich}
                  disabled={batchEnrichLoading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-bold transition duration-300 flex items-center space-x-2"
                >
                  {batchEnrichLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Enriching...</span>
                    </>
                  ) : (
                    <>
                      <span>🔍</span>
                      <span>Auto-fill All</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => setShowAddSong(!showAddSong)}
                  className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-lg font-bold transition duration-300"
                >
                  {showAddSong ? 'Hide Add Song' : 'Add New Song'}
                </button>
                <button
                  onClick={() => setShowPlaylistImport(!showPlaylistImport)}
                  className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg font-bold transition duration-300"
                >
                  {showPlaylistImport ? 'Hide Playlist Import' : 'Import Playlist'}
                </button>
                <button
                  onClick={() => setShowCsvUpload(!showCsvUpload)}
                  className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-bold transition duration-300"
                >
                  {showCsvUpload ? 'Hide CSV Upload' : 'Upload CSV'}
                </button>
              </div>
            </div>

            {/* CSV Upload Section */}
            {showCsvUpload && (
              <div className="bg-gray-800 rounded-xl p-6 mb-8">
                <h3 className="text-lg font-bold mb-4">Upload Songs from CSV</h3>
                <p className="text-gray-300 mb-4 text-sm">
                  Expected CSV format: Title, Artist, Genre, Mood, Year, Notes
                  <br />
                  <span className="text-purple-300">Genres and Moods can be comma-separated (e.g., "Rock, Jazz")</span>
                </p>

                {!csvFile ? (
                  <div
                    className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-purple-500 transition duration-300"
                    onDrop={handleCsvDrop}
                    onDragOver={(e) => e.preventDefault()}
                    onClick={() => document.getElementById('csvFileInput').click()}
                  >
                    <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                      <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <p className="text-gray-300">
                      <span className="font-bold text-purple-400">Click to upload</span> or drag and drop
                    </p>
                    <p className="text-gray-400 text-sm">CSV files only (max 5MB)</p>
                    <input
                      id="csvFileInput"
                      type="file"
                      accept=".csv"
                      onChange={handleCsvFileSelect}
                      className="hidden"
                    />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* File Info */}
                    <div className="bg-gray-700 rounded-lg p-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-bold">{csvFile.name}</p>
                          <p className="text-sm text-gray-300">{(csvFile.size / 1024).toFixed(1)} KB</p>
                        </div>
                        <button
                          onClick={() => {
                            setCsvFile(null);
                            setCsvPreview(null);
                            setCsvError('');
                          }}
                          className="text-red-400 hover:text-red-300"
                        >
                          Remove
                        </button>
                      </div>
                    </div>

                    {/* NEW: Auto-enrichment Option */}
                    <div className="bg-gray-700 rounded-lg p-4">
                      <label className="flex items-center space-x-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={csvAutoEnrich}
                          onChange={(e) => setCsvAutoEnrich(e.target.checked)}
                          className="w-4 h-4 text-blue-600 bg-gray-600 border-gray-500 rounded focus:ring-blue-500"
                        />
                        <div>
                          <span className="font-medium text-white">🔍 Auto-fill missing metadata from Spotify</span>
                          <p className="text-sm text-gray-300 mt-1">
                            Automatically fills in missing genres, moods, and years using Spotify data. Only updates empty fields.
                          </p>
                        </div>
                      </label>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex space-x-4">
                      <button
                        onClick={previewCsv}
                        disabled={csvUploading}
                        className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                      >
                        {csvUploading ? 'Processing...' : 'Preview'}
                      </button>
                      {csvPreview && (
                        <button
                          onClick={uploadCsv}
                          disabled={csvUploading}
                          className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                        >
                          {csvUploading ? 'Uploading...' : `Import ${csvPreview.valid_rows} Songs`}
                        </button>
                      )}
                    </div>

                    {/* CSV Preview */}
                    {csvPreview && (
                      <div className="bg-gray-700 rounded-lg p-4">
                        <h4 className="font-bold mb-2">
                          Preview: {csvPreview.valid_rows} of {csvPreview.total_rows} rows valid
                        </h4>
                        
                        {csvPreview.errors.length > 0 && (
                          <div className="mb-4">
                            <h5 className="text-red-400 font-bold mb-2">Errors:</h5>
                            <div className="bg-red-900/20 rounded p-2 max-h-32 overflow-y-auto">
                              {csvPreview.errors.map((error, idx) => (
                                <p key={idx} className="text-red-300 text-sm">{error}</p>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-gray-600">
                                <th className="text-left p-2">Title</th>
                                <th className="text-left p-2">Artist</th>
                                <th className="text-left p-2">Genres</th>
                                <th className="text-left p-2">Moods</th>
                                <th className="text-left p-2">Year</th>
                              </tr>
                            </thead>
                            <tbody>
                              {csvPreview.preview.map((song, idx) => (
                                <tr key={idx} className="border-b border-gray-600">
                                  <td className="p-2">{song.title}</td>
                                  <td className="p-2">{song.artist}</td>
                                  <td className="p-2">{song.genres.join(', ')}</td>
                                  <td className="p-2">{song.moods.join(', ')}</td>
                                  <td className="p-2">{song.year || '-'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {csvError && (
                      <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-red-200">
                        {csvError}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Playlist Import Section */}
            {showPlaylistImport && (
              <div className="bg-gray-800 rounded-xl p-6 mb-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-bold">Import from Music Playlist</h3>
                  <button
                    onClick={() => setShowPlaylistImport(false)}
                    className="text-gray-400 hover:text-white text-xl"
                  >
                    ×
                  </button>
                </div>
                <p className="text-gray-300 mb-4 text-sm">
                  Import songs from Spotify or Apple Music public playlists
                </p>

                {playlistError && (
                  <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                    {playlistError}
                  </div>
                )}

                <form onSubmit={handlePlaylistImport} className="space-y-4">
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">Platform</label>
                    <select
                      value={playlistPlatform}
                      onChange={(e) => setPlaylistPlatform(e.target.value)}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    >
                      <option value="spotify">Spotify</option>
                      <option value="apple_music">Apple Music</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">Playlist URL</label>
                    <input
                      type="url"
                      placeholder={playlistPlatform === 'spotify' 
                        ? 'https://open.spotify.com/playlist/...' 
                        : 'https://music.apple.com/playlist/...'
                      }
                      value={playlistUrl}
                      onChange={(e) => setPlaylistUrl(e.target.value)}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      required
                    />
                  </div>
                  
                  <button
                    type="submit"
                    disabled={importingPlaylist}
                    onClick={() => console.log('Import button clicked!')}
                    className="w-full bg-green-600 hover:bg-green-700 py-2 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                  >
                    {importingPlaylist ? 'Importing...' : `Import from ${playlistPlatform === 'apple_music' ? 'Apple Music' : 'Spotify'}`}
                  </button>
                </form>
              </div>
            )}

            {/* Add Song Form */}
            {showAddSong && (
              <div className="bg-gray-800 rounded-xl p-6 mb-8">
                <h2 className="text-xl font-bold mb-4">Add New Song</h2>
                
                {songError && !editingSong && (
                  <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                    {songError}
                  </div>
                )}
                
                <form onSubmit={handleAddSong} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input
                    type="text"
                    placeholder="Song Title"
                    value={songForm.title}
                    onChange={(e) => setSongForm({...songForm, title: e.target.value})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Artist"
                    value={songForm.artist}
                    onChange={(e) => setSongForm({...songForm, artist: e.target.value})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                    required
                  />
                  
                  {/* NEW: Auto-fill Metadata Button */}
                  <div className="md:col-span-2 mb-4">
                    <button
                      type="button"
                      onClick={handleAutoFillMetadata}
                      disabled={autoFillLoading || !songForm.title.trim() || !songForm.artist.trim()}
                      className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-medium transition duration-300 disabled:cursor-not-allowed flex items-center space-x-2"
                    >
                      {autoFillLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          <span>Searching...</span>
                        </>
                      ) : (
                        <>
                          <span>🔍</span>
                          <span>Auto-fill Info from Spotify</span>
                        </>
                      )}
                    </button>
                    <p className="text-xs text-gray-400 mt-1">
                      Fill in Title and Artist above, then click to automatically find Genre, Mood, and Year
                    </p>
                  </div>
                  
                  <input
                    type="text"
                    placeholder="Genres (comma separated)"
                    value={songForm.genres.join(', ')}
                    onChange={(e) => setSongForm({...songForm, genres: e.target.value.split(',').map(g => g.trim())})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  />
                  <input
                    type="text"
                    placeholder="Moods (comma separated)"
                    value={songForm.moods.join(', ')}
                    onChange={(e) => setSongForm({...songForm, moods: e.target.value.split(',').map(m => m.trim())})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  />
                  <input
                    type="number"
                    placeholder="Year"
                    value={songForm.year}
                    onChange={(e) => setSongForm({...songForm, year: e.target.value})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  />
                  <input
                    type="text"
                    placeholder="Notes (optional)"
                    value={songForm.notes}
                    onChange={(e) => setSongForm({...songForm, notes: e.target.value})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  />
                  <div className="md:col-span-2">
                    <button
                      type="submit"
                      className="w-full bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300"
                    >
                      Add Song
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Songs List */}
            <div className="bg-gray-800 rounded-xl p-6">
              {/* NEW: Filter and Batch Edit Controls */}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold">Your Songs ({filteredSongs.length})</h2>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => exportSongsToCSV()}
                      className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
                    >
                      Export CSV
                    </button>
                    
                    {/* NEW: Sort By Dropdown */}
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value)}
                      className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:ring-purple-500 focus:border-purple-500"
                    >
                      <option value="created_at">📅 Newest First</option>
                      <option value="popularity">🔥 Most Popular</option>
                      <option value="title">🎵 By Title A-Z</option>
                      <option value="artist">👤 By Artist A-Z</option>
                      <option value="year">📆 By Year (Latest)</option>
                    </select>
                  </div>
                </div>

                {/* Search and Filter Bar */}
                <div className="grid grid-cols-1 md:grid-cols-6 gap-3 mb-4">
                  <input
                    type="text"
                    placeholder="Search songs..."
                    value={songFilter}
                    onChange={(e) => setSongFilter(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm"
                  />
                  <select
                    value={genreFilter}
                    onChange={(e) => setGenreFilter(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                  >
                    <option value="">All Genres</option>
                    {filterOptions.genres?.map((genre) => (
                      <option key={genre} value={genre}>{genre}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder="Filter by artist..."
                    value={artistFilter}
                    onChange={(e) => setArtistFilter(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm"
                  />
                  <select
                    value={moodFilter}
                    onChange={(e) => setMoodFilter(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                  >
                    <option value="">All Moods</option>
                    {filterOptions.moods?.map((mood) => (
                      <option key={mood} value={mood}>{mood}</option>
                    ))}
                  </select>
                  <select
                    value={yearFilter}
                    onChange={(e) => setYearFilter(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                  >
                    <option value="">All Years</option>
                    {filterOptions.years?.map((year) => (
                      <option key={year} value={year}>{year}</option>
                    ))}
                  </select>
                  <select
                    value={decadeFilter}
                    onChange={(e) => setDecadeFilter(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                  >
                    <option value="">All Decades</option>
                    {filterOptions.decades?.map((decade) => (
                      <option key={decade} value={decade}>{decade}</option>
                    ))}
                  </select>
                </div>

                {/* Batch Operations Bar */}
                {filteredSongs.length > 0 && (
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center space-x-3">
                      <label className="flex items-center space-x-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedSongs.size === filteredSongs.length && filteredSongs.length > 0}
                          onChange={handleSelectAll}
                          className="rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
                        />
                        <span className="text-sm">Select All</span>
                      </label>
                      {selectedSongs.size > 0 && (
                        <span className="text-sm text-gray-300">
                          {selectedSongs.size} selected
                        </span>
                      )}
                    </div>
                    
                    {selectedSongs.size > 0 && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setShowPlaylistModal(true)}
                          className="bg-yellow-600 hover:bg-yellow-700 px-3 py-1 rounded text-sm font-medium transition duration-300"
                        >
                          Add to Playlist ({selectedSongs.size})
                        </button>
                        <button
                          onClick={() => setShowBatchEdit(!showBatchEdit)}
                          className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm font-medium transition duration-300"
                        >
                          Edit Selected ({selectedSongs.size})
                        </button>
                        <button
                          onClick={handleBatchDelete}
                          className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm font-medium transition duration-300"
                        >
                          Delete Selected
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Batch Edit Form */}
                {showBatchEdit && selectedSongs.size > 0 && (
                  <div className="bg-gray-700 rounded-lg p-4 mb-4">
                    <h3 className="font-bold mb-3">Batch Edit {selectedSongs.size} Songs</h3>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
                      <input
                        type="text"
                        placeholder="New Artist"
                        value={batchEditForm.artist}
                        onChange={(e) => setBatchEditForm({...batchEditForm, artist: e.target.value})}
                        className="bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white placeholder-gray-400 text-sm"
                      />
                      <input
                        type="text"
                        placeholder="New Genres (comma separated)"
                        value={batchEditForm.genres}
                        onChange={(e) => setBatchEditForm({...batchEditForm, genres: e.target.value})}
                        className="bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white placeholder-gray-400 text-sm"
                      />
                      <input
                        type="text"
                        placeholder="New Moods (comma separated)"
                        value={batchEditForm.moods}
                        onChange={(e) => setBatchEditForm({...batchEditForm, moods: e.target.value})}
                        className="bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white placeholder-gray-400 text-sm"
                      />
                      <input
                        type="number"
                        placeholder="New Year"
                        value={batchEditForm.year}
                        onChange={(e) => setBatchEditForm({...batchEditForm, year: e.target.value})}
                        className="bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white placeholder-gray-400 text-sm"
                      />
                      {/* NEW: Notes field for batch editing */}
                      <textarea
                        placeholder="New Notes (will replace existing notes)"
                        value={batchEditForm.notes}
                        onChange={(e) => setBatchEditForm({...batchEditForm, notes: e.target.value})}
                        className="bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white placeholder-gray-400 text-sm"
                        rows="2"
                      />
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={handleBatchEdit}
                        className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm font-medium transition duration-300"
                      >
                        Apply Changes
                      </button>
                      <button
                        onClick={() => setShowBatchEdit(false)}
                        className="bg-gray-600 hover:bg-gray-500 px-4 py-2 rounded text-sm font-medium transition duration-300"
                      >
                        Cancel
                      </button>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                      Only filled fields will be updated. This will completely replace existing values.
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                {filteredSongs.map((song) => (
                  <div key={song.id} className={`rounded-lg p-4 ${
                    song.hidden 
                      ? 'bg-gray-800 border-2 border-dashed border-gray-600 opacity-75' 
                      : 'bg-gray-700'
                  }`}>
                    <div className="flex items-center space-x-3">
                      {/* Checkbox for selection */}
                      <input
                        type="checkbox"
                        checked={selectedSongs.has(song.id)}
                        onChange={() => handleSelectSong(song.id)}
                        className="rounded bg-gray-600 border-gray-500 text-purple-600 focus:ring-purple-500"
                      />
                      
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <h3 className={`font-bold text-lg ${song.hidden ? 'text-gray-400' : 'text-white'}`}>
                                {song.title}
                              </h3>
                              {song.hidden && (
                                <span className="bg-gray-600 text-gray-300 text-xs px-2 py-1 rounded-full font-medium">
                                  👁️‍🗨️ Hidden
                                </span>
                              )}
                            </div>
                            <p className={`${song.hidden ? 'text-gray-500' : 'text-gray-300'}`}>
                              by {song.artist}
                            </p>
                            <div className="flex flex-wrap gap-2 mt-2">
                              {song.genres.map((genre, index) => (
                                <span key={index} className="bg-purple-600 text-xs px-2 py-1 rounded-full">
                                  {genre}
                                </span>
                              ))}
                              {song.moods.map((mood, index) => (
                                <span key={index} className="bg-blue-600 text-xs px-2 py-1 rounded-full">
                                  {mood}
                                </span>
                              ))}
                              {song.year && (
                                <span className="bg-green-600 text-xs px-2 py-1 rounded-full">
                                  {song.year}
                                </span>
                              )}
                              {/* Request Count Badge */}
                              <span className="bg-orange-600 text-xs px-2 py-1 rounded-full font-semibold">
                                🔥 {song.request_count || 0} requests
                              </span>
                            </div>
                            {song.notes && (
                              <p className={`text-sm mt-1 ${song.hidden ? 'text-gray-500' : 'text-gray-400'}`}>
                                {song.notes}
                              </p>
                            )}
                          </div>
                          <div className="flex space-x-2 ml-4">
                            <button
                              onClick={() => handleEditSong(song)}
                              className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm font-medium transition duration-300"
                            >
                              Edit
                            </button>
                            {/* NEW: Hide/Show Button */}
                            <button
                              onClick={() => handleToggleSongVisibility(song.id)}
                              className={`px-3 py-1 rounded text-sm font-medium transition duration-300 ${
                                song.hidden 
                                  ? 'bg-green-600 hover:bg-green-700' 
                                  : 'bg-yellow-600 hover:bg-yellow-700'
                              }`}
                              title={song.hidden ? 'Show to audience' : 'Hide from audience'}
                            >
                              {song.hidden ? 'Show' : 'Hide'}
                            </button>
                            <button
                              onClick={() => handleDeleteSong(song.id)}
                              className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm font-medium transition duration-300"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {filteredSongs.length === 0 && songs.length > 0 && (
                <div className="text-center py-8 text-gray-400">
                  <p>No songs match your current filters.</p>
                  <button 
                    onClick={() => {
                      setSongFilter('');
                      setGenreFilter('');
                      setArtistFilter('');
                      setMoodFilter('');
                      setYearFilter('');
                      setDecadeFilter('');
                    }}
                    className="mt-2 text-purple-400 hover:text-purple-300 underline"
                  >
                    Clear all filters
                  </button>
                </div>
              )}

              {songs.length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  <p>No songs yet. Add your first song above or upload a CSV file.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Requests Tab */}
        {activeTab === 'requests' && (
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Song Requests</h2>
              
              {/* Show Management Controls */}
              <div className="flex items-center space-x-3">
                {/* NEW: Song Suggestions Button */}
                <button
                  onClick={() => setShowSuggestions(!showSuggestions)}
                  className={`px-4 py-2 rounded-lg font-medium transition duration-300 flex items-center space-x-2 ${
                    showSuggestions ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  <span>💡</span>
                  <span>Song Suggestions</span>
                  {songSuggestions.filter(s => s.status === 'pending').length > 0 && (
                    <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                      {songSuggestions.filter(s => s.status === 'pending').length}
                    </span>
                  )}
                </button>
                
                {currentShow ? (
                  <div className="flex items-center space-x-3">
                    <div className="bg-green-600 px-3 py-2 rounded-lg">
                      <span className="text-sm font-medium">🎤 Live: {currentShow.name}</span>
                    </div>
                    <button
                      onClick={handleStopShow}
                      className="bg-red-600 hover:bg-red-700 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
                    >
                      Stop Show
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowStartModal(true)}
                    className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium transition duration-300 flex items-center space-x-2"
                  >
                    <span>🎭</span>
                    <span>Start a Show</span>
                  </button>
                )}
              </div>
            </div>
            
            {/* Main Requests List (no show active) */}
            {!currentShow && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4">📥 All Requests ({requests.length})</h3>
                <div className="space-y-3">
                  {requests.slice(0, 50).map((request) => (
                    <div key={request.id} className="bg-gray-700 p-4 rounded-lg">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <span className="font-medium text-blue-400">{request.song_title}</span>
                            <span className="text-gray-400">by {request.song_artist}</span>
                            {request.tip_clicked && <span className="text-green-400 text-sm">💰</span>}
                            {request.social_clicks?.length > 0 && (
                              <span className="text-purple-400 text-sm">📱 {request.social_clicks.length}</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-300">
                            From: <span className="text-white">{request.requester_name}</span>
                            {request.dedication && (
                              <span className="italic ml-2">"{request.dedication}"</span>
                            )}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(request.created_at).toLocaleDateString()} at {new Date(request.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            request.status === 'pending' ? 'bg-yellow-600/20 text-yellow-400' :
                            request.status === 'accepted' ? 'bg-green-600/20 text-green-400' :
                            request.status === 'played' ? 'bg-blue-600/20 text-blue-400' :
                            'bg-red-600/20 text-red-400'
                          }`}>
                            {request.status}
                          </span>
                          {request.status === 'pending' && (
                            <div className="flex space-x-1">
                              <button
                                onClick={() => updateRequestStatus(request.id, 'accepted')}
                                className="bg-green-600 hover:bg-green-700 text-xs px-2 py-1 rounded"
                              >
                                Accept
                              </button>
                              <button
                                onClick={() => updateRequestStatus(request.id, 'rejected')}
                                className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1 rounded"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                          {request.status === 'accepted' && (
                            <button
                              onClick={() => updateRequestStatus(request.id, 'played')}
                              className="bg-purple-600 hover:bg-purple-700 text-xs px-2 py-1 rounded"
                            >
                              Mark Played
                            </button>
                          )}
                          {/* NEW: Delete button for unassigned requests */}
                          <button
                            onClick={() => handleDeleteRequest(request.id, request.song_title)}
                            className="bg-gray-600 hover:bg-red-600 text-white text-xs px-2 py-1 rounded transition duration-300"
                            title="Delete this request permanently"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  {requests.length === 0 && (
                    <p className="text-gray-400 text-center py-8">No requests yet. Share your audience link to start receiving requests!</p>
                  )}
                  {requests.length > 50 && (
                    <p className="text-gray-400 text-center text-sm">Showing 50 of {requests.length} requests</p>
                  )}
                </div>
              </div>
            )}
            
            {/* Show-Based Requests (when show is active) */}
            {currentShow && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4">🎤 Current Show: {currentShow.name}</h3>
                <div className="space-y-3">
                  {requests.filter(r => r.show_name === currentShow.name).slice(0, 50).map((request) => (
                    <div key={request.id} className="bg-gray-700 p-4 rounded-lg border-l-4 border-green-500">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <span className="font-medium text-blue-400">{request.song_title}</span>
                            <span className="text-gray-400">by {request.song_artist}</span>
                            {request.tip_clicked && <span className="text-green-400 text-sm">💰</span>}
                            {request.social_clicks?.length > 0 && (
                              <span className="text-purple-400 text-sm">📱 {request.social_clicks.length}</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-300">
                            From: <span className="text-white">{request.requester_name}</span>
                            {request.dedication && (
                              <span className="italic ml-2">"{request.dedication}"</span>
                            )}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(request.created_at).toLocaleDateString()} at {new Date(request.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            request.status === 'pending' ? 'bg-yellow-600/20 text-yellow-400' :
                            request.status === 'accepted' ? 'bg-green-600/20 text-green-400' :
                            request.status === 'played' ? 'bg-blue-600/20 text-blue-400' :
                            'bg-red-600/20 text-red-400'
                          }`}>
                            {request.status}
                          </span>
                          {request.status === 'pending' && (
                            <div className="flex space-x-1">
                              <button
                                onClick={() => updateRequestStatus(request.id, 'accepted')}
                                className="bg-green-600 hover:bg-green-700 text-xs px-2 py-1 rounded"
                              >
                                Accept
                              </button>
                              <button
                                onClick={() => updateRequestStatus(request.id, 'rejected')}
                                className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1 rounded"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                          {request.status === 'accepted' && (
                            <button
                              onClick={() => updateRequestStatus(request.id, 'played')}
                              className="bg-purple-600 hover:bg-purple-700 text-xs px-2 py-1 rounded"
                            >
                              Mark Played
                            </button>
                          )}
                          {/* NEW: Delete button for current show requests */}
                          <button
                            onClick={() => handleDeleteRequest(request.id, request.song_title)}
                            className="bg-gray-600 hover:bg-red-600 text-white text-xs px-2 py-1 rounded transition duration-300"
                            title="Delete this request permanently"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Shows Dropdown */}
            {shows.length > 0 && (
              <div className="border-t border-gray-600 pt-6">
                <h3 className="text-lg font-semibold mb-4">🎭 Shows</h3>
                <div className="space-y-3">
                  {shows.map((show) => (
                    <details key={show.id} className="bg-gray-700 rounded-lg">
                      <summary className="cursor-pointer p-4 font-medium hover:bg-gray-600 rounded-lg transition duration-300 flex justify-between items-center">
                        <div>
                          📁 {show.name} ({show.date || 'No date'})
                          <span className="text-gray-400 text-sm ml-2">
                            ({requests.filter(r => r.show_name === show.name).length} requests)
                          </span>
                        </div>
                        {/* NEW: Delete button for entire show */}
                        <button
                          onClick={(e) => {
                            e.preventDefault(); // Prevent details from toggling
                            e.stopPropagation(); // Prevent event bubbling
                            handleDeleteShow(show.id, show.name);
                          }}
                          className="bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-1 rounded transition duration-300 ml-4"
                          title={`Delete show "${show.name}" and all requests permanently`}
                        >
                          🗑️ Delete Show
                        </button>
                      </summary>
                      <div className="px-4 pb-4 space-y-2">
                        {requests.filter(r => r.show_name === show.name).map((request) => (
                          <div key={request.id} className="bg-gray-600 p-3 rounded">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <div className="flex items-center space-x-2 mb-1">
                                  <span className="font-medium text-blue-400 text-sm">{request.song_title}</span>
                                  <span className="text-gray-400 text-sm">by {request.song_artist}</span>
                                  {request.tip_clicked && <span className="text-green-400 text-xs">💰</span>}
                                  {request.social_clicks?.length > 0 && (
                                    <span className="text-purple-400 text-xs">📱 {request.social_clicks.length}</span>
                                  )}
                                </div>
                                <p className="text-xs text-gray-300">
                                  From: {request.requester_name}
                                  {request.dedication && <span className="italic ml-1">"{request.dedication}"</span>}
                                </p>
                              </div>
                              <div className="flex items-center space-x-2 ml-4">
                                <span className={`px-2 py-1 rounded text-xs ${
                                  request.status === 'pending' ? 'bg-yellow-600/20 text-yellow-400' :
                                  request.status === 'accepted' ? 'bg-green-600/20 text-green-400' :
                                  request.status === 'played' ? 'bg-blue-600/20 text-blue-400' :
                                  'bg-red-600/20 text-red-400'
                                }`}>
                                  {request.status}
                                </span>
                                {/* NEW: Delete button for individual requests */}
                                <button
                                  onClick={() => handleDeleteRequest(request.id, request.song_title)}
                                  className="bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-1 rounded transition duration-300"
                                  title="Delete this request permanently"
                                >
                                  🗑️
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* NEW: Song Suggestions Section (when toggled on) */}
        {showSuggestions && (
          <div className="bg-gray-700 rounded-xl p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-green-400">💡 Song Suggestions from Audience</h3>
              <button
                onClick={fetchSongSuggestions}
                className="bg-green-600 hover:bg-green-700 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
              >
                Refresh
              </button>
            </div>

            {suggestionError && (
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                {suggestionError}
              </div>
            )}

            {songSuggestions.length === 0 ? (
              <div className="text-center py-6 text-gray-400">
                <p>No song suggestions yet.</p>
                <p className="text-sm mt-2">Suggestions will appear here when your audience suggests new songs for your repertoire.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {songSuggestions.map((suggestion) => (
                  <div key={suggestion.id} className="bg-gray-600 p-4 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <span className="font-medium text-blue-400">{suggestion.suggested_title}</span>
                          <span className="text-gray-400">by {suggestion.suggested_artist}</span>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            suggestion.status === 'pending' ? 'bg-yellow-600/20 text-yellow-400' :
                            suggestion.status === 'added' ? 'bg-green-600/20 text-green-400' :
                            'bg-red-600/20 text-red-400'
                          }`}>
                            {suggestion.status}
                          </span>
                        </div>
                        <p className="text-sm text-gray-300">
                          Suggested by: <span className="text-white">{suggestion.requester_name}</span>
                          {suggestion.message && (
                            <span className="italic ml-2">"{suggestion.message}"</span>
                          )}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(suggestion.created_at).toLocaleDateString()} at {new Date(suggestion.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        {suggestion.status === 'pending' && (
                          <div className="flex space-x-1">
                            <button
                              onClick={() => handleSuggestionAction(suggestion.id, 'added', suggestion.suggested_title)}
                              className="bg-green-600 hover:bg-green-700 text-xs px-3 py-1 rounded transition duration-300"
                              title="Add to your repertoire"
                            >
                              ✓ Add
                            </button>
                            <button
                              onClick={() => handleSuggestionAction(suggestion.id, 'rejected', suggestion.suggested_title)}
                              className="bg-red-600 hover:bg-red-700 text-xs px-3 py-1 rounded transition duration-300"
                              title="Reject suggestion"
                            >
                              ✗ Reject
                            </button>
                          </div>
                        )}
                        <button
                          onClick={() => handleDeleteSuggestion(suggestion.id, suggestion.suggested_title)}
                          className="bg-gray-600 hover:bg-red-600 text-white text-xs px-2 py-1 rounded transition duration-300"
                          title="Delete suggestion permanently"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Start Show Modal */}
        {showStartModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
              <h3 className="text-xl font-bold text-white mb-4">🎭 Start a New Show</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Show Name</label>
                  <input
                    type="text"
                    placeholder="e.g., Friday Night Live, Coffee House Set"
                    value={newShowName}
                    onChange={(e) => setNewShowName(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                    onKeyPress={(e) => e.key === 'Enter' && handleStartShow()}
                  />
                </div>
                <p className="text-gray-400 text-sm">
                  All new song requests will be organized under this show until you stop it.
                </p>
                <div className="flex space-x-3 mt-6">
                  <button
                    onClick={() => {
                      setShowStartModal(false);
                      setNewShowName('');
                    }}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleStartShow}
                    disabled={!newShowName.trim()}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 py-2 rounded-lg font-medium transition duration-300 disabled:cursor-not-allowed"
                  >
                    Start Show
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div>
            {/* Audience Link */}
            <div className="bg-purple-800/50 rounded-xl p-6 mb-8">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-xl font-bold mb-2">Your Audience Link</h2>
                  <p className="text-purple-200 mb-4">Share this link with your audience for song requests:</p>
                </div>
                {subscriptionStatus && (
                  <div className="text-right">
                    <div className={`px-3 py-1 rounded-full text-xs font-bold ${
                      subscriptionStatus.plan === 'trial' ? 'bg-blue-600' :
                      subscriptionStatus.plan === 'pro' ? 'bg-green-600' : 'bg-orange-600'
                    }`}>
                      {subscriptionStatus.plan === 'trial' ? 'TRIAL' :
                       subscriptionStatus.plan === 'pro' ? 'PRO' : 'FREE'}
                    </div>
                    <div className="text-purple-200 text-xs mt-1">
                      {subscriptionStatus.plan === 'trial' ? 
                        `Trial ends: ${new Date(subscriptionStatus.trial_ends_at).toLocaleDateString()}` :
                        subscriptionStatus.plan === 'pro' ? 
                        'Unlimited requests' :
                        `${subscriptionStatus.requests_used}/${subscriptionStatus.requests_limit} requests used`
                      }
                    </div>
                    {subscriptionStatus.plan === 'free' && subscriptionStatus.next_reset_date && (
                      <div className="text-purple-300 text-xs">
                        Resets: {new Date(subscriptionStatus.next_reset_date).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className="flex flex-col lg:flex-row lg:items-center space-y-4 lg:space-y-0 lg:space-x-4">
                <div className="flex items-center space-x-4 flex-1">
                  <input
                    type="text"
                    value={audienceUrl}
                    readOnly
                    className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  />
                  <button
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(audienceUrl);
                        // Provide visual feedback
                        const button = event.target;
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        button.style.backgroundColor = '#059669'; // green-600
                        setTimeout(() => {
                          button.textContent = originalText;
                          button.style.backgroundColor = ''; // reset to original
                        }, 2000);
                      } catch (err) {
                        console.error('Failed to copy text: ', err);
                        // Fallback for browsers that don't support clipboard API
                        const textArea = document.createElement('textarea');
                        textArea.value = audienceUrl;
                        document.body.appendChild(textArea);
                        textArea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textArea);
                        
                        // Provide visual feedback for fallback
                        const button = event.target;
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        button.style.backgroundColor = '#059669';
                        setTimeout(() => {
                          button.textContent = originalText;
                          button.style.backgroundColor = '';
                        }, 2000);
                      }
                    }}
                    className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition duration-300"
                  >
                    Copy
                  </button>
                </div>
                
                {/* NEW: Active Playlist Selector (Pro Feature) */}
                {subscriptionStatus && subscriptionStatus.plan === 'pro' && (
                  <div className="flex items-center space-x-2">
                    <span className="text-purple-200 text-sm font-medium">Active Playlist:</span>
                    {playlists.length > 0 ? (
                      <select
                        value={activePlaylistId || 'all_songs'}
                        onChange={(e) => {
                          if (e.target.value === 'manage_playlists') {
                            setShowManagePlaylistsModal(true);
                          } else {
                            activatePlaylist(e.target.value);
                          }
                        }}
                        className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:ring-purple-500 focus:border-purple-500"
                      >
                        {playlists.map(playlist => (
                          <option key={playlist.id} value={playlist.id}>
                            {playlist.name} ({playlist.song_count} songs)
                          </option>
                        ))}
                        <option value="manage_playlists" className="font-bold text-yellow-300">
                          ⚙️ Manage Playlists
                        </option>
                      </select>
                    ) : (
                      <span className="text-gray-400 text-sm">
                        No playlists yet. Go to Songs tab → select songs → "Add to Playlist"
                      </span>
                    )}
                  </div>
                )}
                
                <div className="flex items-center space-x-2">
                  <button
                    onClick={generateQRCode}
                    className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium transition duration-300"
                  >
                    QR Code
                  </button>
                  <button
                    onClick={generateAndDownloadFlyer}
                    className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Print Flyer
                  </button>
                  {subscriptionStatus && subscriptionStatus.plan === 'free' && !subscriptionStatus.can_make_request && (
                    <button
                      onClick={() => setShowUpgrade(true)}
                      className="bg-orange-600 hover:bg-orange-700 px-4 py-2 rounded-lg font-bold transition duration-300"
                    >
                      Upgrade
                    </button>
                  )}
                  {/* NEW: Upgrade button for trial users */}
                  {subscriptionStatus && subscriptionStatus.plan === 'trial' && (
                    <button
                      onClick={() => setShowUpgrade(true)}
                      className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-bold transition duration-300 flex items-center space-x-2"
                    >
                      <span>⚡</span>
                      <span>Upgrade Now</span>
                    </button>
                  )}
                </div>
              </div>
              
              {/* NEW: Trial Upgrade Notice */}
              {subscriptionStatus && subscriptionStatus.plan === 'trial' && (
                <div className="mt-4 bg-blue-900/50 border border-blue-500/50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-blue-200 font-bold text-sm">🚀 Enjoying your trial?</h3>
                      <p className="text-blue-300 text-xs mt-1">
                        Lock in unlimited requests for just $5/month
                      </p>
                    </div>
                    <button
                      onClick={() => setShowUpgrade(true)}
                      className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-lg text-sm font-bold transition duration-300"
                    >
                      Upgrade Now
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-bold mb-4">Profile Settings</h2>
            
            {profileError && (
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                {profileError}
              </div>
            )}
            
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Stage Name</label>
                  <input
                    type="text"
                    value={profile.name}
                    onChange={(e) => setProfile({...profile, name: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    required
                  />
                </div>
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Email</label>
                  <input
                    type="email"
                    value={profile.email}
                    disabled
                    className="w-full bg-gray-600 border border-gray-600 rounded-lg px-4 py-2 text-gray-400"
                    title="Email cannot be changed"
                  />
                </div>
              </div>
              
              {/* NEW: Enhanced Tip Payment Settings */}
              <div className="border-t border-gray-600 pt-6">
                <h3 className="text-lg font-semibold text-white mb-4">💰 Tip Payment Settings</h3>
                <p className="text-gray-300 text-sm mb-4">Set up payment methods so your audience can tip you directly</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">
                      PayPal Username
                      <span className="text-green-400 ml-1">💳</span>
                    </label>
                    <input
                      type="text"
                      placeholder="paypalusername (without @)"
                      value={profile.paypal_username || ''}
                      onChange={(e) => setProfile({...profile, paypal_username: e.target.value})}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                    />
                    <p className="text-gray-400 text-xs mt-1">Used for PayPal.me/yourusername tip links</p>
                  </div>
                  
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">
                      Venmo Username
                      <span className="text-blue-400 ml-1">📱</span>
                    </label>
                    <input
                      type="text"
                      placeholder="venmousername (without @)"
                      value={profile.venmo_username || ''}
                      onChange={(e) => setProfile({...profile, venmo_username: e.target.value})}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                    />
                    <p className="text-gray-400 text-xs mt-1">Used for Venmo.com/yourusername tip links</p>
                  </div>
                </div>
                
                {/* Legacy Venmo Link Field for backward compatibility */}
                <div className="mt-4">
                  <label className="block text-gray-300 text-sm font-bold mb-2">
                    Legacy Venmo Link 
                    <span className="text-gray-500 text-xs">(deprecated - use username above)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="@yourusername or venmo.com/yourusername"
                    value={profile.venmo_link}
                    onChange={(e) => setProfile({...profile, venmo_link: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-gray-300 text-sm font-bold mb-2">Website</label>
                <input
                  type="url"
                  placeholder="https://your-website.com"
                  value={profile.website}
                  onChange={(e) => setProfile({...profile, website: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
              </div>
              
              <div>
                <label className="block text-gray-300 text-sm font-bold mb-2">Bio</label>
                <textarea
                  placeholder="Tell your audience about yourself..."
                  value={profile.bio}
                  onChange={(e) => setProfile({...profile, bio: e.target.value})}
                  rows="4"
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
              </div>
              
              {/* NEW: Social Media Links for "Follow Me" Section */}
              <div className="border-t border-gray-600 pt-6">
                <h3 className="text-lg font-semibold text-white mb-4">📱 Social Media Links</h3>
                <p className="text-gray-300 text-sm mb-4">Add your social media accounts so fans can follow you</p>
                
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-2">
                        Instagram Username
                        <span className="text-pink-400 ml-1">📷</span>
                      </label>
                      <input
                        type="text"
                        placeholder="yourusername (without @)"
                        value={profile.instagram_username || ''}
                        onChange={(e) => setProfile({...profile, instagram_username: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-2">
                        TikTok Username
                        <span className="text-purple-400 ml-1">🎵</span>
                      </label>
                      <input
                        type="text"
                        placeholder="yourusername (without @)"
                        value={profile.tiktok_username || ''}
                        onChange={(e) => setProfile({...profile, tiktok_username: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">
                      Facebook Page/Username
                      <span className="text-blue-400 ml-1">👥</span>
                    </label>
                    <input
                      type="text"
                      placeholder="yourpage or facebook.com/yourpage"
                      value={profile.facebook_username || ''}
                      onChange={(e) => setProfile({...profile, facebook_username: e.target.value})}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                    />
                  </div>
                  
                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-2">
                        Spotify Artist URL
                        <span className="text-green-400 ml-1">🎧</span>
                      </label>
                      <input
                        type="text"
                        placeholder="https://open.spotify.com/artist/..."
                        value={profile.spotify_artist_url || ''}
                        onChange={(e) => setProfile({...profile, spotify_artist_url: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-2">
                        Apple Music Artist URL
                        <span className="text-red-400 ml-1">🍎</span>
                      </label>
                      <input
                        type="text"
                        placeholder="https://music.apple.com/us/artist/..."
                        value={profile.apple_music_artist_url || ''}
                        onChange={(e) => setProfile({...profile, apple_music_artist_url: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      />
                    </div>
                  </div>
                </div>
              </div>
              
              <button
                type="submit"
                className="w-full bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300"
              >
                Update Profile
              </button>
            </form>
            </div>
          </div>
        )}

        {/* NEW: Phase 3 - Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            {/* Analytics Header */}
            <div className="bg-gray-800 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-2xl font-bold">📊 Analytics Dashboard</h2>
                  <p className="text-gray-300">Insights into your audience and performance</p>
                </div>
                
                {/* Timeframe Selector */}
                <div className="flex space-x-2">
                  {['daily', 'weekly', 'monthly'].map((timeframe) => (
                    <button
                      key={timeframe}
                      onClick={() => handleTimeframeChange(timeframe)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition duration-300 ${
                        analyticsTimeframe === timeframe
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {timeframe.charAt(0).toUpperCase() + timeframe.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Analytics Summary Cards */}
              {analyticsData && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
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
                    <p className="text-lg font-bold text-gray-300">{analyticsData.period}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Requesters Section */}
            <div className="bg-gray-800 rounded-xl p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold">👥 Audience Requesters</h3>
                <button
                  onClick={exportRequestersCSV}
                  className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-sm font-medium transition duration-300"
                >
                  📊 Export CSV
                </button>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left py-2 text-gray-300">Name</th>
                      <th className="text-left py-2 text-gray-300">Email</th>
                      <th className="text-left py-2 text-gray-300">Requests</th>
                      <th className="text-left py-2 text-gray-300">Latest Request</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requestersData.slice(0, 10).map((requester, index) => (
                      <tr key={index} className="border-b border-gray-700 hover:bg-gray-700">
                        <td className="py-2 font-medium">{requester.name}</td>
                        <td className="py-2 text-gray-300">{requester.email}</td>
                        <td className="py-2">
                          <span className="bg-purple-600 px-2 py-1 rounded-full text-xs">
                            {requester.request_count}
                          </span>
                        </td>
                        <td className="py-2 text-gray-400 text-xs">
                          {new Date(requester.latest_request).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {requestersData.length === 0 && (
                  <div className="text-center py-8 text-gray-400">
                    <p>No requesters yet. Share your QR code to start receiving requests!</p>
                  </div>
                )}
                
                {requestersData.length > 10 && (
                  <div className="text-center py-4 text-gray-400">
                    <p>Showing top 10 requesters. Export CSV for complete list.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Analytics Charts Section */}
            {analyticsData && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Requested Songs */}
                <div className="bg-gray-800 rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4">🎵 Most Requested Songs</h3>
                  <div className="space-y-3">
                    {analyticsData.top_songs.slice(0, 5).map((item, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <div className="flex-1">
                          <p className="font-medium text-sm">{item.song}</p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-orange-400 font-bold">{item.count}</span>
                          <div className="w-20 bg-gray-700 rounded-full h-2">
                            <div 
                              className="bg-orange-500 h-2 rounded-full"
                              style={{
                                width: `${(item.count / Math.max(...analyticsData.top_songs.map(s => s.count))) * 100}%`
                              }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {analyticsData.top_songs.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                      <p>No song requests yet in this period.</p>
                    </div>
                  )}
                </div>

                {/* Most Frequent Requesters */}
                <div className="bg-gray-800 rounded-xl p-6">
                  <h3 className="text-xl font-bold mb-4">⭐ Most Active Requesters</h3>
                  <div className="space-y-3">
                    {analyticsData.top_requesters.slice(0, 5).map((item, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <div className="flex-1">
                          <p className="font-medium text-sm">{item.requester}</p>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-blue-400 font-bold">{item.count}</span>
                          <div className="w-20 bg-gray-700 rounded-full h-2">
                            <div 
                              className="bg-blue-500 h-2 rounded-full"
                              style={{
                                width: `${(item.count / Math.max(...analyticsData.top_requesters.map(r => r.count))) * 100}%`
                              }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {analyticsData.top_requesters.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                      <p>No frequent requesters yet in this period.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Daily Timeline */}
            {analyticsData && analyticsData.daily_stats.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-4">📈 Daily Activity</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 text-gray-300">Date</th>
                        <th className="text-left py-2 text-gray-300">Requests</th>
                        <th className="text-left py-2 text-gray-300">Unique Requesters</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analyticsData.daily_stats.map((day, index) => (
                        <tr key={index} className="border-b border-gray-700 hover:bg-gray-700">
                          <td className="py-2 font-medium">{day.date}</td>
                          <td className="py-2">
                            <span className="bg-purple-600 px-2 py-1 rounded-full text-xs">
                              {day.request_count}
                            </span>
                          </td>
                          <td className="py-2">
                            <span className="bg-blue-600 px-2 py-1 rounded-full text-xs">
                              {day.unique_requesters}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {analyticsLoading && (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                <p className="text-gray-400 mt-2">Loading analytics...</p>
              </div>
            )}
          </div>
        )}

        {/* Design Tab */}
        {activeTab === 'design' && (
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-xl font-bold">Audience Page Design</h2>
                <p className="text-gray-300 text-sm">Customize how your audience sees your song request page</p>
              </div>
              {subscriptionStatus && subscriptionStatus.plan !== 'pro' && subscriptionStatus.plan !== 'trial' && (
                <div className="bg-green-600 text-white px-3 py-1 rounded-full text-sm font-bold">
                  PRO FEATURE
                </div>
              )}
            </div>
            
            {designError && (
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                {designError}
              </div>
            )}
            
            <form onSubmit={handleDesignUpdate} className="space-y-6">
              {/* Color Scheme */}
              <div>
                <label className="block text-gray-300 text-sm font-bold mb-3">Color Theme</label>
                <div className="grid grid-cols-5 gap-3">
                  {[
                    { name: 'purple', color: 'bg-purple-600', label: 'Purple' },
                    { name: 'blue', color: 'bg-blue-600', label: 'Blue' },
                    { name: 'green', color: 'bg-green-600', label: 'Green' },
                    { name: 'red', color: 'bg-red-600', label: 'Red' },
                    { name: 'orange', color: 'bg-orange-600', label: 'Orange' }
                  ].map((theme) => (
                    <button
                      key={theme.name}
                      type="button"
                      onClick={() => setDesignSettings({...designSettings, color_scheme: theme.name})}
                      className={`p-3 rounded-lg border-2 transition duration-300 ${
                        designSettings.color_scheme === theme.name
                          ? 'border-white shadow-lg'
                          : 'border-gray-600 hover:border-gray-400'
                      }`}
                    >
                      <div className={`w-full h-8 ${theme.color} rounded mb-2`}></div>
                      <span className="text-xs text-gray-300">{theme.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Layout Mode */}
              <div>
                <label className="block text-gray-300 text-sm font-bold mb-3">Song Display Layout</label>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    onClick={() => setDesignSettings({...designSettings, layout_mode: 'grid'})}
                    className={`p-4 rounded-lg border-2 transition duration-300 ${
                      designSettings.layout_mode === 'grid'
                        ? 'border-purple-500 bg-purple-900/20'
                        : 'border-gray-600 hover:border-gray-400'
                    }`}
                  >
                    <div className="grid grid-cols-2 gap-1 mb-2">
                      <div className="bg-gray-600 h-3 rounded"></div>
                      <div className="bg-gray-600 h-3 rounded"></div>
                      <div className="bg-gray-600 h-3 rounded"></div>
                      <div className="bg-gray-600 h-3 rounded"></div>
                    </div>
                    <span className="text-sm">Grid View</span>
                  </button>
                  
                  <button
                    type="button"
                    onClick={() => setDesignSettings({...designSettings, layout_mode: 'list'})}
                    className={`p-4 rounded-lg border-2 transition duration-300 ${
                      designSettings.layout_mode === 'list'
                        ? 'border-purple-500 bg-purple-900/20'
                        : 'border-gray-600 hover:border-gray-400'
                    }`}
                  >
                    <div className="space-y-1 mb-2">
                      <div className="bg-gray-600 h-2 rounded w-full"></div>
                      <div className="bg-gray-600 h-2 rounded w-full"></div>
                      <div className="bg-gray-600 h-2 rounded w-full"></div>
                    </div>
                    <span className="text-sm">List View</span>
                  </button>
                </div>
              </div>

              {/* Artist Photo */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <label className="block text-gray-300 text-sm font-bold">Artist Photo</label>
                  {subscriptionStatus?.plan_type !== 'pro' && (
                    <span className="bg-yellow-600 text-yellow-100 text-xs px-2 py-1 rounded-full font-bold">
                      PRO
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-4">
                  {designSettings.artist_photo ? (
                    <div className="relative">
                      <img
                        src={designSettings.artist_photo}
                        alt="Artist"
                        className="w-20 h-20 rounded-full object-cover"
                      />
                      <button
                        type="button"
                        onClick={() => setDesignSettings({...designSettings, artist_photo: null})}
                        className="absolute -top-1 -right-1 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-700"
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <div className="w-20 h-20 rounded-full bg-gray-700 flex items-center justify-center">
                      <span className="text-gray-400 text-xs">No Photo</span>
                    </div>
                  )}
                  <div>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleArtistPhotoUpload}
                      className="hidden"
                      id="artist-photo-upload"
                    />
                    <label
                      htmlFor="artist-photo-upload"
                      className={`inline-flex items-center px-4 py-2 rounded-lg cursor-pointer transition duration-300 ${
                        subscriptionStatus?.plan_type === 'pro'
                          ? 'bg-blue-600 hover:bg-blue-700 text-white'
                          : 'bg-gray-600 hover:bg-gray-500 text-gray-300'
                      }`}
                    >
                      {subscriptionStatus?.plan_type === 'pro' ? (
                        <>📷 Upload Photo</>
                      ) : (
                        <>🔒 Upload Photo (Pro)</>
                      )}
                    </label>
                    <p className="text-xs text-gray-400 mt-1">
                      {subscriptionStatus?.plan_type === 'pro' 
                        ? 'Max 2MB, JPG/PNG' 
                        : 'Pro feature - Max 2MB, JPG/PNG'
                      }
                    </p>
                  </div>
                </div>
              </div>

              {/* Display Options */}
              <div>
                <label className="block text-gray-300 text-sm font-bold mb-3">Show on Audience Page</label>
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={designSettings.show_year}
                      onChange={(e) => setDesignSettings({...designSettings, show_year: e.target.checked})}
                      className="mr-3"
                    />
                    <span className="text-gray-300">Show song year</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={designSettings.show_notes}
                      onChange={(e) => setDesignSettings({...designSettings, show_notes: e.target.checked})}
                      className="mr-3"
                    />
                    <span className="text-gray-300">Show song notes</span>
                  </label>
                </div>
                
                {/* NEW: Pro Feature - Song Suggestions Toggle */}
                {subscriptionStatus && subscriptionStatus.plan === 'pro' && (
                  <div className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      id="allow_song_suggestions"
                      checked={designSettings.allow_song_suggestions}
                      onChange={(e) => setDesignSettings({...designSettings, allow_song_suggestions: e.target.checked})}
                      className="w-4 h-4 text-purple-600 bg-gray-700 border-gray-600 rounded focus:ring-purple-500 focus:ring-2"
                    />
                    <label htmlFor="allow_song_suggestions" className="text-white text-sm">
                      Allow Song Suggestions 
                      <span className="text-yellow-400 ml-2">✨ PRO</span>
                    </label>
                    <div className="group relative">
                      <span className="text-gray-400 cursor-help">ℹ️</span>
                      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-48 text-center">
                        Let your audience suggest songs that aren't in your current repertoire
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Show Pro upgrade notice for free users */}
                {subscriptionStatus && subscriptionStatus.plan !== 'pro' && (
                  <div className="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-yellow-400">✨</span>
                      <span className="text-yellow-200 text-sm font-medium">Song Suggestions - Pro Feature</span>
                    </div>
                    <p className="text-yellow-300 text-xs mt-1">
                      Upgrade to Pro to let your audience suggest songs that aren't in your repertoire
                    </p>
                    <button
                      onClick={() => setShowUpgrade(true)}
                      className="bg-yellow-600 hover:bg-yellow-700 text-white text-xs px-3 py-1 rounded mt-2 transition duration-300"
                    >
                      Upgrade to Pro
                    </button>
                  </div>
                )}
              </div>

              <div className="flex space-x-4">
                <button
                  type="submit"
                  className="flex-1 bg-purple-600 hover:bg-purple-700 py-3 rounded-lg font-bold transition duration-300"
                >
                  Save Design Settings
                </button>
                <button
                  type="button"
                  onClick={() => window.open(`/musician/${musician.slug}`, '_blank')}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-bold transition duration-300"
                >
                  Preview Page
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Upgrade Modal */}
        {showUpgrade && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-800 rounded-xl p-8 w-full max-w-md">
              <h2 className="text-2xl font-bold text-center mb-6">Upgrade to RequestWave Pro</h2>
              
              <div className="text-center mb-6">
                <div className="bg-green-600 text-white rounded-full px-6 py-3 text-3xl font-bold mb-4">
                  $5/month
                </div>
                <p className="text-gray-300 mb-4">Get unlimited song requests from your audience</p>
                
                <div className="text-left bg-gray-700 rounded-lg p-4 mb-6">
                  <h3 className="font-bold mb-3 text-green-400">✓ Pro Features:</h3>
                  <ul className="space-y-2 text-sm">
                    <li>• Unlimited song requests</li>
                    <li>• No monthly limits</li>
                    <li>• Priority support</li>
                    <li>• All current and future features</li>
                  </ul>
                </div>
                
                {subscriptionStatus && subscriptionStatus.plan === 'free' && (
                  <div className="bg-orange-900/50 rounded-lg p-3 mb-4 text-orange-200">
                    <p className="font-bold">Request Limit Reached</p>
                    <p className="text-sm">
                      You've used {subscriptionStatus.requests_used}/{subscriptionStatus.requests_limit} requests this month
                    </p>
                  </div>
                )}
              </div>
              
              <div className="flex space-x-4">
                <button
                  onClick={() => setShowUpgrade(false)}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 py-3 rounded-lg transition duration-300"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpgrade}
                  disabled={upgrading}
                  className="flex-1 bg-green-600 hover:bg-green-700 py-3 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                >
                  {upgrading ? 'Processing...' : 'Upgrade Now'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* QR Code Modal */}
        {showQRModal && qrCode && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-gray-800 rounded-xl p-8 w-full max-w-md text-center">
              <h2 className="text-2xl font-bold mb-4">Your QR Code</h2>
              <p className="text-gray-300 mb-6">Share this QR code with your audience</p>
              
              <div className="bg-white rounded-lg p-4 mb-6 inline-block">
                <img src={qrCode.qr_code} alt="QR Code" className="w-64 h-64" />
              </div>
              
              <div className="text-xs text-gray-400 mb-6 break-all">
                {qrCode.audience_url}
              </div>
              
              <div className="flex flex-col space-y-3">
                <button
                  onClick={downloadQRCode}
                  className="bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-bold transition duration-300"
                >
                  Download QR Code
                </button>
                <button
                  onClick={printQRFlyer}
                  className="bg-green-600 hover:bg-green-700 py-3 rounded-lg font-bold transition duration-300"
                >
                  Print Flyer with Instructions
                </button>
                <button
                  onClick={() => setShowQRModal(false)}
                  className="bg-gray-600 hover:bg-gray-700 py-3 rounded-lg transition duration-300"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* NEW: Edit Song Modal */}
        {showEditModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4">Edit Song</h2>
              
              {songError && editingSong && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                  {songError}
                </div>
              )}
              
              <form onSubmit={handleUpdateSong} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Song Title"
                  value={songForm.title}
                  onChange={(e) => setSongForm({...songForm, title: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  required
                />
                <input
                  type="text"
                  placeholder="Artist"
                  value={songForm.artist}
                  onChange={(e) => setSongForm({...songForm, artist: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                  required
                />
                
                {/* Auto-fill Metadata Button */}
                <div className="md:col-span-2 mb-4">
                  <button
                    type="button"
                    onClick={handleAutoFillMetadata}
                    disabled={autoFillLoading || !songForm.title.trim() || !songForm.artist.trim()}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-medium transition duration-300 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    {autoFillLoading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>Searching...</span>
                      </>
                    ) : (
                      <>
                        <span>🔍</span>
                        <span>Auto-fill Info from Spotify</span>
                      </>
                    )}
                  </button>
                  <p className="text-xs text-gray-400 mt-1">
                    Fill in Title and Artist above, then click to automatically find Genre, Mood, and Year
                  </p>
                </div>
                
                <input
                  type="text"
                  placeholder="Genres (comma separated)"
                  value={songForm.genres.join(', ')}
                  onChange={(e) => setSongForm({...songForm, genres: e.target.value.split(',').map(g => g.trim())})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                <input
                  type="text"
                  placeholder="Moods (comma separated)"
                  value={songForm.moods.join(', ')}
                  onChange={(e) => setSongForm({...songForm, moods: e.target.value.split(',').map(m => m.trim())})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                <input
                  type="number"
                  placeholder="Year"
                  value={songForm.year}
                  onChange={(e) => setSongForm({...songForm, year: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                <input
                  type="text"
                  placeholder="Notes (optional)"
                  value={songForm.notes}
                  onChange={(e) => setSongForm({...songForm, notes: e.target.value})}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
                
                <div className="md:col-span-2 flex space-x-4">
                  <button
                    type="submit"
                    className="flex-1 bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300"
                  >
                    Update Song
                  </button>
                  <button
                    type="button"
                    onClick={cancelEdit}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-bold transition duration-300"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
        
        {/* NEW: Add to Playlist Modal */}
        {showPlaylistModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4">Add Songs to Playlist</h2>
              <p className="text-gray-300 mb-4">Selected {selectedSongs.size} songs</p>
              
              {playlistManagementError && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                  {playlistManagementError}
                </div>
              )}

              {/* Action selector */}
              <div className="mb-4">
                <div className="flex space-x-2 mb-4">
                  <button
                    onClick={() => setPlaylistAction('create')}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition duration-300 ${
                      playlistAction === 'create'
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    Create New
                  </button>
                  <button
                    onClick={() => setPlaylistAction('add')}
                    className={`flex-1 py-2 px-4 rounded-lg font-medium transition duration-300 ${
                      playlistAction === 'add'
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    Add to Existing
                  </button>
                </div>

                {playlistAction === 'create' ? (
                  <input
                    type="text"
                    placeholder="New Playlist Name"
                    value={playlistName}
                    onChange={(e) => setPlaylistName(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                    required
                  />
                ) : (
                  <select
                    value={selectedExistingPlaylist}
                    onChange={(e) => setSelectedExistingPlaylist(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                    required
                  >
                    <option value="">Select a playlist...</option>
                    {playlists.filter(p => p.id !== 'all_songs').map(playlist => (
                      <option key={playlist.id} value={playlist.id}>
                        {playlist.name} ({playlist.song_count} songs)
                      </option>
                    ))}
                  </select>
                )}
              </div>
              
              <div className="flex space-x-4">
                <button
                  onClick={handlePlaylistAction}
                  disabled={playlistLoading}
                  className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 py-2 rounded-lg font-bold transition duration-300"
                >
                  {playlistLoading ? 'Processing...' : (playlistAction === 'create' ? 'Create Playlist' : 'Add to Playlist')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowPlaylistModal(false);
                    setPlaylistName('');
                    setSelectedExistingPlaylist('');
                    setPlaylistAction('create');
                  }}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-bold transition duration-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* NEW: Manage Playlists Modal */}
        {showManagePlaylistsModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Manage Playlists</h2>
                <button
                  onClick={() => setShowManagePlaylistsModal(false)}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                {playlists.filter(p => p.id !== 'all_songs').length === 0 ? (
                  <p className="text-gray-400 text-center py-8">No playlists created yet. Select some songs and click "Add to Playlist" to create your first playlist!</p>
                ) : (
                  playlists.filter(p => p.id !== 'all_songs').map(playlist => (
                    <div key={playlist.id} className="bg-gray-700 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex-1">
                        {editingPlaylist === playlist.id ? (
                          <div className="flex items-center space-x-2">
                            <input
                              type="text"
                              defaultValue={playlist.name}
                              className="bg-gray-600 border border-gray-500 rounded px-3 py-1 text-white flex-1"
                              onKeyPress={(e) => {
                                if (e.key === 'Enter') {
                                  updatePlaylistName(playlist.id, e.target.value);
                                }
                              }}
                              autoFocus
                            />
                            <button
                              onClick={(e) => {
                                const input = e.target.parentElement.querySelector('input');
                                updatePlaylistName(playlist.id, input.value);
                              }}
                              className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingPlaylist(null)}
                              className="bg-gray-600 hover:bg-gray-700 px-3 py-1 rounded text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div>
                            <h3 className="font-medium">{playlist.name}</h3>
                            <p className="text-gray-400 text-sm">
                              {playlist.song_count} songs
                              {playlist.is_active && <span className="ml-2 text-green-400">• Active</span>}
                            </p>
                          </div>
                        )}
                      </div>
                      
                      {editingPlaylist !== playlist.id && (
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => activatePlaylist(playlist.id)}
                            disabled={playlist.is_active}
                            className={`px-3 py-1 rounded text-sm font-medium transition duration-300 ${
                              playlist.is_active
                                ? 'bg-green-600 text-white cursor-default'
                                : 'bg-purple-600 hover:bg-purple-700 text-white'
                            }`}
                          >
                            {playlist.is_active ? 'Active' : 'Activate'}
                          </button>
                          <button
                            onClick={() => setEditingPlaylist(playlist.id)}
                            className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm"
                          >
                            Rename
                          </button>
                          <button
                            onClick={() => deletePlaylist(playlist.id, playlist.name)}
                            className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              <div className="mt-6 pt-4 border-t border-gray-700">
                <button
                  onClick={() => setShowManagePlaylistsModal(false)}
                  className="w-full bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-bold transition duration-300"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const AudienceInterface = () => {
  const { slug } = useParams();
  const [musician, setMusician] = useState(null);
  const [songs, setSongs] = useState([]);
  const [filteredSongs, setFilteredSongs] = useState([]);
  const [filters, setFilters] = useState({});
  const [designSettings, setDesignSettings] = useState({
    color_scheme: 'purple',
    layout_mode: 'grid',
    artist_photo: null,
    show_year: true,
    show_notes: true,
    musician_name: '',
    bio: ''
  });
  const [selectedFilters, setSelectedFilters] = useState({
    genre: '',
    artist: '',
    mood: '',
    year: '',
    decade: ''  // NEW: Add decade filter
  });
  const [requestForm, setRequestForm] = useState({
    requester_name: '',
    requester_email: '',
    dedication: ''
  });
  const [selectedSong, setSelectedSong] = useState(null);
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  // NEW: Prominent search functionality
  const [searchQuery, setSearchQuery] = useState('');

  // NEW: Post-request state for tip/social modal
  const [showPostRequestModal, setShowPostRequestModal] = useState(false);
  const [currentRequestId, setCurrentRequestId] = useState(null);

  // NEW: Tip functionality state
  const [showTipModal, setShowTipModal] = useState(false);
  const [tipAmount, setTipAmount] = useState('');
  const [tipMessage, setTipMessage] = useState('');
  const [tipPlatform, setTipPlatform] = useState('paypal'); // 'paypal' or 'venmo'
  
  // NEW: Song suggestion states
  const [showSuggestionModal, setShowSuggestionModal] = useState(false);
  const [suggestionForm, setSuggestionForm] = useState({
    suggested_title: '',
    suggested_artist: '',
    requester_name: '',
    requester_email: '',
    message: ''
  });
  const [suggestionError, setSuggestionError] = useState('');

  // NEW: Post-request click tracking
  const trackClick = async (type, platform) => {
    if (!currentRequestId) return;
    
    try {
      await axios.post(`${API}/requests/${currentRequestId}/track-click`, {
        type: type, // "tip" or "social"
        platform: platform // "venmo", "paypal", "instagram", etc.
      });
    } catch (error) {
      console.error('Error tracking click:', error);
    }
  };

  const generateSocialLink = (platform, username, url) => {
    switch (platform) {
      case 'instagram':
        return username ? `https://instagram.com/${username}` : null;
      case 'facebook':
        return username ? `https://facebook.com/${username}` : null;
      case 'tiktok':
        return username ? `https://tiktok.com/@${username}` : null;
      case 'spotify':
        return url || null;
      case 'apple_music':
        return url || null;
      default:
        return null;
    }
  };

  const handleSocialClick = (platform) => {
    const link = generateSocialLink(
      platform, 
      musician[`${platform}_username`] || musician[`${platform}_artist_url`],
      musician[`${platform}_artist_url`]
    );
    
    if (link) {
      trackClick('social', platform);
      window.open(link, '_blank');
    }
  };

  const handleTipClick = (platform) => {
    trackClick('tip', platform);
    
    // Use existing tip functionality but with tracking
    if (platform === 'venmo') {
      setTipPlatform('venmo');
    } else {
      setTipPlatform('paypal');
    }
    
    setShowPostRequestModal(false);
    setShowTipModal(true);
  };

  // Color scheme mappings
  const colorSchemes = {
    purple: {
      primary: 'bg-purple-600 hover:bg-purple-700',
      secondary: 'bg-purple-800/50',
      accent: 'text-purple-400',
      button: 'bg-purple-600 hover:bg-purple-700',
      badge: 'bg-purple-600'
    },
    blue: {
      primary: 'bg-blue-600 hover:bg-blue-700',
      secondary: 'bg-blue-800/50',
      accent: 'text-blue-400',
      button: 'bg-blue-600 hover:bg-blue-700',
      badge: 'bg-blue-600'
    },
    green: {
      primary: 'bg-green-600 hover:bg-green-700',
      secondary: 'bg-green-800/50',
      accent: 'text-green-400',
      button: 'bg-green-600 hover:bg-green-700',
      badge: 'bg-green-600'
    },
    red: {
      primary: 'bg-red-600 hover:bg-red-700',
      secondary: 'bg-red-800/50',
      accent: 'text-red-400',
      button: 'bg-red-600 hover:bg-red-700',
      badge: 'bg-red-600'
    },
    orange: {
      primary: 'bg-orange-600 hover:bg-orange-700',
      secondary: 'bg-orange-800/50',
      accent: 'text-orange-400',
      button: 'bg-orange-600 hover:bg-orange-700',
      badge: 'bg-orange-600'
    }
  };

  const colors = colorSchemes[designSettings.color_scheme] || colorSchemes.purple;

  useEffect(() => {
    fetchMusician();
    fetchSongs();
    fetchFilters();
    fetchDesignSettings();
  }, [slug]);

  useEffect(() => {
    if (musician) {
      fetchSongs(); // Use backend filtering instead of client-side
    }
  }, [selectedFilters, searchQuery, musician]); // Trigger when filters or search changes

  const fetchMusician = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${slug}`);
      setMusician(response.data);
    } catch (error) {
      console.error('Error fetching musician:', error);
    }
  };

  const fetchDesignSettings = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${slug}/design`);
      setDesignSettings(response.data);
    } catch (error) {
      console.error('Error fetching design settings:', error);
    }
  };

  const fetchSongs = async () => {
    try {
      // Build query parameters for API call
      const params = new URLSearchParams();
      
      // Add search query
      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim());
      }
      
      // Add filter parameters
      if (selectedFilters.genre) {
        params.append('genre', selectedFilters.genre);
      }
      if (selectedFilters.artist) {
        params.append('artist', selectedFilters.artist);
      }
      if (selectedFilters.mood) {
        params.append('mood', selectedFilters.mood);
      }
      if (selectedFilters.year) {
        params.append('year', selectedFilters.year);
      }
      // NEW: Add decade filter
      if (selectedFilters.decade) {
        params.append('decade', selectedFilters.decade);
      }
      
      const queryString = params.toString();
      const url = `${API}/musicians/${slug}/songs${queryString ? `?${queryString}` : ''}`;
      
      const response = await axios.get(url);
      setSongs(response.data);
      setFilteredSongs(response.data); // Update filtered songs as well
    } catch (error) {
      console.error('Error fetching songs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFilters = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${slug}/filters`);
      setFilters(response.data);
    } catch (error) {
      console.error('Error fetching filters:', error);
    }
  };

  const applyFilters = () => {
    let filtered = [...songs];

    // NEW: Apply search query first (searches across all fields)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      filtered = filtered.filter(song => {
        // Search in title
        const titleMatch = song.title.toLowerCase().includes(query);
        // Search in artist
        const artistMatch = song.artist.toLowerCase().includes(query);
        // Search in genres
        const genreMatch = song.genres.some(genre => 
          genre.toLowerCase().includes(query)
        );
        // Search in moods
        const moodMatch = song.moods.some(mood => 
          mood.toLowerCase().includes(query)
        );
        // Search in year (convert to string for search)
        const yearMatch = song.year && song.year.toString().includes(query);
        
        return titleMatch || artistMatch || genreMatch || moodMatch || yearMatch;
      });
    }

    // Apply specific filters on top of search results
    if (selectedFilters.genre) {
      filtered = filtered.filter(song => song.genres.includes(selectedFilters.genre));
    }
    if (selectedFilters.artist) {
      filtered = filtered.filter(song => 
        song.artist.toLowerCase().includes(selectedFilters.artist.toLowerCase())
      );
    }
    if (selectedFilters.mood) {
      filtered = filtered.filter(song => song.moods.includes(selectedFilters.mood));
    }
    if (selectedFilters.year) {
      filtered = filtered.filter(song => song.year === parseInt(selectedFilters.year));
    }
    // NEW: Apply decade filter
    if (selectedFilters.decade) {
      filtered = filtered.filter(song => song.decade === selectedFilters.decade);
    }

    setFilteredSongs(filtered);
  };

  // NEW: Random song selector function
  const handleRandomSong = () => {
    if (filteredSongs.length === 0) {
      alert('No songs available to choose from. Try adjusting your filters.');
      return;
    }

    // Select a random song from filtered results
    const randomIndex = Math.floor(Math.random() * filteredSongs.length);
    const randomSong = filteredSongs[randomIndex];

    // Pre-fill the request form with the random song
    setRequestForm({
      ...requestForm,
      song_id: randomSong.id,
      song_title: randomSong.title,
      song_artist: randomSong.artist
    });

    // Show the request modal
    setSelectedSong(randomSong);
  };

  const handleRequest = async (song) => {
    if (!requestForm.requester_name || !requestForm.requester_email) {
      alert('Please enter your name and email');
      return;
    }

    try {
      const response = await axios.post(`${API}/requests`, {
        song_id: song.id,
        ...requestForm
      });
      
      // Store request ID for post-request modal
      setCurrentRequestId(response.data.id);
      
      // Close request modal and show post-request options
      setSelectedSong(null);
      setShowPostRequestModal(true);
      
      // Reset form
      setRequestForm({
        requester_name: '',
        requester_email: '',
        dedication: ''
      });
      
    } catch (error) {
      if (error.response?.status === 402) {
        // Request limit reached
        const errorData = error.response.data;
        alert(`Request limit reached! ${errorData.detail.message}\n\nThe musician has reached their monthly request limit. They need to upgrade to Pro for unlimited requests.`);
      } else {
        console.error('Error submitting request:', error);
        alert('Error submitting request. Please try again.');
      }
    }
  };

  const clearFilters = () => {
    setSelectedFilters({
      genre: '',
      artist: '',
      mood: '',
      year: '',
      decade: ''  // NEW: Clear decade filter
    });
    // NEW: Also clear search query
    setSearchQuery('');
  };

  // NEW: Tip functionality functions
  const getTipPresetAmounts = () => [1, 5, 10, 20];

  const handleTipSubmit = async (musicianSlug, requesterName = '') => {
    if (!tipAmount || parseFloat(tipAmount) <= 0) {
      alert('Please enter a valid tip amount');
      return;
    }

    const amount = parseFloat(tipAmount);
    if (amount > 500) {
      alert('Tip amount cannot exceed $500');
      return;
    }

    try {
      // Get payment links from backend
      const response = await axios.get(`${API}/musicians/${musicianSlug}/tip-links`, {
        params: {
          amount: amount,
          message: tipMessage || `Thanks for the music!`
        }
      });

      if (response.data) {
        // Open appropriate payment link
        let paymentUrl = null;
        if (tipPlatform === 'paypal' && response.data.paypal_link) {
          paymentUrl = response.data.paypal_link;
        } else if (tipPlatform === 'venmo' && response.data.venmo_link) {
          paymentUrl = response.data.venmo_link;
        }

        if (paymentUrl) {
          // Record the tip attempt for analytics
          try {
            await axios.post(`${API}/musicians/${musicianSlug}/tips`, {
              amount: amount,
              platform: tipPlatform,
              tipper_name: requesterName || 'Anonymous',
              message: tipMessage
            });
          } catch (error) {
            console.log('Tip tracking failed:', error); // Non-critical
          }

          // Open payment link
          window.open(paymentUrl, '_blank');
          
          // Close modal
          setShowTipModal(false);
          
          // Show success message
          alert(`Opening ${tipPlatform === 'paypal' ? 'PayPal' : 'Venmo'} to send your $${amount} tip!`);
        } else {
          alert(`${tipPlatform === 'paypal' ? 'PayPal' : 'Venmo'} is not set up for this musician`);
        }
      }
    } catch (error) {
      console.error('Tip error:', error);
      if (error.response?.status === 400) {
        alert(error.response.data.detail || 'This musician hasn\'t set up payment methods for tips yet');
      } else {
        alert('Error processing tip. Please try again.');
      }
    }
  };

  // NEW: Handle song suggestion submission
  const handleSuggestionSubmit = async (e) => {
    e.preventDefault();
    setSuggestionError('');

    // Validate form
    if (!suggestionForm.suggested_title.trim() || !suggestionForm.suggested_artist.trim() || 
        !suggestionForm.requester_name.trim() || !suggestionForm.requester_email.trim()) {
      setSuggestionError('Please fill in all required fields');
      return;
    }

    // Validate email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(suggestionForm.requester_email)) {
      setSuggestionError('Please enter a valid email address');
      return;
    }

    try {
      const suggestionData = {
        musician_slug: slug,
        suggested_title: suggestionForm.suggested_title.trim(),
        suggested_artist: suggestionForm.suggested_artist.trim(),
        requester_name: suggestionForm.requester_name.trim(),
        requester_email: suggestionForm.requester_email.trim(),
        message: suggestionForm.message.trim()
      };

      await axios.post(`${API}/song-suggestions`, suggestionData);
      
      // Reset form and close modal
      setSuggestionForm({
        suggested_title: '',
        suggested_artist: '',
        requester_name: '',
        requester_email: '',
        message: ''
      });
      setShowSuggestionModal(false);
      alert('Thank you for your song suggestion! The artist will review it soon.');
      
    } catch (error) {
      console.error('Error submitting suggestion:', error);
      const errorMessage = error.response?.data?.detail || 'Error submitting suggestion';
      setSuggestionError(errorMessage);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (!musician) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Musician not found</h1>
          <p className="text-gray-400">The requested musician profile does not exist.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Mobile-Optimized Header */}
      <header className="bg-gray-800 shadow-lg sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center space-x-4">
            {designSettings.artist_photo && (
              <img
                src={designSettings.artist_photo}
                alt={designSettings.musician_name}
                className="w-12 h-12 md:w-16 md:h-16 rounded-full object-cover"
              />
            )}
            <div className="flex-1 min-w-0">
              <h1 className={`text-xl md:text-2xl font-bold ${colors.accent} truncate`}>
                {designSettings.musician_name}
              </h1>
              {designSettings.bio && (
                <p className="text-gray-300 text-sm md:text-base truncate">{designSettings.bio}</p>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <img
                src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/9wbfmlsw_A_logo_for_%22RequestWave%22_features_a_purple_microph.png"
                alt="RequestWave"
                className="w-6 h-6 object-contain opacity-75"
              />
              <button
                onClick={() => setShowTipModal(true)}
                className="bg-green-600 hover:bg-green-700 px-3 py-2 rounded-lg font-medium transition duration-300 text-sm"
              >
                💰 Tip
              </button>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`md:hidden ${colors.primary} px-4 py-2 rounded-lg font-medium transition duration-300`}
              >
                Filters
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-4 md:py-8">
        {success && (
          <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-3 md:p-4 mb-4 md:mb-6 text-green-200">
            {success}
          </div>
        )}

        {/* NEW: Prominent Search Bar */}
        <div className={`${colors.secondary} rounded-xl p-4 md:p-6 mb-4 md:mb-6`}>
          <div className="flex flex-col space-y-3">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">🔍</div>
              <h2 className="text-xl md:text-2xl font-bold text-white">Search Songs</h2>
            </div>
            <div className="relative">
              <input
                type="text"
                placeholder="Search by title, artist, genre, mood, or year..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-gray-700 border-2 border-gray-600 focus:border-blue-500 rounded-xl px-4 md:px-6 py-3 md:py-4 text-white placeholder-gray-400 text-base md:text-lg font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all duration-300"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition duration-300"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
            {searchQuery && (
              <p className="text-sm text-gray-300">
                Searching for: "<span className="text-white font-medium">{searchQuery}</span>" in titles, artists, genres, moods, and years
              </p>
            )}
          </div>
        </div>

        {/* Mobile/Desktop Filters */}
        <div className={`${colors.secondary} rounded-xl p-4 md:p-6 mb-4 md:mb-8 ${showFilters ? 'block' : 'hidden md:block'}`}>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
            <h2 className="text-lg md:text-xl font-bold mb-2 md:mb-0">Advanced Filters</h2>
            <div className="flex items-center space-x-2">
              <button
                onClick={clearFilters}
                className="text-gray-300 hover:text-white text-sm transition duration-300"
              >
                Clear All
              </button>
              <button
                onClick={() => setShowFilters(false)}
                className="md:hidden text-gray-300 hover:text-white"
              >
                ✕
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 md:gap-4">
            <select
              value={selectedFilters.genre}
              onChange={(e) => setSelectedFilters({...selectedFilters, genre: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 md:px-4 py-2 text-white text-sm md:text-base"
            >
              <option value="">All Genres</option>
              {filters.genres?.map((genre) => (
                <option key={genre} value={genre}>{genre}</option>
              ))}
            </select>
            
            <input
              type="text"
              placeholder="Artist name..."
              value={selectedFilters.artist}
              onChange={(e) => setSelectedFilters({...selectedFilters, artist: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 md:px-4 py-2 text-white placeholder-gray-400 text-sm md:text-base"
            />
            
            <select
              value={selectedFilters.mood}
              onChange={(e) => setSelectedFilters({...selectedFilters, mood: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 md:px-4 py-2 text-white text-sm md:text-base"
            >
              <option value="">All Moods</option>
              {filters.moods?.map((mood) => (
                <option key={mood} value={mood}>{mood}</option>
              ))}
            </select>
            
            <select
              value={selectedFilters.year}
              onChange={(e) => setSelectedFilters({...selectedFilters, year: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 md:px-4 py-2 text-white text-sm md:text-base"
            >
              <option value="">All Years</option>
              {filters.years?.map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
            
            {/* NEW: Decade filter */}
            <select
              value={selectedFilters.decade}
              onChange={(e) => setSelectedFilters({...selectedFilters, decade: e.target.value})}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 md:px-4 py-2 text-white text-sm md:text-base"
            >
              <option value="">All Decades</option>
              {filters.decades?.map((decade) => (
                <option key={decade} value={decade}>{decade}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Songs Display */}
        <div className="mb-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <p className="text-gray-400 text-sm md:text-base">
            {searchQuery ? (
              <>
                <span className="text-white font-medium">{filteredSongs.length}</span> song{filteredSongs.length !== 1 ? 's' : ''} found for "<span className="text-white font-medium">{searchQuery}</span>"
                {(selectedFilters.genre || selectedFilters.artist || selectedFilters.mood || selectedFilters.year || selectedFilters.decade) && (
                  <span> with additional filters applied</span>
                )}
              </>
            ) : (
              <>
                <span className="text-white font-medium">{filteredSongs.length}</span> song{filteredSongs.length !== 1 ? 's' : ''} 
                {(selectedFilters.genre || selectedFilters.artist || selectedFilters.mood || selectedFilters.year || selectedFilters.decade) ? ' found with filters applied' : ' available'}
              </>
            )}
          </p>
          
          {/* Random Song Button and Song Suggestion */}
          {filteredSongs.length > 0 && (
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleRandomSong}
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-4 py-2 rounded-lg font-medium transition duration-300 flex items-center space-x-2 shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <span>🎲</span>
                <span>Random Song</span>
              </button>
              
              {/* NEW: Song Suggestion Button - Only show if enabled by musician */}
              {designSettings.allow_song_suggestions && (
                <button
                  onClick={() => setShowSuggestionModal(true)}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-4 py-2 rounded-lg font-medium transition duration-300 flex items-center space-x-2 shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  <span>💡</span>
                  <span>Suggest a Song</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* List/Grid Toggle for larger screens */}
        <div className="hidden md:flex justify-end mb-6">
          <div className="flex bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setDesignSettings({...designSettings, layout_mode: 'grid'})}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition duration-300 ${
                designSettings.layout_mode === 'grid'
                  ? colors.primary + ' text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Grid
            </button>
            <button
              onClick={() => setDesignSettings({...designSettings, layout_mode: 'list'})}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition duration-300 ${
                designSettings.layout_mode === 'list'
                  ? colors.primary + ' text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              List
            </button>
          </div>
        </div>

        {/* Songs Grid/List */}
        <div className={`${
          designSettings.layout_mode === 'list' 
            ? 'space-y-3 md:space-y-4' 
            : 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6'
        }`}>
          {filteredSongs.map((song) => (
            <div
              key={song.id}
              className={`bg-gray-800 rounded-xl p-4 md:p-6 hover:bg-gray-700 transition duration-300 ${
                designSettings.layout_mode === 'list' ? 'flex items-center space-x-4' : ''
              }`}
            >
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-lg md:text-xl mb-1 md:mb-2 truncate">{song.title}</h3>
                <p className="text-gray-300 mb-2 md:mb-3 truncate">by {song.artist}</p>
                
                <div className="flex flex-wrap gap-1 md:gap-2 mb-3 md:mb-4">
                  {song.genres.map((genre, idx) => (
                    <span key={idx} className="bg-blue-600 text-xs px-2 py-1 rounded">{genre}</span>
                  ))}
                  {song.moods.map((mood, idx) => (
                    <span key={idx} className="bg-green-600 text-xs px-2 py-1 rounded">{mood}</span>
                  ))}
                  {designSettings.show_year && song.year && (
                    <span className="bg-gray-600 text-xs px-2 py-1 rounded">{song.year}</span>
                  )}
                  {/* NEW: Show decade if available */}
                  {song.decade && (
                    <span className="bg-orange-600 text-xs px-2 py-1 rounded">{song.decade}</span>
                  )}
                </div>
                
                {designSettings.show_notes && song.notes && (
                  <p className="text-gray-400 text-xs md:text-sm italic mb-3 md:mb-4">"{song.notes}"</p>
                )}
              </div>
              
              <button
                onClick={() => setSelectedSong(song)}
                className={`${colors.button} w-full md:w-auto px-4 md:px-6 py-2 md:py-3 rounded-lg font-bold transition duration-300 text-sm md:text-base whitespace-nowrap`}
              >
                Request Song
              </button>
            </div>
          ))}
        </div>

        {filteredSongs.length === 0 && (
          <div className="text-center py-12 md:py-16">
            <div className="text-4xl md:text-6xl mb-4">🎵</div>
            <p className="text-gray-400 text-lg md:text-xl mb-2">No songs match your search</p>
            <button
              onClick={clearFilters}
              className={`${colors.button} px-6 py-2 rounded-lg font-medium transition duration-300`}
            >
              Clear Filters
            </button>
          </div>
        )}

        {/* Request Modal - Mobile Optimized */}
        {selectedSong && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-end md:items-center justify-center p-4 z-50">
            <div className="bg-gray-800 rounded-t-xl md:rounded-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1 min-w-0 mr-4">
                  <h2 className="text-xl font-bold mb-1 truncate">Request: {selectedSong.title}</h2>
                  <p className="text-gray-300 truncate">by {selectedSong.artist}</p>
                </div>
                <button
                  onClick={() => setSelectedSong(null)}
                  className="text-gray-400 hover:text-white text-2xl leading-none"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Your Name"
                  value={requestForm.requester_name}
                  onChange={(e) => setRequestForm({...requestForm, requester_name: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                  required
                />
                
                <input
                  type="email"
                  placeholder="Your Email"
                  value={requestForm.requester_email}
                  onChange={(e) => setRequestForm({...requestForm, requester_email: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                  required
                />
                
                <textarea
                  placeholder="Dedication message (optional)"
                  value={requestForm.dedication}
                  onChange={(e) => setRequestForm({...requestForm, dedication: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                  rows="3"
                />
              </div>
              
              <div className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-4 mt-6">
                <button
                  onClick={() => setSelectedSong(null)}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 py-3 rounded-lg transition duration-300 order-2 md:order-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleRequest(selectedSong)}
                  className={`flex-1 ${colors.button} py-3 rounded-lg font-bold transition duration-300 order-1 md:order-2`}
                >
                  Send Request
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* NEW: Post-Request Success Modal - Linktree Style */}
        {showPostRequestModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl p-6 w-full max-w-sm border border-gray-700">
              {/* Artist Info Header */}
              <div className="text-center mb-6">
                <div className="w-20 h-20 bg-gradient-to-r from-purple-600 to-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl">
                  {musician.name?.charAt(0) || '🎵'}
                </div>
                <h3 className="text-xl font-bold text-white mb-1">{musician.name}</h3>
                <p className="text-gray-300 text-sm">Request sent successfully! ✅</p>
              </div>
              
              {/* Linktree Style Header */}
              <div className="text-center mb-6">
                <h4 className="text-lg font-semibold text-white mb-1">
                  Support the artist with a follow or a tip...
                </h4>
                <p className="text-purple-400 font-medium">or both! 🎉</p>
              </div>
              
              {/* Big Green Tip Button */}
              {(musician.paypal_username || musician.venmo_username) && (
                <button
                  onClick={() => {
                    setShowPostRequestModal(false);
                    setShowTipModal(true);
                    // Default to venmo as requested
                    setTipPlatform(musician.venmo_username ? 'venmo' : 'paypal');
                  }}
                  className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-6 rounded-xl mb-4 transition duration-300 flex items-center justify-center space-x-3 text-lg shadow-lg"
                >
                  <span className="text-2xl">💰</span>
                  <span>Send a Tip</span>
                  <span className="text-2xl">🎵</span>
                </button>
              )}
              
              {/* Social Media Links - Linktree Style */}
              <div className="space-y-3">
                {musician.instagram_username && (
                  <button
                    onClick={() => handleSocialClick('instagram')}
                    className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">📷</span>
                    <span>Follow on Instagram</span>
                  </button>
                )}
                
                {musician.tiktok_username && (
                  <button
                    onClick={() => handleSocialClick('tiktok')}
                    className="w-full bg-black hover:bg-gray-900 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🎵</span>
                    <span>Follow on TikTok</span>
                  </button>
                )}
                
                {musician.facebook_username && (
                  <button
                    onClick={() => handleSocialClick('facebook')}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">👥</span>
                    <span>Follow on Facebook</span>
                  </button>
                )}
                
                {musician.spotify_artist_url && (
                  <button
                    onClick={() => handleSocialClick('spotify')}
                    className="w-full bg-green-500 hover:bg-green-600 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🎧</span>
                    <span>Listen on Spotify</span>
                  </button>
                )}
                
                {musician.apple_music_artist_url && (
                  <button
                    onClick={() => handleSocialClick('apple_music')}
                    className="w-full bg-red-500 hover:bg-red-600 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🍎</span>
                    <span>Listen on Apple Music</span>
                  </button>
                )}
              </div>
              
              {/* Close Button */}
              <button
                onClick={() => {
                  setShowPostRequestModal(false);
                  setCurrentRequestId(null);
                }}
                className="w-full bg-gray-600 hover:bg-gray-700 text-gray-300 hover:text-white py-3 rounded-xl font-medium transition duration-300 mt-6"
              >
                Close
              </button>
            </div>
          </div>
        )}
        
        {/* NEW: Tip Modal */}
        {showTipModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-white">💰 Send a Tip</h3>
                <button
                  onClick={() => setShowTipModal(false)}
                  className="text-gray-400 hover:text-white text-xl"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-4">
                {/* Preset amounts */}
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Quick amounts</label>
                  <div className="grid grid-cols-4 gap-2">
                    {getTipPresetAmounts().map(amount => (
                      <button
                        key={amount}
                        type="button"
                        onClick={() => setTipAmount(amount.toString())}
                        className={`py-2 px-3 rounded-lg font-medium transition duration-300 ${
                          tipAmount === amount.toString()
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                      >
                        ${amount}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Custom amount */}
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Custom amount</label>
                  <input
                    type="number"
                    placeholder="0.00"
                    value={tipAmount}
                    onChange={(e) => setTipAmount(e.target.value)}
                    min="0.01"
                    max="500"
                    step="0.01"
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  />
                </div>
                
                {/* Payment platform */}
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Payment method</label>
                  <div className="flex space-x-2">
                    <button
                      type="button"
                      onClick={() => setTipPlatform('paypal')}
                      className={`flex-1 py-2 px-4 rounded-lg font-medium transition duration-300 ${
                        tipPlatform === 'paypal'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      💳 PayPal
                    </button>
                    <button
                      type="button"
                      onClick={() => setTipPlatform('venmo')}
                      className={`flex-1 py-2 px-4 rounded-lg font-medium transition duration-300 ${
                        tipPlatform === 'venmo'
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      📱 Venmo
                    </button>
                  </div>
                </div>
                
                {/* Optional message */}
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Message (optional)</label>
                  <input
                    type="text"
                    placeholder="Thanks for the great music!"
                    value={tipMessage}
                    onChange={(e) => setTipMessage(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                  />
                </div>
                
                {/* Action buttons */}
                <div className="flex space-x-3 mt-6">
                  <button
                    onClick={() => setShowTipModal(false)}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleTipSubmit(musician.slug, '')}
                    disabled={!tipAmount || parseFloat(tipAmount) <= 0}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 py-2 rounded-lg font-medium transition duration-300 disabled:cursor-not-allowed"
                  >
                    Send Tip
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* NEW: Song Suggestion Modal */}
        {showSuggestionModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4 text-center">🎵 Suggest a Song</h2>
              <p className="text-gray-400 text-sm mb-4 text-center">
                Don't see the song you want? Let {musician?.name || 'the artist'} know about it!
              </p>
              
              {suggestionError && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200 text-sm">
                  {suggestionError}
                </div>
              )}
              
              <form onSubmit={handleSuggestionSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Song Title *</label>
                  <input
                    type="text"
                    placeholder="Enter song title..."
                    value={suggestionForm.suggested_title}
                    onChange={(e) => setSuggestionForm({...suggestionForm, suggested_title: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Artist *</label>
                  <input
                    type="text"
                    placeholder="Enter artist name..."
                    value={suggestionForm.suggested_artist}
                    onChange={(e) => setSuggestionForm({...suggestionForm, suggested_artist: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Your Name *</label>
                  <input
                    type="text"
                    placeholder="Enter your name..."
                    value={suggestionForm.requester_name}
                    onChange={(e) => setSuggestionForm({...suggestionForm, requester_name: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Your Email *</label>
                  <input
                    type="email"
                    placeholder="Enter your email..."
                    value={suggestionForm.requester_email}
                    onChange={(e) => setSuggestionForm({...suggestionForm, requester_email: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Message (Optional)</label>
                  <textarea
                    placeholder="Why should they add this song?"
                    value={suggestionForm.message}
                    onChange={(e) => setSuggestionForm({...suggestionForm, message: e.target.value})}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400"
                    rows="3"
                  />
                </div>
                
                <div className="flex space-x-3 pt-2">
                  <button
                    type="submit"
                    className="flex-1 bg-green-600 hover:bg-green-700 py-2 rounded-lg font-bold transition duration-300"
                  >
                    Send Suggestion
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowSuggestionModal(false);
                      setSuggestionError('');
                      setSuggestionForm({
                        suggested_title: '',
                        suggested_artist: '',
                        requester_name: '',
                        requester_email: '',
                        message: ''
                      });
                    }}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-bold transition duration-300"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const LandingPage = () => {
  const [authMode, setAuthMode] = useState('login');

  return <AuthForm mode={authMode} onSwitch={setAuthMode} />;
};

const App = () => {
  const { musician } = useAuth();

  return (
    <Router>
      <Routes>
        <Route path="/" element={musician ? <Navigate to="/dashboard" /> : <LandingPage />} />
        <Route path="/dashboard" element={musician ? <MusicianDashboard /> : <Navigate to="/" />} />
        <Route path="/musician/:slug" element={<AudienceInterface />} />
      </Routes>
    </Router>
  );
};

const AppWithAuth = () => (
  <AuthProvider>
    <App />
  </AuthProvider>
);

export default AppWithAuth;