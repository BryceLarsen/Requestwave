import React, { useState, useEffect, useMemo, createContext, useContext, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import AdminPanel from './AdminPanel';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const BILLING_ENABLED = process.env.REACT_APP_BILLING_ENABLED === 'true';

// API URL — always derive from the environment-configured backend URL.
// Emergent auto-updates REACT_APP_BACKEND_URL at deploy time so this works
// for preview, production, and custom-domain deployments.
const API = `${BACKEND_URL}/api`;

// Audience URL base domain — derived at runtime from the page's origin so the
// app works correctly on any domain it's served from (preview, production, or
// a custom domain) without environment-specific configuration.
const AUDIENCE_BASE_URL =
  typeof window !== 'undefined' && window.location && window.location.origin
    ? window.location.origin
    : '';

// Single helper function for all audience URL generation
const getAudienceUrl = (slug) => {
  if (!slug) {
    console.error('getAudienceUrl called with invalid slug:', slug);
    return AUDIENCE_BASE_URL;
  }
  return `${AUDIENCE_BASE_URL}/musician/${slug}`;
};

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

  // Register a global axios response interceptor so any 401 from the API
  // immediately logs the user out and redirects them to the login screen.
  // Without this, a musician with an expired token would otherwise be left
  // staring at an empty logged-in shell.
  useEffect(() => {
    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401) {
          logout();
          window.location.href = '/';
        }
        return Promise.reject(error);
      }
    );
    return () => {
      axios.interceptors.response.eject(interceptorId);
    };
  }, []);

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

  // NEW: Log OAuth button rendered (telemetry)
  useEffect(() => {
    console.log('oauth_button_rendered', {
      mode: mode,
      environment: process.env.NODE_ENV || 'development',
      user_agent: navigator.userAgent,
      referrer: document.referrer,
      timestamp: new Date().toISOString()
    });
  }, [mode]);

  // NEW: Emergent OAuth handler with telemetry
  const handleEmergentOAuth = () => {
    // Log OAuth button click (non-PII telemetry)
    console.log('oauth_click', {
      environment: process.env.NODE_ENV || 'development',
      user_agent: navigator.userAgent,
      referrer: document.referrer,
      timestamp: new Date().toISOString()
    });
    
    // Get current preview URL for redirect
    const currentUrl = window.location.origin;
    const redirectUrl = `${currentUrl}/profile`;
    
    // Redirect to Emergent OAuth
    const emergentOAuthUrl = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    window.location.href = emergentOAuthUrl;
  };

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
    <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl">
      {!showForgotPassword ? (
        <>
          <h2 className="text-2xl font-bold text-white text-center mb-6">
            {mode === 'login' ? 'Welcome Back' : (
              <>
                Join <span className="text-purple-400">Request</span><span className="text-green-400">Wave</span>
              </>
            )}
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

          {/* NEW: Emergent OAuth Login Option */}
          <div className="mt-4">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/20"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-transparent text-purple-200">or</span>
              </div>
            </div>
            
            <button
              onClick={handleEmergentOAuth}
              className="mt-4 w-full bg-white hover:bg-gray-100 text-gray-800 font-bold py-3 rounded-lg transition duration-300 flex items-center justify-center space-x-2"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285f4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34a853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#fbbc05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#ea4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>Continue with Google</span>
            </button>
          </div>

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
          
          {/* NEW: Having Trouble? Support Block */}
          <div className="mt-6 pt-4 border-t border-white/20 text-center">
            <p className="text-purple-200 text-sm">
              Having trouble signing in?<br />
              Contact{' '}
              <a 
                href="mailto:requestwave@adventuresoundlive.com"
                className="text-purple-300 hover:text-white underline transition duration-300"
              >
                requestwave@adventuresoundlive.com
              </a>{' '}
              for help.
            </p>
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
  );
};

// Utility function for consistent timezone-aware timestamp formatting
const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'Unknown time';
  
  try {
    const date = new Date(timestamp);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.warn('Invalid timestamp:', timestamp);
      return 'Invalid date';
    }
    
    // Get user's timezone for consistent display
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
    // Format date and time in user's local timezone
    const dateOptions = {
      timeZone,
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    };
    
    const timeOptions = {
      timeZone,
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    };
    
    const localDate = date.toLocaleDateString('en-US', dateOptions);
    const localTime = date.toLocaleTimeString('en-US', timeOptions);
    
    return `${localDate} at ${localTime}`;
  } catch (error) {
    console.error('Error formatting timestamp:', error, 'Original:', timestamp);
    return 'Error formatting date';
  }
};

// Utility function for just time (used in On Stage interface)
const formatTime = (timestamp) => {
  if (!timestamp) return 'Unknown';
  
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'Invalid';
    
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return date.toLocaleTimeString('en-US', {
      timeZone,
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  } catch (error) {
    console.error('Error formatting time:', error);
    return 'Error';
  }
};

const MusicianDashboard = () => {
  const { musician, token, logout, setMusician } = useAuth();
  const [activeTab, setActiveTab] = useState('onstage');
  
  // Debug activeTab changes
  useEffect(() => {
    console.log('🏷️ ActiveTab changed to:', activeTab);
  }, [activeTab]);
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

  // LST Upload state
  const [lstFile, setLstFile] = useState(null);
  const [lstPreview, setLstPreview] = useState(null);
  const [lstUploading, setLstUploading] = useState(false);
  const [lstError, setLstError] = useState('');
  const [showLstUpload, setShowLstUpload] = useState(false);
  const [lstAutoEnrich, setLstAutoEnrich] = useState(false);

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

  // NEW: Genre and mood editing state for Add New functionality
  const [showAddGenre, setShowAddGenre] = useState(false);
  const [showAddMood, setShowAddMood] = useState(false);
  const [newGenre, setNewGenre] = useState('');
  const [newMood, setNewMood] = useState('');

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
  const [playlistFilter, setPlaylistFilter] = useState('');
  // Songs tab: 'in' shows songs IN the selected playlist (default), 'not_in' shows songs NOT in it
  const [playlistFilterMode, setPlaylistFilterMode] = useState('in');
  const [moodFilter, setMoodFilter] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [showLearnLater, setShowLearnLater] = useState(false);  // NEW: Learn Later filter toggle
  
  // NEW: Sort functionality state
  const [sortOption, setSortOption] = useState('most-popular'); // 'most-popular', 'alphabetical', 'newest', 'random'
  const [randomSeed, setRandomSeed] = useState(Date.now());
  const [decadeFilter, setDecadeFilter] = useState('');  // NEW: Add decade filter
  const [notesFilter, setNotesFilter] = useState('');  // NEW: Add notes filter
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
  
  // NEW: Redesigned Analytics state
  // Force default to 'alltime' and clear any problematic saved preferences
  const getInitialAnalyticsPeriod = () => {
    const saved = localStorage.getItem('analytics_period');
    // Always default to 'alltime' to avoid user confusion
    if (!saved || saved === 'last7days' || saved === 'last30days') {
      localStorage.setItem('analytics_period', 'alltime');
      return 'alltime';
    }
    return saved;
  };
  
  const [analyticsPeriod, setAnalyticsPeriod] = useState(getInitialAnalyticsPeriod());
  const [topSongsLimit, setTopSongsLimit] = useState(10);
  const [topRequestersLimit, setTopRequestersLimit] = useState(10);
  const [analyticsDays, setAnalyticsDays] = useState(null); // null = all time
  const [requestersData, setRequestersData] = useState([]);
  // NEW: Requesters filter — 'all' | `profile:<id>` | `event:<id>`
  const [requestersFilter, setRequestersFilter] = useState('all');
  // NEW (Sprint 3): show filter applied only to the email export — 'all' or a show id
  const [requestersExportShowId, setRequestersExportShowId] = useState('all');
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // NEW: Show Analytics Dashboard state
  const [showAnalyticsView, setShowAnalyticsView] = useState('detail'); // 'detail' | 'trends'
  const [showAnalyticsProfileId, setShowAnalyticsProfileId] = useState('');
  const [showAnalyticsShowId, setShowAnalyticsShowId] = useState('');
  const [showDetailData, setShowDetailData] = useState(null);
  const [showDetailLoading, setShowDetailLoading] = useState(false);
  const [showTrendsLimit, setShowTrendsLimit] = useState(5);
  const [showTrendsData, setShowTrendsData] = useState(null);
  const [showTrendsLoading, setShowTrendsLoading] = useState(false);

  // NEW: Show management state
  const [currentShow, setCurrentShow] = useState(null);
  const [showStartModal, setShowStartModal] = useState(false);
  const [newShowName, setNewShowName] = useState('');
  const [showPlaylistFilterMode, setShowPlaylistFilterMode] = useState('all'); // 'all' | 'selected'
  const [showEnabledPlaylistIds, setShowEnabledPlaylistIds] = useState([]);
  const [shows, setShows] = useState([]);
  const [groupedRequests, setGroupedRequests] = useState({ unassigned: [], shows: {} });

  // NEW: Unassigned Requests panel state (Requests tab bottom panel)
  const [unassignedRequests, setUnassignedRequests] = useState([]);
  const [unassignedPanelOpen, setUnassignedPanelOpen] = useState(false);
  const [unassignedAssignFor, setUnassignedAssignFor] = useState(null); // request_id currently showing the assign-show dropdown

  // Batch selection state for requests
  const [selectedRequests, setSelectedRequests] = useState(new Set());
  const [showAllRequests, setShowAllRequests] = useState(true); // For collapsible All Requests

  // Requests tab — single/bulk action modals (post-show mobile review)
  const [singleRequestModal, setSingleRequestModal] = useState(null); // request object or null
  const [bulkRequestModalOpen, setBulkRequestModalOpen] = useState(false);

  // Batch selection state for song suggestions
  const [selectedSuggestions, setSelectedSuggestions] = useState(new Set());
  
  // Song Management Dropdown State
  const [showSongManagementDropdown, setShowSongManagementDropdown] = useState(false);
  
  // Mobile Navigation Dropdown State
  const [showMobileNav, setShowMobileNav] = useState(false);
  
  // Quick Start Guide (manual access only)
  const [showQuickStart, setShowQuickStart] = useState(false);
  
  // NEW: Songs Help Modal state
  const [showSongsHelp, setShowSongsHelp] = useState(false);
  
  // NEW: Song deletion confirmation modal state
  const [showDeleteSongModal, setShowDeleteSongModal] = useState(false);
  const [songToDelete, setSongToDelete] = useState(null);
  
  // NEW: Filters visibility state
  const [showFilters, setShowFilters] = useState(false);
  
  // NEW: On Stage tab state
  const [completedSectionCollapsed, setCompletedSectionCollapsed] = useState(false);
  
  // NEW: Auto-fill metadata state
  const [autoFillLoading, setAutoFillLoading] = useState(false);
  
  // NEW: Song suggestions state
  const [songSuggestions, setSongSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionsSectionCollapsed, setSuggestionsSectionCollapsed] = useState(false);
  const [suggestionError, setSuggestionError] = useState('');
  
  // Song picker modal state for suggestion matching
  const [matchingSuggestion, setMatchingSuggestion] = useState(null);
  const [songSearchTerm, setSongSearchTerm] = useState('');
  const [selectedMatchSongId, setSelectedMatchSongId] = useState('');
  
  // NEW: Archived shows state
  const [archivedShowsCollapsed, setArchivedShowsCollapsed] = useState(true);
  
  // NEW: Post-request state for tracking clicks
  const [currentRequestId, setCurrentRequestId] = useState(null);
  const [showPostRequestModal, setShowPostRequestModal] = useState(false);
  
  // NEW: Edit Playlist Songs Modal State  
  const [showEditPlaylistSongsModal, setShowEditPlaylistSongsModal] = useState(false);
  const [editingSongsPlaylist, setEditingSongsPlaylist] = useState(null);
  const [editPlaylistSongs, setEditPlaylistSongs] = useState([]);
  const [editPlaylistLoading, setEditPlaylistLoading] = useState(false);
  const [editPlaylistError, setEditPlaylistError] = useState('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  // NEW: Tip functionality state
  const [showTipModal, setShowTipModal] = useState(false);
  const [tipAmount, setTipAmount] = useState('');
  const [tipMessage, setTipMessage] = useState('');
  const [tipPlatform, setTipPlatform] = useState('paypal'); // 'paypal' or 'venmo'
  const [tipSongId, setTipSongId] = useState(null); // For integrated tips with requests
  const [showZelleModal, setShowZelleModal] = useState(false);
  const [zelleInfo, setZelleInfo] = useState({});
  const [showSocialMediaModal, setShowSocialMediaModal] = useState(false);
  
  // NEW: Batch enrichment for existing songs
  const [batchEnrichLoading, setBatchEnrichLoading] = useState(false);
  
  const [contactForm, setContactForm] = useState({
    name: '',
    email: '',
    message: ''
  });
  const [contactLoading, setContactLoading] = useState(false);
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
  
  // NEW: Enhanced playlist management state
  const [editingPlaylistName, setEditingPlaylistName] = useState('');
  const [playlistToDelete, setPlaylistToDelete] = useState(null);
  const [showPlaylistDeleteConfirmation, setShowPlaylistDeleteConfirmation] = useState(false);
  const [showPlaylistToast, setShowPlaylistToast] = useState(false);
  const [playlistToastMessage, setPlaylistToastMessage] = useState('');
  const [openDropdownId, setOpenDropdownId] = useState(null); // NEW: Track which dropdown is open
  const [playlistsExpanded, setPlaylistsExpanded] = useState(false); // NEW: Track if playlists section is expanded
  
  // Multi-Profile System state
  const [profiles, setProfiles] = useState([]);
  const [showProfileEditor, setShowProfileEditor] = useState(false);
  const [editingProfile, setEditingProfile] = useState(null);
  const [profileForm, setProfileForm] = useState({ name: '', slug: '', active_playlist_ids: ['__all__'], show_tips_in_success_screen: true, show_tips_in_orientation: true, email_capture_mode: 'optional', paypal_username: '', venmo_username: '', cashapp_username: '', zelle_info: '', instagram_username: '', tiktok_username: '', facebook_url: '', spotify_url: '', apple_music_url: '', website: '', bio: '', musician_name: '', design_color_scheme: '', design_artist_photo: '', design_show_year: true, design_show_notes: true });
  const [accountSettingsExpanded, setAccountSettingsExpanded] = useState(false);
  const [accountEmailInput, setAccountEmailInput] = useState('');
  const [accountSlugInput, setAccountSlugInput] = useState('');
  const [savingAccountEmail, setSavingAccountEmail] = useState(false);
  const [savingAccountSlug, setSavingAccountSlug] = useState(false);
  const [accountEmailMsg, setAccountEmailMsg] = useState({ type: '', text: '' });
  const [accountSlugMsg, setAccountSlugMsg] = useState({ type: '', text: '' });
  const [profileFilterId, setProfileFilterId] = useState(''); // For requests tab filter

  // On-Stage profile/event selector (Sprint 2 Prompt 4)
  const [onstageSelection, setOnstageSelection] = useState(() => {
    try { return localStorage.getItem('onstage_selection') || ''; } catch { return ''; }
  });
  const [onstageSelectorExpanded, setOnstageSelectorExpanded] = useState(() => {
    try { return localStorage.getItem('onstage_selector_expanded') === 'true'; } catch { return false; }
  });
  
  // Events (Sprint 2 Prompt 3)
  const EVENT_FORM_DEFAULT = { name: '', slug: '', profile_id: '', event_date: '', active_playlist_ids: ['__all__'], show_tips_in_success_screen: true, show_tips_in_orientation: true, email_capture_mode: 'optional', paypal_username: '', venmo_username: '', cashapp_username: '', zelle_info: '', instagram_username: '', tiktok_username: '', facebook_url: '', spotify_url: '', apple_music_url: '', website: '', bio: '', musician_name: '', copy_from_source: '' };
  const [events, setEvents] = useState([]);
  const [showEventEditor, setShowEventEditor] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [eventForm, setEventForm] = useState(EVENT_FORM_DEFAULT);
  const [eventFilterId, setEventFilterId] = useState('');  // For requests tab filter
  const [showPastEvents, setShowPastEvents] = useState(false);
  const [showMergeDialog, setShowMergeDialog] = useState(false);
  const [mergeForEventId, setMergeForEventId] = useState(null);
  const [mergeDestProfileId, setMergeDestProfileId] = useState('');
  
  // Error toast state for request operations
  const [errorToast, setErrorToast] = useState({ show: false, message: '' });
  
  // Helper function to show error toast
  const showErrorToast = (message, error = null) => {
    // Detect network/offline errors
    let displayMessage = message;
    if (error) {
      if (!navigator.onLine || error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
        displayMessage = 'You appear to be offline. Reconnect and try again.';
      }
    }
    setErrorToast({ show: true, message: displayMessage });
    setTimeout(() => setErrorToast({ show: false, message: '' }), 5000);
  };
  
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
        } else if (tipPlatform === 'cashapp' && response.data.cash_app_link) {
          paymentUrl = response.data.cash_app_link;
        }

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

        if (tipPlatform === 'zelle') {
          // For Zelle, show special modal with copy functionality
          setZelleInfo({
            contact: musician.zelle_email || musician.zelle_phone,
            contactType: musician.zelle_email ? 'email' : 'phone',
            amount: amount,
            message: tipMessage || 'Thanks for the music!'
          });
          setShowTipModal(false);
          setShowZelleModal(true);
          
          // After showing Zelle modal, go directly to social media
          // (This will be handled after Zelle modal is closed)
        } else if (paymentUrl) {
          // Handle PayPal/Venmo/Cash App payment links
          if (tipPlatform === 'venmo' && paymentUrl.startsWith('venmo://')) {
            // For Venmo deep links, implement fallback for desktop browsers
            const venmoMatch = paymentUrl.match(/recipients=([^&]+)/);
            const venmoUsername = venmoMatch ? venmoMatch[1] : 'this musician';
            
            try {
              // Try to open the Venmo app first
              window.location.href = paymentUrl;
              
              // Show brief confirmation message
              setTimeout(() => {
                alert(`Opening Venmo app to send $${amount} tip to @${venmoUsername}!`);
              }, 500);
              
            } catch (error) {
              // Fallback for desktop users
              alert(`To send your $${amount} tip:\n\n1. Open Venmo app on your phone\n2. Search for @${venmoUsername}\n3. Send $${amount} with message: "${tipMessage || 'Thanks for the music!'}"`);
            }
          } else if (tipPlatform === 'cashapp') {
            // Cash App links work universally
            window.open(paymentUrl, '_blank');
            alert(`Opening Cash App to send your $${amount} tip!`);
          } else {
            // PayPal links work universally
            window.open(paymentUrl, '_blank');
            alert(`Opening PayPal to send your $${amount} tip!`);
          }
          
          // Close tip modal and go directly to social media
          setShowTipModal(false);
          // Show social media modal if we were in request flow
          if (tipSongId) {
            setShowSocialMediaModal(true);
          }
        } else {
          const platformName = tipPlatform === 'paypal' ? 'PayPal' : 
                             tipPlatform === 'venmo' ? 'Venmo' : 
                             tipPlatform === 'cashapp' ? 'Cash App' : 'Zelle';
          alert(`${platformName} is not set up for this musician`);
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

  const getTipPresetAmounts = () => [3, 5, 10];

  // Refresh musician profile from backend to ensure state integrity
  const refreshMusicianProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const updatedMusician = response.data;
      setMusician(updatedMusician);
      localStorage.setItem('musician', JSON.stringify(updatedMusician));
      console.log('Musician profile refreshed from backend', {
        current_show_id: updatedMusician.current_show_id,
        current_show_name: updatedMusician.current_show_name
      });
    } catch (error) {
      console.error('Error refreshing musician profile:', error);
    }
  };

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

  const fetchGroupedRequests = async (showId = null) => {
    try {
      // If showId is provided, filter by show; otherwise get all grouped requests
      const url = showId
        ? `${API}/requests/grouped?show_id=${showId}`
        : `${API}/requests/grouped`;
      const response = await axios.get(url, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      setGroupedRequests(response.data);
    } catch (error) {
      console.error('Error fetching grouped requests:', error);
    }
  };

  // NEW: Unassigned Requests panel — fetch + actions
  const fetchUnassignedRequests = async () => {
    try {
      const response = await axios.get(`${API}/requests/unassigned`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setUnassignedRequests(response.data?.requests || []);
    } catch (error) {
      console.error('Error fetching unassigned requests:', error);
    }
  };

  const removeUnassigned = (requestId) => {
    setUnassignedRequests((prev) => prev.filter((r) => r.id !== requestId));
    if (unassignedAssignFor === requestId) setUnassignedAssignFor(null);
  };

  const handleAssignUnassignedToShow = async (requestId, showId) => {
    if (!showId) return;
    try {
      await axios.post(
        `${API}/requests/${requestId}/assign-show`,
        { show_id: showId },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      removeUnassigned(requestId);
      // Optimistically update local requests so show card counts reflect the new
      // assignment immediately, even before the refetch completes.
      setRequests((prev) =>
        Array.isArray(prev)
          ? prev.map((r) => (r.id === requestId ? { ...r, show_id: showId } : r))
          : prev
      );
      // Re-fetch authoritative data so show cards list and grouped views stay in sync.
      await Promise.all([
        fetchRequests(),
        fetchShows(),
        fetchGroupedRequests(),
      ]);
    } catch (error) {
      console.error('Error assigning unassigned request to show:', error);
      alert(error.response?.data?.detail || 'Failed to assign request to show');
    }
  };

  const handleArchiveUnassigned = async (requestId) => {
    try {
      await axios.put(
        `${API}/requests/${requestId}/archive`,
        {},
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      removeUnassigned(requestId);
    } catch (error) {
      console.error('Error archiving unassigned request:', error);
      alert(error.response?.data?.detail || 'Failed to archive request');
    }
  };

  const handleDeleteUnassigned = async (requestId, songTitle) => {
    const confirmMsg = `Delete this request${songTitle ? ` for "${songTitle}"` : ''}? This cannot be undone.`;
    if (!window.confirm(confirmMsg)) return;
    try {
      await axios.delete(`${API}/requests/${requestId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      removeUnassigned(requestId);
    } catch (error) {
      console.error('Error deleting unassigned request:', error);
      alert(error.response?.data?.detail || 'Failed to delete request');
    }
  };



  const handleStartShow = async () => {
    if (!newShowName.trim()) {
      showErrorToast('Please enter a show name');
      return;
    }
    
    // Validate: if "selected" mode, must have at least one playlist
    if (showPlaylistFilterMode === 'selected' && showEnabledPlaylistIds.length === 0) {
      showErrorToast('Please select at least one playlist or choose "All songs"');
      return;
    }

    try {
      // Capture browser timezone to send with show creation
      const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      
      // Sprint 2 Prompt 4: target the On-Stage selected context if present
      const startPayload = {
        name: newShowName,
        timezone: browserTimezone,
        playlist_filter_mode: showPlaylistFilterMode,
        enabled_playlist_ids: showPlaylistFilterMode === 'selected' ? showEnabledPlaylistIds : []
      };
      if (onstageSelection) {
        const [kind, id] = onstageSelection.split(':');
        if (kind === 'profile') startPayload.profile_id = id;
        if (kind === 'event') startPayload.event_id = id;
      }
      
      const response = await axios.post(`${API}/shows/start`, startPayload, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      // Update musician state with new show info from backend response
      if (response.data.musician) {
        setMusician(prev => ({
          ...prev,
          current_show_id: response.data.musician.current_show_id,
          current_show_name: response.data.musician.current_show_name
        }));
        // Update localStorage with new musician state
        const storedMusician = JSON.parse(localStorage.getItem('musician') || '{}');
        localStorage.setItem('musician', JSON.stringify({
          ...storedMusician,
          current_show_id: response.data.musician.current_show_id,
          current_show_name: response.data.musician.current_show_name
        }));
      }

      setShowStartModal(false);
      setNewShowName('');
      setShowPlaylistFilterMode('all');
      setShowEnabledPlaylistIds([]);
      fetchCurrentShow();
      fetchShows();
      // Refresh per-profile / per-event current_show pointers so On-Stage selector reflects the new show
      fetchProfiles();
      fetchEvents();
    } catch (error) {
      console.error('Error starting show:', error);
      showErrorToast(error.response?.data?.detail || 'Error starting show. Please try again.', error);
    }
  };

  // ===== Sprint 2 Prompt 4: Export show requests as CSV =====
  const csvEscape = (v) => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  
  const exportShowRequestsCSV = (show) => {
    const showRequests = requests.filter(r => r.show_id === show.id);
    // Group by song (song_id when present, fallback to title+artist)
    const groups = new Map();
    for (const r of showRequests) {
      const key = r.song_id || `${r.song_title}||${r.song_artist}`;
      if (!groups.has(key)) {
        groups.set(key, {
          title: r.song_title || '',
          artist: r.song_artist || '',
          count: 0,
          requesters: [],
          dedications: [],
          latest: null,
          latestStatus: null,
        });
      }
      const g = groups.get(key);
      g.count += 1;
      if (r.requester_name) g.requesters.push(r.requester_name);
      if (r.dedication && r.dedication.trim()) g.dedications.push(r.dedication.trim());
      const ts = r.created_at ? new Date(r.created_at).getTime() : 0;
      if (g.latest === null || ts > g.latest) {
        g.latest = ts;
        g.latestStatus = r.status || 'pending';
      }
    }
    
    const rows = Array.from(groups.values()).sort((a, b) => b.count - a.count);
    
    const headers = ['Song Title', 'Artist', 'Request Count', 'Requester Names', 'Dedications', 'Status'];
    const body = rows.map(g => [
      csvEscape(g.title),
      csvEscape(g.artist),
      g.count,
      csvEscape(g.requesters.join(', ')),
      csvEscape(g.dedications.join(', ')),
      csvEscape(g.latestStatus || 'pending'),
    ].join(','));
    
    const csv = [headers.join(','), ...body].join('\n') + '\n';
    const safeName = (show.name || 'show').toLowerCase().replace(/[^a-z0-9-_]+/g, '-').replace(/^-+|-+$/g, '') || 'show';
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeName}-requests.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleStopShow = async () => {
    if (!currentShow) return;

    if (confirm(`Stop this show "${currentShow.name}"?`)) {
      try {
        // Sprint 2 Prompt 4: stop scoped to selected context if any
        const stopBody = {};
        if (onstageSelection) {
          const [kind, id] = onstageSelection.split(':');
          if (kind === 'profile') stopBody.profile_id = id;
          if (kind === 'event') stopBody.event_id = id;
        }
        const response = await axios.post(`${API}/shows/stop`, stopBody);

        // Update musician state to clear show info from backend response
        if (response.data.musician) {
          setMusician(prev => ({
            ...prev,
            current_show_id: response.data.musician.current_show_id,
            current_show_name: response.data.musician.current_show_name
          }));
          // Update localStorage with cleared musician state
          const storedMusician = JSON.parse(localStorage.getItem('musician') || '{}');
          localStorage.setItem('musician', JSON.stringify({
            ...storedMusician,
            current_show_id: null,
            current_show_name: null
          }));
        }

        setCurrentShow(null);
        fetchGroupedRequests();
        // Refresh per-profile / per-event current_show pointers so On-Stage selector reflects the change
        fetchProfiles();
        fetchEvents();
      } catch (error) {
        console.error('Error stopping show:', error);
        showErrorToast(error.response?.data?.detail || 'Error stopping show. Please try again.', error);
      }
    }
  };

  // Per-profile stop: used by the Requests tab live banners.
  // Stops only the show running on the given profile, leaving other profiles' shows untouched.
  const handleStopShowForProfile = async (profileId, showName) => {
    if (!profileId) return;
    if (!confirm(`Stop this show "${showName || ''}"?`)) return;
    try {
      const response = await axios.post(`${API}/shows/stop`, { profile_id: profileId });
      if (response.data?.musician) {
        setMusician(prev => ({
          ...prev,
          current_show_id: response.data.musician.current_show_id,
          current_show_name: response.data.musician.current_show_name
        }));
        const storedMusician = JSON.parse(localStorage.getItem('musician') || '{}');
        localStorage.setItem('musician', JSON.stringify({
          ...storedMusician,
          current_show_id: response.data.musician.current_show_id,
          current_show_name: response.data.musician.current_show_name
        }));
      }
      // Refresh everything that depends on per-profile current_show state
      await fetchProfiles();
      await fetchEvents();
      await fetchCurrentShow();
      await fetchShows();
      fetchGroupedRequests();
    } catch (error) {
      console.error('Error stopping show for profile:', error);
      showErrorToast(error.response?.data?.detail || 'Error stopping show. Please try again.', error);
    }
  };

  // NEW: Delete individual request from history
  const handleDeleteRequest = async (requestId, requestTitle) => {
    if (confirm(`Permanently delete request for "${requestTitle}"? This cannot be undone.`)) {
      try {
        await axios.delete(`${API}/requests/${requestId}`);
        fetchGroupedRequests();
      } catch (error) {
        console.error('Error deleting request:', error);
        showErrorToast(error.response?.data?.detail || 'Error deleting request. Please try again.', error);
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
      } catch (error) {
        console.error('Error deleting show:', error);
        showErrorToast(error.response?.data?.detail || 'Error deleting show. Please try again.', error);
      }
    }
  };

  // NEW: Show archive management functions with telemetry
  const handleArchiveShow = async (showId, showName) => {
    // Telemetry: Archive start
    console.log('show_archive_start', {
      show_id: showId,
      show_name: showName,
      timestamp: new Date().toISOString()
    });
    
    if (confirm(`Archive show "${showName}"? The show and its requests will be moved to the archived section.`)) {
      try {
        await axios.put(`${API}/shows/${showId}/archive`);
        fetchGroupedRequests();
        fetchShows();
        fetchCurrentShow(); // Update current show status
        
        // Telemetry: Archive success
        console.log('show_archive_success', {
          show_id: showId,
          show_name: showName,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        console.error('Error archiving show:', error);
        showErrorToast(error.response?.data?.detail || 'Error archiving show. Please try again.', error);
        
        // Telemetry: Archive error
        console.log('show_archive_error', {
          show_id: showId,
          show_name: showName,
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    }
  };

  const handleRestoreShow = async (showId, showName) => {
    // Telemetry: Restore start
    console.log('show_restore_start', {
      show_id: showId,
      show_name: showName,
      timestamp: new Date().toISOString()
    });
    
    if (confirm(`Restore show "${showName}" from archive? It will be moved back to the active shows section.`)) {
      try {
        await axios.put(`${API}/shows/${showId}/restore`);
        fetchGroupedRequests();
        fetchShows();
        fetchCurrentShow(); // Update current show status
        // UI update implies success - no alert needed
        
        // Telemetry: Restore success
        console.log('show_restore_success', {
          show_id: showId,
          show_name: showName,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        console.error('Error restoring show:', error);
        alert('Error restoring show. Please try again.');
        
        // Telemetry: Restore error
        console.log('show_restore_error', {
          show_id: showId,
          show_name: showName,
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    }
  };

  // NEW: Song suggestions management functions
  const fetchSongSuggestions = async (showId = null) => {
    try {
      // If showId is provided, filter by show; otherwise get all suggestions
      const url = showId 
        ? `${API}/song-suggestions?show_id=${showId}`
        : `${API}/song-suggestions`;
      const response = await axios.get(url);
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
    if (confirm(`Delete "${suggestionTitle}"?\n\nThis action cannot be undone.`)) {
      try {
        await axios.delete(`${API}/song-suggestions/${suggestionId}`);
        fetchSongSuggestions();
      } catch (error) {
        console.error('Error deleting suggestion:', error);
        showErrorToast(error.response?.data?.detail || 'Error deleting suggestion. Please try again.', error);
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
      }
    } catch (error) {
      console.error('Error toggling song visibility:', error);
      alert('Error updating song visibility. Please try again.');
    }
  };

  // Toggle Learn Later bookmark for a song. Optimistically updates the local
  // songs array so the bookmark icon flips immediately on all visible cards.
  const handleToggleLearnLater = async (songId) => {
    if (!songId) return;
    // Optimistic update
    setSongs((prev) =>
      prev.map((s) => (s.id === songId ? { ...s, in_learn_later: !s.in_learn_later } : s))
    );
    try {
      const response = await axios.post(
        `${API}/songs/${songId}/learn-later`,
        {},
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      const next = !!response.data?.in_learn_later;
      // Reconcile with the server's authoritative state
      setSongs((prev) =>
        prev.map((s) => (s.id === songId ? { ...s, in_learn_later: next } : s))
      );
    } catch (error) {
      console.error('Error toggling Learn Later:', error);
      // Revert optimistic update on failure
      setSongs((prev) =>
        prev.map((s) => (s.id === songId ? { ...s, in_learn_later: !s.in_learn_later } : s))
      );
    }
  };

  // Compact Learn Later bookmark icon. Filled when in_learn_later=true, outline otherwise.
  // Pass either {songId} (looks up state from songs) or {song} (full object). The
  // icon is intentionally small/unobtrusive — no labels or dialogs.
  const renderLearnLaterBookmark = ({ songId, song, size = 18 }) => {
    const resolvedId = songId || song?.id;
    if (!resolvedId) return null;
    const resolved = song || songs.find((s) => s.id === resolvedId);
    // If the song isn't in our songs catalogue yet (e.g. a request for an
    // unknown song), don't render the bookmark at all rather than guessing.
    if (!resolved) return null;
    const isFilled = !!resolved.in_learn_later;
    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          handleToggleLearnLater(resolvedId);
        }}
        title={isFilled ? 'Remove from Learn Later' : 'Add to Learn Later'}
        aria-label={isFilled ? 'Remove from Learn Later' : 'Add to Learn Later'}
        aria-pressed={isFilled}
        data-testid={`learn-later-bookmark-${resolvedId}`}
        data-in-learn-later={isFilled ? 'true' : 'false'}
        className={`inline-flex items-center justify-center align-middle rounded p-0.5 transition-colors duration-150 ${
          isFilled ? 'text-yellow-400 hover:text-yellow-300' : 'text-gray-400 hover:text-gray-200'
        }`}
      >
        <svg
          width={size}
          height={size}
          viewBox="0 0 24 24"
          fill={isFilled ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
          <text
            x="12"
            y="13"
            textAnchor="middle"
            fontSize="7"
            fontWeight="700"
            fill={isFilled ? '#1f2937' : 'currentColor'}
            stroke="none"
            fontFamily="ui-sans-serif, system-ui, -apple-system, sans-serif"
          >
            LL
          </text>
        </svg>
      </button>
    );
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
    cash_app_username: '',
    zelle_email: '',
    zelle_phone: '',
    // Payment toggles
    paypal_enabled: true,
    venmo_enabled: true,
    cash_app_enabled: true,
    zelle_enabled: true,
    // Feature toggles
    tips_enabled: true,
    requests_enabled: true,
    // Social media fields
    instagram_username: '',
    facebook_username: '',
    tiktok_username: '',
    spotify_artist_url: '',
    apple_music_artist_url: ''
  });
  const [profileError, setProfileError] = useState('');

  // Subscription management state (Freemium model)
  const [subscriptionStatus, setSubscriptionStatus] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('annual'); // Default to annual (better value)
  const [upgrading, setUpgrading] = useState(false);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState('');
  const [deletingAccount, setDeletingAccount] = useState(false);

  // NEW: Account management state for email and password changes
  const [showChangeEmail, setShowChangeEmail] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [changeEmailForm, setChangeEmailForm] = useState({
    new_email: '',
    confirm_email: '',
    current_password: ''
  });
  const [changePasswordForm, setChangePasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [changeEmailError, setChangeEmailError] = useState('');
  const [changePasswordError, setChangePasswordError] = useState('');
  const [changingEmail, setChangingEmail] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  // Design settings state
  const [designSettings, setDesignSettings] = useState({
    color_scheme: 'purple',
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
    // Refresh musician profile from backend to ensure state integrity (prevents stale localStorage)
    refreshMusicianProfile();
    
    fetchSongs();
    fetchRequests();
    fetchSubscriptionStatus();
    fetchSongSuggestions();
    fetchPlaylists(); // NEW: Fetch playlists on dashboard initialization
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

  // Set default show based on musician's current_show_id - backend is source of truth
  useEffect(() => {
    if ((activeTab === 'requests' || activeTab === 'onstage') && shows.length > 0 && musician) {
      // Backend is the single source of truth for active show
      // If current_show_id is null, there is NO active show - do not infer from shows list
      if (musician.current_show_id) {
        const backendCurrentShow = shows.find(show => show.id === musician.current_show_id);
        if (backendCurrentShow) {
          setCurrentShow(backendCurrentShow);
        } else {
          // Show exists in backend but not in local shows list yet - fetch will update
          setCurrentShow(null);
        }
      } else {
        // No active show according to backend - clear it
        setCurrentShow(null);
      }
    }
  }, [activeTab, shows, musician]);

  // On Stage tab: Re-fetch data scoped by show_id when currentShow changes
  // This ensures API-level filtering, not just frontend filtering
  useEffect(() => {
    if (activeTab === 'onstage' && currentShow) {
      // Fetch requests and suggestions scoped to the current show
      fetchRequests(currentShow.id);
      fetchSongSuggestions(currentShow.id);
      if (process.env.NODE_ENV === 'development') {
        console.log('[On Stage] Fetching data scoped to show:', currentShow.id, currentShow.name);
      }
    }
  }, [activeTab, currentShow]);

  useEffect(() => {
    if (showProfile) {
      fetchProfile();
    }
  }, [showProfile]);

  // NEW: Also fetch profile when activeTab is 'profile' to populate the Profile tab form
  useEffect(() => {
    if (activeTab === 'profile') {
      fetchProfile();
      fetchProfiles();
    }
    if (activeTab === 'requests' || activeTab === 'events') {
      // Need events available for badge rendering and event filter dropdown
      fetchEvents();
      if (profiles.length === 0) fetchProfiles();
    }
    if (activeTab === 'requests') {
      // NEW: Refresh orphaned/unassigned requests panel when the Requests tab is opened
      fetchUnassignedRequests();
    }
    if (activeTab === 'onstage') {
      // On-Stage selector needs profiles + events populated
      if (profiles.length === 0) fetchProfiles();
      fetchEvents();
    }
  }, [activeTab]);

  // On-Stage selector: persist + react to changes (Sprint 2 Prompt 4)
  useEffect(() => {
    try { if (onstageSelection) localStorage.setItem('onstage_selection', onstageSelection); } catch {}
  }, [onstageSelection]);
  useEffect(() => {
    try { localStorage.setItem('onstage_selector_expanded', String(onstageSelectorExpanded)); } catch {}
  }, [onstageSelectorExpanded]);

  // Initialize selection to default profile on first On-Stage activation
  useEffect(() => {
    if (activeTab !== 'onstage') return;
    if (onstageSelection) return;
    const dp = profiles.find(p => p.is_default);
    if (dp) setOnstageSelection(`profile:${dp.id}`);
  }, [activeTab, profiles, onstageSelection]);

  // When selection changes, point currentShow at the selected context's show
  useEffect(() => {
    if (activeTab !== 'onstage') return;
    if (!onstageSelection) return;
    const [kind, id] = onstageSelection.split(':');
    let ref = null;
    if (kind === 'profile') ref = profiles.find(p => p.id === id);
    if (kind === 'event') ref = events.find(ev => ev.id === id);
    if (ref?.current_show_id) {
      setCurrentShow({ id: ref.current_show_id, name: ref.current_show_name });
    } else {
      setCurrentShow(null);
    }
  }, [activeTab, onstageSelection, profiles, events]);

  // Requests tab — auto-dismiss bulk modal when fewer than 2 cards are selected
  useEffect(() => {
    if (selectedRequests.size < 2 && bulkRequestModalOpen) {
      setBulkRequestModalOpen(false);
    }
  }, [selectedRequests, bulkRequestModalOpen]);

  // NEW: Handle URL parameters for sort option
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sortParam = urlParams.get('sort');
    if (sortParam && ['most-popular', 'alphabetical', 'newest', 'random'].includes(sortParam)) {
      setSortOption(sortParam);
      if (sortParam === 'random') {
        setRandomSeed(Date.now());
      }
    }
  }, []);

  // NEW: Update URL when sort option changes
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (sortOption === 'most-popular') {
      urlParams.delete('sort');
    } else {
      urlParams.set('sort', sortOption);
    }
    
    const newUrl = urlParams.toString() ? 
      `${window.location.pathname}?${urlParams.toString()}` : 
      window.location.pathname;
    window.history.replaceState({}, '', newUrl);
  }, [sortOption]);

  // NEW: Fetch playlists when subscription status changes
  useEffect(() => {
    if (subscriptionStatus) {
      fetchPlaylists();
    }
  }, [subscriptionStatus]);

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
        cash_app_username: musician.cash_app_username || '',
        zelle_email: musician.zelle_email || '',
        zelle_phone: musician.zelle_phone || '',
        // Payment toggles
        paypal_enabled: musician.paypal_enabled !== false,
        venmo_enabled: musician.venmo_enabled !== false,
        cash_app_enabled: musician.cash_app_enabled !== false,
        zelle_enabled: musician.zelle_enabled !== false,
        // Feature toggles
        tips_enabled: musician.tips_enabled !== false,
        requests_enabled: musician.requests_enabled !== false,
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

  // Close song management dropdown when clicking outside or pressing Escape
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showSongManagementDropdown && !event.target.closest('.song-management-dropdown')) {
        setShowSongManagementDropdown(false);
      }
      if (showMobileNav && !event.target.closest('.mobile-nav-dropdown')) {
        setShowMobileNav(false);
      }
    };

    const handleEscapeKey = (event) => {
      if (event.key === 'Escape') {
        if (showSongManagementDropdown) setShowSongManagementDropdown(false);
        if (showMobileNav) setShowMobileNav(false);
      }
    };

    if (showSongManagementDropdown || showMobileNav) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscapeKey);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscapeKey);
    };
  }, [showSongManagementDropdown, showMobileNav]);

  const fetchSongs = async () => {
    try {
      const response = await axios.get(`${API}/songs?sort_by=${sortBy}`);
      setSongs(response.data);
      
      // Extract available genres and moods from loaded songs - UPDATE FILTER OPTIONS
      setTimeout(() => {
        // Update filterOptions with extracted data from songs
        const allGenres = new Set();
        const allMoods = new Set();
        
        response.data.forEach(song => {
          if (song.genres && Array.isArray(song.genres)) {
            song.genres.forEach(genre => {
              if (genre && genre.trim()) {
                allGenres.add(genre.trim());
              }
            });
          }
          if (song.moods && Array.isArray(song.moods)) {
            song.moods.forEach(mood => {
              if (mood && mood.trim()) {
                allMoods.add(mood.trim());
              }
            });
          }
        });
        
        setFilterOptions(prev => ({
          ...prev,
          genres: Array.from(allGenres).sort(),
          moods: Array.from(allMoods).sort()
        }));
      }, 100); // Small delay to ensure songs state is updated
      
    } catch (error) {
      console.error('Error fetching songs:', error);
    }
  };

  // NEW: Fetch filter options for musician dashboard
  const fetchFilterOptions = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${musician.slug}/filters`);
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

  const fetchRequests = async (showId = null) => {
    try {
      // If showId is provided, filter by show; otherwise get all requests
      const url = showId
        ? `${API}/requests/musician/${musician.id}?show_id=${showId}`
        : `${API}/requests/musician/${musician.id}`;
      const response = await axios.get(url);
      setRequests(response.data.requests); // Updated to handle new response format
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
    setSongToDelete(songId);
    setShowDeleteSongModal(true);
  };

  const confirmDeleteSong = async () => {
    if (!songToDelete) return;
    
    try {
      console.log('Deleting song with ID:', songToDelete);
      await axios.delete(`${API}/songs/${songToDelete}`);
      fetchSongs();
      console.log('Song deleted successfully');
      setShowDeleteSongModal(false);
      setSongToDelete(null);
    } catch (error) {
      console.error('Error deleting song:', error);
      alert(`Error deleting song: ${error.response?.data?.detail || error.message}`);
      setShowDeleteSongModal(false);
      setSongToDelete(null);
    }
  };

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`);
      setProfile(response.data);
    } catch (error) {
      console.error('Error fetching profile:', error);
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
        // Payment usernames
        paypal_username: response.data.paypal_username,
        venmo_username: response.data.venmo_username,
        cash_app_username: response.data.cash_app_username,
        zelle_email: response.data.zelle_email,
        zelle_phone: response.data.zelle_phone,
        // Payment toggles
        paypal_enabled: response.data.paypal_enabled,
        venmo_enabled: response.data.venmo_enabled,
        cash_app_enabled: response.data.cash_app_enabled,
        zelle_enabled: response.data.zelle_enabled,
        // Feature toggles
        tips_enabled: response.data.tips_enabled,
        requests_enabled: response.data.requests_enabled,
        // Social media
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

  // Multi-Profile CRUD functions
  const fetchProfiles = async () => {
    try {
      const response = await axios.get(`${API}/profiles`);
      setProfiles(response.data);
    } catch (error) {
      console.error('Error fetching profiles:', error);
    }
  };

  const handleCreateProfile = async () => {
    try {
      const response = await axios.post(`${API}/profiles`, profileForm);
      setProfiles([...profiles, response.data]);
      setShowProfileEditor(false);
      setProfileForm({ name: '', slug: '', active_playlist_ids: ['__all__'], show_tips_in_success_screen: true, show_tips_in_orientation: true, email_capture_mode: 'optional', paypal_username: '', venmo_username: '', cashapp_username: '', zelle_info: '', instagram_username: '', tiktok_username: '', facebook_url: '', spotify_url: '', apple_music_url: '', website: '', bio: '', musician_name: '', design_color_scheme: '', design_artist_photo: '', design_show_year: true, design_show_notes: true });
    } catch (error) {
      alert(error.response?.data?.detail || 'Error creating profile');
    }
  };

  const handleUpdateProfileById = async () => {
    if (!editingProfile) return;
    try {
      const response = await axios.put(`${API}/profiles/${editingProfile.id}`, profileForm);
      setProfiles(profiles.map(p => p.id === editingProfile.id ? response.data : p));
      setShowProfileEditor(false);
      setEditingProfile(null);
      setProfileForm({ name: '', slug: '', active_playlist_ids: ['__all__'], show_tips_in_success_screen: true, show_tips_in_orientation: true, email_capture_mode: 'optional', paypal_username: '', venmo_username: '', cashapp_username: '', zelle_info: '', instagram_username: '', tiktok_username: '', facebook_url: '', spotify_url: '', apple_music_url: '', website: '', bio: '', musician_name: '', design_color_scheme: '', design_artist_photo: '', design_show_year: true, design_show_notes: true });
    } catch (error) {
      alert(error.response?.data?.detail || 'Error updating profile');
    }
  };

  const handleDeleteProfile = async (profileId) => {
    if (!window.confirm('Delete this profile? This cannot be undone.')) return;
    try {
      await axios.delete(`${API}/profiles/${profileId}`);
      setProfiles(profiles.filter(p => p.id !== profileId));
    } catch (error) {
      alert(error.response?.data?.detail || 'Error deleting profile');
    }
  };

  // ===== Events (Sprint 2 Prompt 3) =====
  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${API}/events`);
      setEvents(response.data || []);
    } catch (error) {
      console.error('fetchEvents failed', error);
    }
  };

  const slugifyForEvent = (s) => (s || '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);

  const openEventEditor = (eventToEdit = null) => {
    if (eventToEdit) {
      setEditingEvent(eventToEdit);
      setEventForm({
        name: eventToEdit.name || '',
        slug: eventToEdit.slug || '',
        profile_id: eventToEdit.profile_id || '',
        event_date: eventToEdit.event_date ? String(eventToEdit.event_date).slice(0, 10) : '',
        active_playlist_ids: eventToEdit.active_playlist_ids || ['__all__'],
        show_tips_in_success_screen: eventToEdit.show_tips_in_success_screen !== false,
        show_tips_in_orientation: eventToEdit.show_tips_in_orientation !== false,
        email_capture_mode: eventToEdit.email_capture_mode || 'optional',
        paypal_username: eventToEdit.paypal_username || '',
        venmo_username: eventToEdit.venmo_username || '',
        cashapp_username: eventToEdit.cashapp_username || '',
        zelle_info: eventToEdit.zelle_info || '',
        instagram_username: eventToEdit.instagram_username || '',
        tiktok_username: eventToEdit.tiktok_username || '',
        facebook_url: eventToEdit.facebook_url || '',
        spotify_url: eventToEdit.spotify_url || '',
        apple_music_url: eventToEdit.apple_music_url || '',
        website: eventToEdit.website || '',
        bio: eventToEdit.bio || '',
        musician_name: eventToEdit.musician_name || '',
        copy_from_source: '',
      });
    } else {
      setEditingEvent(null);
      setEventForm({ ...EVENT_FORM_DEFAULT, profile_id: profiles.find(p => p.is_default)?.id || profiles[0]?.id || '' });
    }
    setShowEventEditor(true);
  };

  const handleEventFormSubmit = async (e) => {
    e.preventDefault();
    try {
      const cleanedSlug = slugifyForEvent(eventForm.slug || eventForm.name);
      if (!cleanedSlug) {
        showErrorToast('Slug is required');
        return;
      }
      if (!eventForm.profile_id) {
        showErrorToast('Please choose a parent profile');
        return;
      }
      // Profile-change confirmation when editing
      if (editingEvent && eventForm.profile_id !== editingEvent.profile_id) {
        const confirmed = window.confirm(
          'This will change your audience URL. Any links or QR codes already shared will stop working. Are you sure?'
        );
        if (!confirmed) return;
      }
      const payload = {
        ...eventForm,
        slug: cleanedSlug,
        event_date: eventForm.event_date ? eventForm.event_date : null,
      };
      // Translate copy_from_source select value to API field
      if (payload.copy_from_source) {
        if (payload.copy_from_source.startsWith('profile:')) {
          payload.copy_from_profile_id = payload.copy_from_source.split(':')[1];
        } else if (payload.copy_from_source.startsWith('event:')) {
          payload.copy_from_event_id = payload.copy_from_source.split(':')[1];
        }
      }
      delete payload.copy_from_source;

      if (editingEvent) {
        const response = await axios.put(`${API}/events/${editingEvent.id}`, payload);
        setEvents(events.map(ev => ev.id === editingEvent.id ? response.data : ev));
      } else {
        const response = await axios.post(`${API}/events`, payload);
        setEvents([response.data, ...events]);
      }
      setShowEventEditor(false);
      setEditingEvent(null);
    } catch (err) {
      showErrorToast(err.response?.data?.detail || 'Error saving event');
    }
  };

  const handleDeleteEvent = async (event) => {
    if (event.status !== 'upcoming') {
      showErrorToast('Only upcoming events can be deleted');
      return;
    }
    if (!window.confirm(`Delete event "${event.name}"? This cannot be undone.`)) return;
    try {
      await axios.delete(`${API}/events/${event.id}`);
      setEvents(events.filter(ev => ev.id !== event.id));
    } catch (err) {
      showErrorToast(err.response?.data?.detail || 'Error deleting event');
    }
  };

  const handleEventStatusChange = async (event, newStatus, mergeIntoProfileId = null) => {
    try {
      const payload = { status: newStatus };
      if (mergeIntoProfileId) payload.merge_into_profile_id = mergeIntoProfileId;
      const response = await axios.put(`${API}/events/${event.id}/status`, payload);
      setEvents(events.map(ev => ev.id === event.id ? { ...ev, ...response.data } : ev));
    } catch (err) {
      showErrorToast(err.response?.data?.detail || 'Error updating event status');
    }
  };

  const buildEventUrl = (event) => {
    const profile = profiles.find(p => p.id === event.profile_id);
    if (!profile || !musician) return '';
    return `${AUDIENCE_BASE_URL}/musician/${musician.slug}/${profile.slug}/${event.slug}`;
  };

  const openProfileEditor = (profileToEdit = null) => {
    if (profileToEdit) {
      setEditingProfile(profileToEdit);
      setProfileForm({
        name: profileToEdit.name,
        slug: profileToEdit.slug,
        active_playlist_ids: profileToEdit.active_playlist_ids || [],
        show_tips_in_success_screen: profileToEdit.show_tips_in_success_screen !== false,
        show_tips_in_orientation: profileToEdit.show_tips_in_orientation !== false,
        email_capture_mode: profileToEdit.email_capture_mode || 'optional',
        paypal_username: profileToEdit.paypal_username || '',
        venmo_username: profileToEdit.venmo_username || '',
        cashapp_username: profileToEdit.cashapp_username || '',
        zelle_info: profileToEdit.zelle_info || '',
        instagram_username: profileToEdit.instagram_username || '',
        tiktok_username: profileToEdit.tiktok_username || '',
        facebook_url: profileToEdit.facebook_url || '',
        spotify_url: profileToEdit.spotify_url || '',
        apple_music_url: profileToEdit.apple_music_url || '',
        website: profileToEdit.website || '',
        bio: profileToEdit.bio || '',
        musician_name: profileToEdit.musician_name || '',
        design_color_scheme: profileToEdit.design_color_scheme || '',
        design_artist_photo: profileToEdit.design_artist_photo || '',
        design_show_year: profileToEdit.design_show_year !== false,
        design_show_notes: profileToEdit.design_show_notes !== false,
      });
    } else {
      setEditingProfile(null);
      setProfileForm({ name: '', slug: '', active_playlist_ids: ['__all__'], show_tips_in_success_screen: true, show_tips_in_orientation: true, email_capture_mode: 'optional', paypal_username: '', venmo_username: '', cashapp_username: '', zelle_info: '', instagram_username: '', tiktok_username: '', facebook_url: '', spotify_url: '', apple_music_url: '', website: '', bio: '', musician_name: '', design_color_scheme: '', design_artist_photo: '', design_show_year: true, design_show_notes: true });
    }
    setShowProfileEditor(true);
  };

  const generateSlugFromName = (name) => {
    return name.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/[\s]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
  };

  const handleProfilePhotoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        alert('Image size must be less than 2MB');
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        setProfileForm(prev => ({ ...prev, design_artist_photo: event.target.result }));
      };
      reader.readAsDataURL(file);
    }
  };

  const fetchSubscriptionStatus = async () => {
    if (!BILLING_ENABLED) {
      // In free mode, set everyone as having pro access
      setSubscriptionStatus({
        plan: "pro",
        status: "active",
        trial_eligible: false,
        trial_end: null,
        audience_link_active: true,
        has_pro_access: true,
        next_invoice_date: null
      });
      return;
    }
    
    try {
      const response = await axios.get(`${API}/subscription/status`);
      setSubscriptionStatus(response.data);
    } catch (error) {
      console.error('Error fetching subscription status:', error);
    }
  };

  const handleUpgrade = async () => {
    if (!BILLING_ENABLED) {
      alert('Billing is disabled in Free mode');
      return;
    }
    
    setUpgrading(true);
    try {
      const plan = selectedPlan; // 'monthly' or 'annual'
      
      const response = await axios.post(`${API}/subscription/checkout`, {
        plan: plan,
        success_url: `${window.location.origin}/dashboard?tab=subscription&session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${window.location.origin}/dashboard?tab=subscription`
      });
      
      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url;
      }
    } catch (error) {
      console.error('Error creating checkout session:', error);
      alert('Error processing subscription. Please try again.');
    } finally {
      setUpgrading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!BILLING_ENABLED) {
      alert('Billing is disabled in Free mode');
      return;
    }
    
    if (window.confirm('Are you sure you want to cancel your subscription? Your audience link will be deactivated, but your songs and request history will remain saved.')) {
      try {
        await axios.post(`${API}/subscription/cancel`);
        alert('Subscription canceled. Your audience link has been deactivated.');
        fetchSubscriptionStatus();
      } catch (error) {
        console.error('Error canceling subscription:', error);
        alert('Error canceling subscription. Please try again.');
      }
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmationText !== 'DELETE') {
      alert('Please type "DELETE" to confirm account deletion.');
      return;
    }

    setDeletingAccount(true);
    try {
      await axios.delete(`${API}/account/delete`, {
        data: { confirmation_text: deleteConfirmationText }
      });
      alert('Account deleted successfully. You will be logged out.');
      logout();
    } catch (error) {
      console.error('Error deleting account:', error);
      alert('Error deleting account. Please try again.');
    } finally {
      setDeletingAccount(false);
      setShowDeleteConfirmation(false);
      setDeleteConfirmationText('');
    }
  };

  // NEW: Account management handler functions
  const handleChangeEmail = async () => {
    setChangeEmailError('');
    
    // Validation
    if (!changeEmailForm.new_email || !changeEmailForm.confirm_email || !changeEmailForm.current_password) {
      setChangeEmailError('All fields are required');
      return;
    }
    
    if (changeEmailForm.new_email !== changeEmailForm.confirm_email) {
      setChangeEmailError('Email addresses do not match');
      return;
    }
    
    if (changeEmailForm.new_email === musician.email) {
      setChangeEmailError('New email must be different from current email');
      return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(changeEmailForm.new_email)) {
      setChangeEmailError('Please enter a valid email address');
      return;
    }
    
    setChangingEmail(true);
    
    try {
      await axios.put(`${API}/profile/change-email`, {
        new_email: changeEmailForm.new_email,
        current_password: changeEmailForm.current_password
      });
      
      // Update local musician data
      const updatedMusician = { ...musician, email: changeEmailForm.new_email };
      setMusician(updatedMusician);
      localStorage.setItem('musician', JSON.stringify(updatedMusician));
      
      // Reset form and close
      setChangeEmailForm({ new_email: '', confirm_email: '', current_password: '' });
      setShowChangeEmail(false);
      
      alert('Email address updated successfully!');
    } catch (error) {
      console.error('Error changing email:', error);
      setChangeEmailError(error.response?.data?.detail || 'Error updating email address');
    } finally {
      setChangingEmail(false);
    }
  };

  const handleChangePassword = async () => {
    setChangePasswordError('');
    
    // Validation
    if (!changePasswordForm.current_password || !changePasswordForm.new_password || !changePasswordForm.confirm_password) {
      setChangePasswordError('All fields are required');
      return;
    }
    
    if (changePasswordForm.new_password !== changePasswordForm.confirm_password) {
      setChangePasswordError('New passwords do not match');
      return;
    }
    
    if (changePasswordForm.new_password.length < 8) {
      setChangePasswordError('New password must be at least 8 characters long');
      return;
    }
    
    if (!/[A-Za-z]/.test(changePasswordForm.new_password)) {
      setChangePasswordError('New password must contain at least one letter');
      return;
    }
    
    if (!/\d/.test(changePasswordForm.new_password)) {
      setChangePasswordError('New password must contain at least one number');
      return;
    }
    
    if (changePasswordForm.current_password === changePasswordForm.new_password) {
      setChangePasswordError('New password must be different from current password');
      return;
    }
    
    setChangingPassword(true);
    
    try {
      await axios.put(`${API}/profile/change-password`, {
        current_password: changePasswordForm.current_password,
        new_password: changePasswordForm.new_password
      });
      
      // Reset form and close
      setChangePasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      setShowChangePassword(false);
      
      alert('Password updated successfully!');
    } catch (error) {
      console.error('Error changing password:', error);
      setChangePasswordError(error.response?.data?.detail || 'Error updating password');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleSaveAccountEmail = async () => {
    setAccountEmailMsg({ type: '', text: '' });
    const trimmed = (accountEmailInput || '').trim().toLowerCase();
    if (!trimmed) {
      setAccountEmailMsg({ type: 'error', text: 'Email is required' });
      return;
    }
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(trimmed)) {
      setAccountEmailMsg({ type: 'error', text: 'Invalid email format' });
      return;
    }
    if (musician && trimmed === (musician.email || '').toLowerCase()) {
      setAccountEmailMsg({ type: 'error', text: 'This is already your email' });
      return;
    }
    setSavingAccountEmail(true);
    try {
      await axios.put(`${API}/account/email`, { new_email: trimmed });
      setMusician({ ...musician, email: trimmed });
      if (profile) setProfile({ ...profile, email: trimmed });
      setAccountEmailMsg({ type: 'success', text: 'Email updated' });
    } catch (error) {
      setAccountEmailMsg({ type: 'error', text: error.response?.data?.detail || 'Error updating email' });
    } finally {
      setSavingAccountEmail(false);
    }
  };

  const handleSaveAccountSlug = async () => {
    setAccountSlugMsg({ type: '', text: '' });
    const trimmed = (accountSlugInput || '').trim().toLowerCase();
    if (!trimmed) {
      setAccountSlugMsg({ type: 'error', text: 'Slug is required' });
      return;
    }
    if (!/^[a-z0-9-]+$/.test(trimmed)) {
      setAccountSlugMsg({ type: 'error', text: 'Use only lowercase letters, numbers, and hyphens' });
      return;
    }
    if (trimmed.length < 2 || trimmed.length > 60) {
      setAccountSlugMsg({ type: 'error', text: 'Slug must be 2–60 characters' });
      return;
    }
    if (trimmed.startsWith('-') || trimmed.endsWith('-')) {
      setAccountSlugMsg({ type: 'error', text: 'Slug cannot start or end with a hyphen' });
      return;
    }
    if (musician && trimmed === musician.slug) {
      setAccountSlugMsg({ type: 'error', text: 'This is already your slug' });
      return;
    }
    setSavingAccountSlug(true);
    try {
      await axios.put(`${API}/account/slug`, { new_slug: trimmed });
      setMusician({ ...musician, slug: trimmed });
      if (profile) setProfile({ ...profile, slug: trimmed });
      setAccountSlugMsg({ type: 'success', text: 'Master slug updated' });
    } catch (error) {
      setAccountSlugMsg({ type: 'error', text: error.response?.data?.detail || 'Error updating slug' });
    } finally {
      setSavingAccountSlug(false);
    }
  };

  const checkPaymentStatus = async (sessionId) => {
    try {
      const response = await axios.get(`${API}/subscription/checkout/status/${sessionId}`);
      if (response.data.payment_status === 'paid') {
        alert('Payment successful! Your audience link is now active.');
        fetchSubscriptionStatus();
        // Remove session_id from URL
        window.history.replaceState({}, document.title, window.location.pathname);
      } else if (response.data.status === 'expired') {
        alert('Payment session expired. Please try again.');
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
      
      // Genre filter - including special "No Genre" option
      const genreMatch = genreFilter === '' || 
        (genreFilter === '__NO_GENRE__' 
          ? (!song.genres || song.genres.length === 0 || song.genres.every(g => !g || g.trim() === ''))
          : song.genres.some(genre => genre.toLowerCase().includes(genreFilter.toLowerCase())));
      
      // Playlist filter (client-side) — supports 'in' and 'not_in' modes
      const playlistMatch = playlistFilter === '' || (() => {
        // Find the selected playlist
        const selectedPlaylist = playlists.find(p => p.id === playlistFilter);
        if (!selectedPlaylist || !selectedPlaylist.song_ids) return false;
        const isInPlaylist = selectedPlaylist.song_ids.includes(song.id);
        return playlistFilterMode === 'not_in' ? !isInPlaylist : isInPlaylist;
      })();
      
      // Mood filter - including special "No Mood" option
      const moodMatch = moodFilter === '' ||
        (moodFilter === '__NO_MOOD__'
          ? (!song.moods || song.moods.length === 0 || song.moods.every(m => !m || m.trim() === ''))
          : song.moods.some(mood => mood.toLowerCase().includes(moodFilter.toLowerCase())));
      
      // Year filter - including special "No Year" option
      const yearMatch = yearFilter === '' || 
        (yearFilter === '__NO_YEAR__'
          ? (!song.year || song.year === '' || song.year === null || song.year === undefined)
          : (song.year && song.year.toString() === yearFilter));
      
      // NEW: Decade filter
      const decadeMatch = decadeFilter === '' || 
        (song.decade && song.decade === decadeFilter);
      
      // NEW: Notes filter
      const notesMatch = notesFilter === '' ||
        (song.notes && song.notes.toLowerCase().includes(notesFilter.toLowerCase()));
      
      return searchMatch && genreMatch && playlistMatch && moodMatch && yearMatch && decadeMatch && notesMatch;
    });
    
    // NEW: Apply sorting
    filtered = applySorting(filtered);
    
    setFilteredSongs(filtered);
  };

  // NEW: Sorting function
  const applySorting = (songsToSort) => {
    const sorted = [...songsToSort];
    
    switch (sortOption) {
      case 'most-popular':
        return sorted.sort((a, b) => (b.unique_show_count || 0) - (a.unique_show_count || 0));
      case 'alphabetical':
        return sorted.sort((a, b) => a.title.localeCompare(b.title));
      case 'newest':
        return sorted.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      case 'random':
        // Use seeded random for consistent results
        const seededRandom = (seed) => {
          const x = Math.sin(seed) * 10000;
          return x - Math.floor(x);
        };
        return sorted.sort((a, b) => {
          const seedA = (a.id.charCodeAt(0) + randomSeed) % 1000;
          const seedB = (b.id.charCodeAt(0) + randomSeed) % 1000;
          return seededRandom(seedA) - seededRandom(seedB);
        });
      default:
        return sorted;
    }
  };

  // NEW: Shuffle function for random sort
  const handleShuffle = () => {
    setRandomSeed(Date.now());
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
    
    // Helper function to get playlists for a song (pipe-delimited for CSV import compatibility)
    const getSongPlaylists = (songId) => {
      return playlists
        .filter(playlist => playlist.song_ids && playlist.song_ids.includes(songId))
        .map(playlist => playlist.name)
        .join('|');
    };
    
    // Helper function to properly escape CSV fields
    const escapeCSVField = (field) => {
      // Convert to string and handle null/undefined
      const str = String(field ?? '');
      // Escape double quotes by doubling them
      const escaped = str.replace(/"/g, '""');
      // Always wrap in quotes to handle commas, newlines, and special characters
      return `"${escaped}"`;
    };
    
    const csvContent = [
      ['Title', 'Artist', 'Genres', 'Moods', 'Year', 'Playlists', 'Notes'],
      ...exportSongs.map(song => [
        song.title,
        song.artist,
        song.genres.join(', '),
        song.moods.join(', '),
        song.year || '',
        getSongPlaylists(song.id),
        song.notes || ''
      ])
    ].map(row => row.map(field => escapeCSVField(field)).join(',')).join('\n');

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
      const deleteResults = await Promise.allSettled(
        Array.from(selectedSongs).map(async (songId) => {
          try {
            await axios.delete(`${API}/songs/${songId}`);
            return { songId, success: true };
          } catch (error) {
            console.error(`Failed to delete song ${songId}:`, error);
            return { songId, success: false, error: error.response?.data?.detail || error.message };
          }
        })
      );

      const successful = deleteResults.filter(result => result.status === 'fulfilled' && result.value.success);
      const failed = deleteResults.filter(result => result.status === 'rejected' || (result.status === 'fulfilled' && !result.value.success));
      
      fetchSongs();
      setSelectedSongs(new Set());
      
      if (failed.length === 0) {
        alert(`Successfully deleted ${successful.length} songs`);
      } else if (successful.length === 0) {
        alert(`Failed to delete all ${failed.length} songs. Please check your connection and try again.`);
      } else {
        alert(`Partially completed: ${successful.length} songs deleted successfully, ${failed.length} songs failed. Please try deleting the failed songs individually if needed.`);
      }
    } catch (error) {
      console.error('Error in batch deletion process:', error);
      alert('Error processing song deletions. Please try again.');
    }
  };

  // Update filtered songs when songs or filters change
  React.useEffect(() => {
    filterSongs();
  }, [songs, songFilter, genreFilter, playlistFilter, playlistFilterMode, moodFilter, yearFilter, decadeFilter, notesFilter, sortOption, randomSeed]);

  // Reset playlist filter mode to 'in' whenever the selected playlist changes
  React.useEffect(() => {
    setPlaylistFilterMode('in');
  }, [playlistFilter]);

  // NEW: Refetch songs and filter options when sort order changes
  React.useEffect(() => {
    if (musician) {
      fetchSongs();
      fetchFilterOptions();
    }
  }, [sortBy, musician]);

  useEffect(() => {
    if (musician) {
      fetchSongs();
      fetchFilterOptions();
      fetchRequests();
      fetchDesignSettings();
    }
  }, [musician]);

  // NEW: Phase 3 - Analytics functions
  const fetchAnalytics = async (daysOverride = undefined) => {
    // Use override if provided, otherwise use state
    const daysToUse = daysOverride !== undefined ? daysOverride : analyticsDays;
    console.log('🔍 fetchAnalytics called with days:', daysToUse, '(override:', daysOverride, ', state:', analyticsDays, ')');
    setAnalyticsLoading(true);
    try {
      // Build URL with days parameter only if not null (for all time)
      const url = daysToUse !== null 
        ? `${API}/analytics/daily?days=${daysToUse}`
        : `${API}/analytics/daily`; // No days parameter = all time
      console.log('🌐 Making analytics request to:', url);
      const response = await axios.get(url, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      console.log('✅ Analytics response received:', response.data);
      setAnalyticsData(response.data);
      console.log('📊 Analytics data set successfully');
    } catch (error) {
      console.error('❌ Error fetching analytics:', error);
      console.error('❌ Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
    } finally {
      setAnalyticsLoading(false);
      console.log('🏁 Analytics loading completed');
    }
  };

  // Build the {profile_id, event_id} query params from a filter token like
  // 'all', 'profile:<id>', or 'event:<id>'. Returns {} when no filter is set.
  const buildRequestersFilterParams = (filterToken) => {
    if (!filterToken || filterToken === 'all') return {};
    const [kind, id] = filterToken.split(':');
    if (!id) return {};
    if (kind === 'profile') return { profile_id: id };
    if (kind === 'event') return { event_id: id };
    return {};
  };

  const fetchRequesters = async (filterToken = requestersFilter) => {
    try {
      const params = buildRequestersFilterParams(filterToken);
      const response = await axios.get(`${API}/analytics/requesters`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        params
      });
      setRequestersData(response.data.requesters);
    } catch (error) {
      console.error('Error fetching requesters:', error);
    }
  };

  const exportRequestersCSV = async () => {
    try {
      const params = buildRequestersFilterParams(requestersFilter);
      const response = await axios.get(`${API}/analytics/export-requesters`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob',
        params
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

  // NEW: Show Analytics Dashboard fetchers
  const fetchShowDetailAnalytics = async (showId) => {
    if (!showId) {
      setShowDetailData(null);
      return;
    }
    setShowDetailLoading(true);
    try {
      const response = await axios.get(`${API}/analytics/show-detail`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        params: { show_id: showId },
      });
      setShowDetailData(response.data);
    } catch (error) {
      console.error('Error fetching show detail analytics:', error);
      setShowDetailData(null);
    } finally {
      setShowDetailLoading(false);
    }
  };

  const fetchShowTrendsAnalytics = async (profileId, limit) => {
    if (!profileId) {
      setShowTrendsData(null);
      return;
    }
    setShowTrendsLoading(true);
    try {
      const response = await axios.get(`${API}/analytics/show-trends`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        params: { profile_id: profileId, limit },
      });
      setShowTrendsData(response.data);
    } catch (error) {
      console.error('Error fetching show trends analytics:', error);
      setShowTrendsData(null);
    } finally {
      setShowTrendsLoading(false);
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

  // Load saved analytics period preference
  useEffect(() => {
    const savedPeriod = localStorage.getItem('analytics_period');
    if (savedPeriod) {
      setAnalyticsPeriod(savedPeriod);
    }
  }, []);

  // Handle analytics data fetching when tab becomes active
  useEffect(() => {
    console.log('🔄 Analytics useEffect triggered', { activeTab, analyticsPeriod });
    if (activeTab === 'analytics') {
      console.log('✅ Analytics tab is active, fetching data...');
      
      const periodToDaysMap = {
        'today': 1,
        'last7days': 7,
        'last30days': 30,
        'last3months': 90,
        'lastyear': 365,
        'alltime': null
      };
      
      const days = periodToDaysMap[analyticsPeriod];
      setAnalyticsDays(days); // Set to null for alltime, number for specific periods
      handleTimeframeChange(days ? `${days}days` : 'alltime');
      
      // Trigger analytics data fetching with explicit days value
      console.log('🚀 About to call fetchAnalytics and fetchRequesters with days:', days);
      fetchAnalytics(days); // Pass days directly to avoid state timing issues
      fetchRequesters();
    }
  }, [activeTab, analyticsPeriod]);

  // NEW: Show Analytics Dashboard — initialize default profile + auto-load data
  useEffect(() => {
    if (activeTab !== 'analytics' || !profiles || profiles.length === 0) return;
    // Default profile selection: prefer is_default, else first profile
    if (!showAnalyticsProfileId) {
      const def = profiles.find((p) => p.is_default) || profiles[0];
      if (def) setShowAnalyticsProfileId(def.id);
    }
  }, [activeTab, profiles]);

  // Filter shows scoped to the selected analytics profile
  const showAnalyticsScopedShows = useMemo(() => {
    if (!showAnalyticsProfileId || !shows) return [];
    return shows
      .filter((s) => s.profile_id === showAnalyticsProfileId)
      .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }, [shows, showAnalyticsProfileId]);

  // Auto-select the most recent show when profile changes
  useEffect(() => {
    if (activeTab !== 'analytics') return;
    if (showAnalyticsScopedShows.length === 0) {
      setShowAnalyticsShowId('');
      setShowDetailData(null);
      return;
    }
    // If the currently selected show isn't in scope, reset to the most recent
    const currentInScope = showAnalyticsScopedShows.some((s) => s.id === showAnalyticsShowId);
    if (!currentInScope) {
      setShowAnalyticsShowId(showAnalyticsScopedShows[0].id);
    }
  }, [showAnalyticsScopedShows, activeTab]);

  // Fetch show-detail when selected show changes (and view is 'detail')
  useEffect(() => {
    if (activeTab !== 'analytics') return;
    if (showAnalyticsView !== 'detail') return;
    if (showAnalyticsShowId) fetchShowDetailAnalytics(showAnalyticsShowId);
  }, [showAnalyticsShowId, showAnalyticsView, activeTab]);

  // Fetch show-trends when profile or limit changes (and view is 'trends')
  useEffect(() => {
    if (activeTab !== 'analytics') return;
    if (showAnalyticsView !== 'trends') return;
    if (showAnalyticsProfileId) fetchShowTrendsAnalytics(showAnalyticsProfileId, showTrendsLimit);
  }, [showAnalyticsProfileId, showTrendsLimit, showAnalyticsView, activeTab]);


  // Fetch analytics when analyticsDays changes
  useEffect(() => {
    if (activeTab === 'analytics' && analyticsDays !== undefined) {
      fetchAnalytics();
    }
  }, [analyticsDays]);

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
      // Update design settings
      await axios.put(`${API}/design/settings`, designSettings);
      
      // Update profile settings (for tip system toggle)
      await axios.put(`${API}/profile`, {
        tips_enabled: profile.tips_enabled
      });
      
      alert('Design settings updated successfully!');
    } catch (error) {
      setDesignError(error.response?.data?.detail || 'Error updating design settings');
    }
  };

  const handleArtistPhotoUpload = (e) => {
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
      const response = await axios.get(`${API}/qr-code`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setQrCode(response.data);
      setShowQRModal(true);
    } catch (error) {
      console.error('Error generating QR code:', error);
      alert('Error generating QR code. Please make sure you are logged in.');
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
      const response = await axios.get(`${API}/qr-flyer`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const link = document.createElement('a');
      link.href = response.data.flyer;
      link.download = `${musician.name}-qr-flyer.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error generating flyer:', error);
      alert('Error generating flyer. Please make sure you are logged in.');
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

  // UNIFIED: Single updateRequestStatus function for both Requests tab and On Stage tab
  const updateRequestStatus = async (requestId, status) => {
    // Validate status (archived handled by separate endpoint)
    const validStatuses = ['pending', 'up_next', 'accepted', 'played', 'rejected'];
    if (!validStatuses.includes(status)) {
      const errorMsg = `Invalid status "${status}". Use archiveRequest() for archiving.`;
      if (process.env.NODE_ENV === 'development') {
        console.error('[Status Update] Invalid status:', { requestId, status });
      }
      showErrorToast(errorMsg, error);
      return;
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        showErrorToast('Please log in again to update request status');
        return;
      }

      const payload = { status };
      if (process.env.NODE_ENV === 'development') {
        console.log('[Status Update] Request:', { requestId, status });
      }
      
      const response = await axios.put(
        `${API}/requests/${requestId}/status`, 
        payload,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[Status Update] Success:', { requestId, newStatus: response.data.new_status });
      }
      
      // Refresh request data for both tabs
      fetchRequests();
      
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[Status Update] Error:', {
          requestId,
          status,
          error: error.response?.data || error.message,
          statusCode: error.response?.status
        });
      }
      
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message || 
                       `Failed to update request status to "${status}"`;
      showErrorToast(errorMsg, error);
    }
  };

  // UNIFIED: Archive request function (separate endpoint from status updates)
  const archiveRequest = async (requestId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        showErrorToast('Please log in again to archive request');
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('[Archive] Request:', requestId);
      }
      
      const response = await axios.put(
        `${API}/requests/${requestId}/archive`,
        {},
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[Archive] Success:', requestId);
      }
      
      // Refresh request data for both tabs
      fetchRequests();
      
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[Archive] Error:', {
          requestId,
          error: error.response?.data || error.message,
          statusCode: error.response?.status
        });
      }
      
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message || 
                       'Failed to archive request';
      showErrorToast(errorMsg, error);
    }
  };

  // Helper: Map backend status to display label
  const getStatusLabel = (status) => {
    const labels = {
      'pending': 'Pending',
      'up_next': 'Up Next',
      'accepted': 'Accepted',
      'played': 'Played',
      'rejected': 'Skipped',  // Display as "Skipped" but backend stores "rejected"
      'archived': 'Archived'
    };
    return labels[status] || status;
  };

  const clearRequestSelection = () => {
    setSelectedRequests(new Set());
  };

  const selectAllRequests = (requestsList) => {
    const requestIds = requestsList.map(r => r.id);
    setSelectedRequests(new Set(requestIds));
  };

  const toggleRequestSelection = (requestId) => {
    setSelectedRequests(prev => {
      const newSet = new Set(prev);
      if (newSet.has(requestId)) {
        newSet.delete(requestId);
      } else {
        newSet.add(requestId);
      }
      return newSet;
    });
  };

  const batchUpdateRequestStatus = async (status) => {
    // Validate status
    const validStatuses = ['pending', 'up_next', 'accepted', 'played', 'rejected'];
    if (!validStatuses.includes(status)) {
      showErrorToast(`Invalid status "${status}". Cannot batch update to archived (use batch archive instead).`);
      return;
    }

    if (selectedRequests.size === 0) {
      showErrorToast('Please select requests to update');
      return;
    }

    const confirmMessage = `Mark ${selectedRequests.size} selected request(s) as ${status}?`;
    if (!confirm(confirmMessage)) return;

    try {
      const token = localStorage.getItem('token');
      if (process.env.NODE_ENV === 'development') {
        console.log('[Batch Update] Starting:', { count: selectedRequests.size, status });
      }
      
      const promises = Array.from(selectedRequests).map(requestId =>
        axios.put(`${API}/requests/${requestId}/status`, 
          { status },
          { headers: { 'Authorization': `Bearer ${token}` } }
        ).then(res => ({ requestId, success: true, data: res.data }))
         .catch(err => ({ requestId, success: false, error: err.response?.data?.detail || err.message }))
      );

      const results = await Promise.all(promises);
      
      const successes = results.filter(r => r.success).length;
      const failures = results.filter(r => !r.success).length;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[Batch Update] Complete:', { successes, failures });
        if (failures > 0) {
          const errorDetails = results.filter(r => !r.success).map(r => ({ id: r.requestId, error: r.error }));
          console.error('[Batch Update] Failures:', errorDetails);
        }
      }
      
      // Clear selection and refresh
      clearRequestSelection();
      fetchRequests();
      
      if (failures === 0) {
        alert(`Successfully updated ${successes} request(s) to ${status}`);
      } else {
        const message = `Updated ${successes} request(s). ${failures} failed.`;
        showErrorToast(message);
        alert(message + ' Check console for details.');
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[Batch Update] Fatal error:', error);
      }
      showErrorToast('Error updating requests. Please try again.');
    }
  };

  const batchArchiveRequests = async () => {
    if (selectedRequests.size === 0) {
      showErrorToast('Please select requests to archive');
      return;
    }

    const confirmMessage = `Archive ${selectedRequests.size} selected request(s)?`;
    if (!confirm(confirmMessage)) return;

    try {
      const token = localStorage.getItem('token');
      if (process.env.NODE_ENV === 'development') {
        console.log('[Batch Archive] Starting:', { count: selectedRequests.size });
      }
      
      const promises = Array.from(selectedRequests).map(requestId =>
        axios.put(`${API}/requests/${requestId}/archive`, 
          {},
          { headers: { 'Authorization': `Bearer ${token}` } }
        ).then(res => ({ requestId, success: true, data: res.data }))
         .catch(err => ({ requestId, success: false, error: err.response?.data?.detail || err.message }))
      );

      const results = await Promise.all(promises);
      
      const successes = results.filter(r => r.success).length;
      const failures = results.filter(r => !r.success).length;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[Batch Archive] Complete:', { successes, failures });
        if (failures > 0) {
          const errorDetails = results.filter(r => !r.success).map(r => ({ id: r.requestId, error: r.error }));
          console.error('[Batch Archive] Failures:', errorDetails);
        }
      }
      
      // Clear selection and refresh
      clearRequestSelection();
      fetchRequests();
      
      if (failures > 0) {
        const message = `Archived ${successes} request(s). ${failures} failed.`;
        showErrorToast(message);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[Batch Archive] Fatal error:', error);
      }
      showErrorToast('Error archiving requests. Please try again.');
    }
  };

  const batchDeleteRequests = async () => {
    if (selectedRequests.size === 0) {
      showErrorToast('Please select requests to delete');
      return;
    }

    const confirmMessage = `Permanently delete ${selectedRequests.size} selected request(s)? This cannot be undone.`;
    if (!confirm(confirmMessage)) return;

    try {
      const token = localStorage.getItem('token');
      if (process.env.NODE_ENV === 'development') {
        console.log('[Batch Delete] Starting:', { count: selectedRequests.size });
      }
      
      const promises = Array.from(selectedRequests).map(requestId =>
        axios.delete(`${API}/requests/${requestId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }).then(res => ({ requestId, success: true, data: res.data }))
         .catch(err => ({ requestId, success: false, error: err.response?.data?.detail || err.message }))
      );

      const results = await Promise.all(promises);
      
      const successes = results.filter(r => r.success).length;
      const failures = results.filter(r => !r.success).length;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[Batch Delete] Complete:', { successes, failures });
        if (failures > 0) {
          const errorDetails = results.filter(r => !r.success).map(r => ({ id: r.requestId, error: r.error }));
          console.error('[Batch Delete] Failures:', errorDetails);
        }
      }
      
      // Clear selection and refresh
      clearRequestSelection();
      fetchRequests();
      
      if (failures > 0) {
        const message = `Deleted ${successes} request(s). ${failures} failed.`;
        showErrorToast(message);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[Batch Delete] Fatal error:', error);
      }
      showErrorToast('Error deleting requests. Please try again.');
    }
  };

  // Song suggestion batch functions
  const toggleSuggestionSelection = (suggestionId) => {
    setSelectedSuggestions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(suggestionId)) {
        newSet.delete(suggestionId);
      } else {
        newSet.add(suggestionId);
      }
      return newSet;
    });
  };

  const clearSuggestionSelection = () => {
    setSelectedSuggestions(new Set());
  };

  const selectAllSuggestions = (suggestionsList) => {
    const suggestionIds = suggestionsList.map(s => s.id);
    setSelectedSuggestions(new Set(suggestionIds));
  };

  const batchSuggestionAction = async (action) => {
    if (selectedSuggestions.size === 0) {
      alert('Please select suggestions to update');
      return;
    }

    const actionText = action === 'added' ? 'add to repertoire' : 
                       action === 'learn_later' ? 'mark as learn later' : 'reject';
    const confirmMessage = `${actionText.charAt(0).toUpperCase() + actionText.slice(1)} ${selectedSuggestions.size} selected suggestion(s)?`;
    if (!confirm(confirmMessage)) return;

    try {
      const token = localStorage.getItem('token');
      const updatePromises = Array.from(selectedSuggestions).map(suggestionId =>
        action === 'learn_later' 
          ? axios.put(`${API}/song-suggestions/${suggestionId}/learn-later`, {}, { headers: { 'Authorization': `Bearer ${token}` } })
          : axios.put(`${API}/song-suggestions/${suggestionId}/status`, { status: action }, { headers: { 'Authorization': `Bearer ${token}` } })
      );

      await Promise.all(updatePromises);
      
      // Clear selection and refresh
      clearSuggestionSelection();
      fetchSongSuggestions();
      
      // UI update implies success - no alert needed for batch actions
    } catch (error) {
      console.error('Error batch updating suggestions:', error);
      alert('Error updating suggestions. Please try again.');
    }
  };

  const batchDeleteSuggestions = async () => {
    if (selectedSuggestions.size === 0) {
      alert('Please select suggestions to delete');
      return;
    }

    const confirmMessage = `Permanently delete ${selectedSuggestions.size} selected suggestion(s)? This cannot be undone.`;
    if (!confirm(confirmMessage)) return;

    try {
      const token = localStorage.getItem('token');
      const deletePromises = Array.from(selectedSuggestions).map(suggestionId =>
        axios.delete(`${API}/song-suggestions/${suggestionId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      );

      await Promise.all(deletePromises);
      
      // Clear selection and refresh
      clearSuggestionSelection();
      fetchSongSuggestions();
      
      // UI update implies success - no alert needed
    } catch (error) {
      console.error('Error batch deleting suggestions:', error);
      alert('Error deleting suggestions. Please try again.');
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

  // LST Upload functions
  const handleLstFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.name.toLowerCase().endsWith('.lst')) {
        setLstFile(file);
        setLstError('');
        setLstPreview(null);
      } else {
        setLstError('Please select a .lst file');
        setLstFile(null);
      }
    }
  };

  const previewLst = async () => {
    if (!lstFile) return;
    
    setLstUploading(true);
    setLstError('');
    
    try {
      const formData = new FormData();
      formData.append('file', lstFile);
      
      const response = await axios.post(`${API}/songs/lst/preview`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setLstPreview(response.data);
    } catch (error) {
      setLstError(error.response?.data?.detail || 'Error previewing LST file');
    } finally {
      setLstUploading(false);
    }
  };

  const uploadLst = async () => {
    if (!lstFile) return;
    
    setLstUploading(true);
    setLstError('');
    
    try {
      const formData = new FormData();
      formData.append('file', lstFile);
      
      const response = await axios.post(`${API}/songs/lst/upload?auto_enrich=${lstAutoEnrich}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Reset form and refresh songs
      setLstFile(null);
      setLstPreview(null);
      setShowLstUpload(false);
      setLstAutoEnrich(false);
      fetchSongs();
      
      // Show success message
      alert(response.data.message || 'LST file uploaded successfully!');
      
    } catch (error) {
      setLstError(error.response?.data?.detail || 'Error uploading LST file');
    } finally {
      setLstUploading(false);
    }
  };

  // NEW: Playlist functions (Pro feature)
  const fetchPlaylists = async () => {
    try {
      // Only fetch if user has Pro access (trial, pro, or canceled with valid access)
      if (!subscriptionStatus || !['trial', 'pro', 'canceled'].includes(subscriptionStatus.plan)) {
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

  const handleAddNewGenre = () => {
    if (newGenre.trim() && !filterOptions.genres?.includes(newGenre.trim())) {
      // Add to current song form
      if (!songForm.genres.includes(newGenre.trim())) {
        setSongForm({...songForm, genres: [...songForm.genres, newGenre.trim()]});
      }
      
      // Add to filterOptions for immediate use
      setFilterOptions(prev => ({
        ...prev,
        genres: [...(prev.genres || []), newGenre.trim()].sort()
      }));
      
      setNewGenre('');
      setShowAddGenre(false);
    }
  };

  const handleAddNewMood = () => {
    if (newMood.trim() && !filterOptions.moods?.includes(newMood.trim())) {
      // Add to current song form
      if (!songForm.moods.includes(newMood.trim())) {
        setSongForm({...songForm, moods: [...songForm.moods, newMood.trim()]});
      }
      
      // Add to filterOptions for immediate use
      setFilterOptions(prev => ({
        ...prev,
        moods: [...(prev.moods || []), newMood.trim()].sort()
      }));
      
      setNewMood('');
      setShowAddMood(false);
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

  // Context-aware bulk: add selected songs to the currently filtered playlist (not_in mode)
  const bulkAddToFilteredPlaylist = async () => {
    if (!playlistFilter || selectedSongs.size === 0) return;
    const playlist = playlists.find(p => p.id === playlistFilter);
    if (!playlist) return;
    try {
      const merged = Array.from(new Set([...(playlist.song_ids || []), ...Array.from(selectedSongs)]));
      await axios.put(`${API}/playlists/${playlistFilter}/songs`, { song_ids: merged });
      setSelectedSongs(new Set());
      fetchPlaylists();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error adding songs to playlist');
    }
  };

  // Context-aware bulk: remove selected songs from the currently filtered playlist (in mode)
  const bulkRemoveFromFilteredPlaylist = async () => {
    if (!playlistFilter || selectedSongs.size === 0) return;
    const playlist = playlists.find(p => p.id === playlistFilter);
    if (!playlist) return;
    try {
      const remaining = (playlist.song_ids || []).filter(id => !selectedSongs.has(id));
      await axios.put(`${API}/playlists/${playlistFilter}/songs`, { song_ids: remaining });
      setSelectedSongs(new Set());
      fetchPlaylists();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error removing songs from playlist');
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

  // NEW: Edit Playlist Songs Functions
  const openEditPlaylistSongsModal = async (playlistId) => {
    if (!playlistId || playlistId === 'all_songs') return;
    
    try {
      setEditPlaylistLoading(true);
      setEditPlaylistError('');
      
      // Fetch detailed playlist information
      const response = await axios.get(`${API}/playlists/${playlistId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      setEditingSongsPlaylist(response.data);
      setEditPlaylistSongs(response.data.songs || []);
      setShowEditPlaylistSongsModal(true);
      setHasUnsavedChanges(false);
      
    } catch (error) {
      console.error('Error fetching playlist details:', error);
      setEditPlaylistError('Error loading playlist details');
      alert('Error loading playlist for editing');
    } finally {
      setEditPlaylistLoading(false);
    }
  };

  const closeEditPlaylistSongsModal = () => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
        return;
      }
    }
    
    setShowEditPlaylistSongsModal(false);
    setEditingSongsPlaylist(null);
    setEditPlaylistSongs([]);
    setEditPlaylistError('');
    setHasUnsavedChanges(false);
  };

  const removeSongFromEditPlaylist = (songId) => {
    const updatedSongs = editPlaylistSongs.filter(song => song.id !== songId);
    setEditPlaylistSongs(updatedSongs);
    setHasUnsavedChanges(true);
  };

  const reorderPlaylistSongs = (dragIndex, hoverIndex) => {
    const draggedSong = editPlaylistSongs[dragIndex];
    const updatedSongs = [...editPlaylistSongs];
    updatedSongs.splice(dragIndex, 1);
    updatedSongs.splice(hoverIndex, 0, draggedSong);
    
    setEditPlaylistSongs(updatedSongs);
    setHasUnsavedChanges(true);
  };

  const savePlaylistSongs = async () => {
    if (!editingSongsPlaylist) return;
    
    try {
      setEditPlaylistLoading(true);
      setEditPlaylistError('');
      
      const songIds = editPlaylistSongs.map(song => song.id);
      
      await axios.put(`${API}/playlists/${editingSongsPlaylist.id}/songs`, {
        song_ids: songIds
      }, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      // Refresh playlists and close modal
      await fetchPlaylists();
      setShowEditPlaylistSongsModal(false);
      setEditingSongsPlaylist(null);
      setEditPlaylistSongs([]);
      setHasUnsavedChanges(false);
      
      alert('Playlist updated successfully!');
      
    } catch (error) {
      console.error('Error saving playlist changes:', error);
      setEditPlaylistError(error.response?.data?.detail || 'Error saving playlist changes');
    } finally {
      setEditPlaylistLoading(false);
    }
  };

  // NEW: Enhanced Playlist Management Functions
  const showPlaylistToastWithMessage = (message) => {
    setPlaylistToastMessage(message);
    setShowPlaylistToast(true);
    setTimeout(() => setShowPlaylistToast(false), 5000); // Auto-hide after 5 seconds
  };

  const startEditingPlaylistName = (playlistId, currentName) => {
    setEditingPlaylist(playlistId);
    setEditingPlaylistName(currentName);
  };

  const cancelEditingPlaylistName = () => {
    setEditingPlaylist(null);
    setEditingPlaylistName('');
  };

  const savePlaylistName = async (playlistId) => {
    const newName = editingPlaylistName.trim();
    if (!newName) {
      alert('Playlist name cannot be empty');
      return;
    }

    if (newName.length > 100) {
      alert('Playlist name too long (max 100 characters)');
      return;
    }

    try {
      await axios.put(`${API}/playlists/${playlistId}/name`, {
        name: newName
      }, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      // Update local state
      setPlaylists(prev => prev.map(p => 
        p.id === playlistId ? { ...p, name: newName } : p
      ));

      setEditingPlaylist(null);
      setEditingPlaylistName('');
      showPlaylistToastWithMessage('Playlist renamed successfully!');

    } catch (error) {
      console.error('Error renaming playlist:', error);
      if (error.response?.status === 403) {
        showPlaylistToastWithMessage('You can only rename your own playlists');
      } else if (error.response?.status === 404) {
        showPlaylistToastWithMessage('Playlist not found');
      } else {
        showPlaylistToastWithMessage(error.response?.data?.detail || 'Error renaming playlist');
      }
    }
  };

  const togglePlaylistVisibility = async (playlistId, currentStatus) => {
    const newStatus = !currentStatus;
    
    try {
      const response = await axios.put(`${API}/playlists/${playlistId}/visibility`, {
        is_public: newStatus
      }, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      // Update local state
      setPlaylists(prev => prev.map(p => 
        p.id === playlistId ? { ...p, is_public: newStatus } : p
      ));

      const statusText = newStatus ? 'public' : 'private';
      let message = `Playlist made ${statusText}`;
      
      // Show additional message if active playlist was cleared
      if (response.data.active_playlist_cleared) {
        message += ' and removed from active status';
        // Reset active playlist selection
        setActivePlaylistId(null);
      }
      
      showPlaylistToastWithMessage(message);

    } catch (error) {
      console.error('Error toggling playlist visibility:', error);
      if (error.response?.status === 403) {
        showPlaylistToastWithMessage('You can only modify your own playlists');
      } else if (error.response?.status === 404) {
        showPlaylistToastWithMessage('Playlist not found');
      } else {
        showPlaylistToastWithMessage(error.response?.data?.detail || 'Error updating playlist visibility');
      }
    }
  };

  const confirmDeletePlaylist = (playlist) => {
    setPlaylistToDelete(playlist);
    setShowPlaylistDeleteConfirmation(true);
  };

  const cancelDeletePlaylist = () => {
    setPlaylistToDelete(null);
    setShowPlaylistDeleteConfirmation(false);
  };

  const softDeletePlaylist = async () => {
    if (!playlistToDelete) return;

    try {
      const response = await axios.delete(`${API}/playlists/${playlistToDelete.id}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      // Remove from local state
      setPlaylists(prev => prev.filter(p => p.id !== playlistToDelete.id));
      
      // Clear playlist filter if it was the deleted playlist
      if (playlistFilter === playlistToDelete.id) {
        setPlaylistFilter('');
      }

      // Close Edit Playlist modal if it was the deleted playlist
      if (editingSongsPlaylist && editingSongsPlaylist.id === playlistToDelete.id) {
        setShowEditPlaylistSongsModal(false);
        setEditingSongsPlaylist(null);
        setEditPlaylistSongs([]);
        setHasUnsavedChanges(false);
      }

      // Close any open dropdown
      setOpenDropdownId(null);

      let message = response.data.message || 'Playlist deleted successfully';
      
      // Show additional message if active playlist was cleared
      if (response.data.active_playlist_cleared) {
        setActivePlaylistId(null);
        message += ' Active playlist cleared.';
      }
      
      showPlaylistToastWithMessage(message);

    } catch (error) {
      console.error('Error deleting playlist:', error);
      if (error.response?.status === 403) {
        showPlaylistToastWithMessage('You can only delete your own playlists');
      } else if (error.response?.status === 404) {
        showPlaylistToastWithMessage('Playlist not found');
      } else {
        showPlaylistToastWithMessage(error.response?.data?.detail || 'Error deleting playlist');
      }
    } finally {
      setPlaylistToDelete(null);
      setShowPlaylistDeleteConfirmation(false);
    }
  };

  const handleContactSubmit = async (e) => {
    e.preventDefault();
    if (!contactForm.name.trim() || !contactForm.email.trim() || !contactForm.message.trim()) {
      alert('Please fill in all fields');
      return;
    }

    setContactLoading(true);
    try {
      await axios.post(`${API}/contact`, {
        name: contactForm.name,
        email: contactForm.email,
        message: contactForm.message,
        musician_id: musician.id
      });
      
      alert('Message sent successfully! We\'ll get back to you soon.');
      setContactForm({ name: '', email: '', message: '' });
    } catch (error) {
      console.error('Error sending contact message:', error);
      alert('Error sending message. Please try again.');
    } finally {
      setContactLoading(false);
    }
  };

  // NEW: Initialize subscription status on component mount
  useEffect(() => {
    if (musician) {
      fetchSubscriptionStatus();
    }
  }, [musician]);

  // Fetch playlists on component mount and when subscription status changes
  useEffect(() => {
    if (musician && subscriptionStatus && ['trial', 'pro', 'canceled'].includes(subscriptionStatus.plan)) {
      fetchPlaylists();
    }
  }, [musician, subscriptionStatus]);

  // NEW: Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Close dropdown if clicking outside
      if (openDropdownId && !event.target.closest('.relative')) {
        setOpenDropdownId(null);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [openDropdownId]);

  // Use centralized audience URL helper
  const audienceUrl = getAudienceUrl(musician.slug);

  if (loading) {
    return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Error Toast */}
      {errorToast.show && (
        <div className="fixed top-4 right-4 z-50 animate-fade-in">
          <div className="bg-red-600 text-white px-6 py-4 rounded-lg shadow-lg max-w-md">
            <div className="flex items-start">
              <span className="text-xl mr-3">⚠️</span>
              <div className="flex-1">
                <p className="font-medium">Error</p>
                <p className="text-sm mt-1">{errorToast.message}</p>
              </div>
              <button
                onClick={() => setErrorToast({ show: false, message: '' })}
                className="ml-4 text-white hover:text-gray-200"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Header */}
      <header className="bg-gray-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Desktop Layout */}
          <div className="hidden md:flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <img
                src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png"
                alt="RequestWave"
                className="w-10 h-10 object-contain"
              />
              <h1 className="text-2xl font-bold">
                <span className="text-purple-400">Request</span><span className="text-green-400">Wave</span>
              </h1>
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

          {/* Mobile Layout */}
          <div className="md:hidden py-4">
            <div className="flex justify-between items-start">
              {/* Left side: Logo and Welcome */}
              <div className="flex flex-col space-y-2">
                <div className="flex items-center space-x-3">
                  <img
                    src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png"
                    alt="RequestWave"
                    className="w-8 h-8 object-contain"
                  />
                  <h1 className="text-xl font-bold">
                    <span className="text-purple-400">Request</span><span className="text-green-400">Wave</span>
                  </h1>
                </div>
                <span className="text-gray-300 text-sm ml-1">Welcome, {musician.name}</span>
              </div>

              {/* Right side: Logout */}
              <button
                onClick={logout}
                className="bg-red-600 hover:bg-red-700 px-3 py-2 rounded-lg transition duration-300 text-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-2 sm:px-4 lg:px-6 xl:px-8 py-4 sm:py-8">

        {/* Desktop Tabs (hidden on mobile) */}
        <div className="hidden md:flex flex-wrap gap-1 bg-gray-800 rounded-lg p-1 mb-8">
          {['onstage', 'songs', 'requests', 'analytics', 'profile', 'events', ...(BILLING_ENABLED ? ['subscription'] : [])].map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveTab(tab);
                
                // Directly trigger analytics fetch when analytics tab is clicked
                if (tab === 'analytics') {
                  console.log('Analytics tab clicked - fetching data immediately');
                  fetchAnalytics();
                  fetchRequesters();
                }
                if (tab === 'events') {
                  fetchEvents();
                }
              }}
              className={`px-3 py-2 rounded-lg font-medium transition duration-300 text-sm sm:text-base flex-shrink-0 ${
                activeTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab === 'analytics' ? 'Analytics' : 
               tab === 'design' ? 'Design' : 
               tab === 'onstage' ? 'On Stage' : 
               tab === 'profile' ? 'Profiles' :
               tab === 'events' ? 'Events' :
               tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'requests' && requests.filter(r => r.status === 'pending').length > 0 && (
                <span className="ml-2 bg-red-500 text-white rounded-full px-2 py-1 text-xs">
                  {requests.filter(r => r.status === 'pending').length}
                </span>
              )}
            </button>
          ))}
          
          {/* Help/Quick Start Button */}
          <button
            onClick={() => setShowQuickStart(true)}
            className="px-2 py-2 rounded-lg font-medium transition duration-300 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white flex items-center justify-center w-8 h-8 ml-2"
            title="Quick Start Guide"
          >
            ?
          </button>
        </div>

        {/* Mobile Navigation Dropdown (visible on mobile only) */}
        <div className="md:hidden mb-8">
          <div className="relative mobile-nav-dropdown">
            <button
              onClick={() => setShowMobileNav(!showMobileNav)}
              className="w-full bg-gray-800 rounded-lg p-3 flex justify-between items-center"
            >
              <div className="flex items-center space-x-2">
                <span className="font-medium">
                  {activeTab === 'analytics' ? 'Analytics' : 
                   activeTab === 'design' ? 'Design' : 
                   activeTab === 'onstage' ? 'On Stage' : 
                   activeTab === 'profile' ? 'Profiles' :
                   activeTab === 'events' ? 'Events' :
                   activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}
                </span>
                {activeTab === 'requests' && requests.filter(r => r.status === 'pending').length > 0 && (
                  <span className="bg-red-500 text-white rounded-full px-2 py-1 text-xs">
                    {requests.filter(r => r.status === 'pending').length}
                  </span>
                )}
              </div>
              <svg className={`w-5 h-5 transition-transform ${showMobileNav ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            
            {/* Mobile Dropdown Menu */}
            {showMobileNav && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 rounded-lg shadow-xl border border-gray-700 z-50">
                <div className="py-2">
                  {['onstage', 'songs', 'requests', 'analytics', 'profile', 'events', ...(BILLING_ENABLED ? ['subscription'] : [])].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => {
                        setActiveTab(tab);
                        setShowMobileNav(false);
                        if (tab === 'events') fetchEvents();
                      }}
                      className={`w-full text-left px-4 py-3 hover:bg-gray-700 flex items-center justify-between ${
                        activeTab === tab ? 'bg-purple-600 text-white' : 'text-gray-300'
                      }`}
                    >
                      <span>
                        {tab === 'analytics' ? 'Analytics' : 
                         tab === 'design' ? 'Design' : 
                         tab === 'onstage' ? 'On Stage' : 
                         tab === 'profile' ? 'Profiles' :
                         tab === 'events' ? 'Events' :
                         tab.charAt(0).toUpperCase() + tab.slice(1)}
                      </span>
                      {tab === 'requests' && requests.filter(r => r.status === 'pending').length > 0 && (
                        <span className="bg-red-500 text-white rounded-full px-2 py-1 text-xs">
                          {requests.filter(r => r.status === 'pending').length}
                        </span>
                      )}
                    </button>
                  ))}
                  
                  <div className="border-t border-gray-700 mt-2 pt-2">
                    <button
                      onClick={() => {
                        setShowQuickStart(true);
                        setShowMobileNav(false);
                      }}
                      className="w-full text-left px-4 py-3 hover:bg-gray-700 text-gray-300"
                    >
                      📖 Quick Start Guide
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Songs Tab */}
        {activeTab === 'songs' && (
          <div>
            {/* Streamlined Header - No Title */}
            <div className="mb-6">
              {/* Header content removed - buttons moved above playlists */}
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

            {/* LST Upload Section */}
            {showLstUpload && (
              <div className="bg-gray-800 rounded-xl p-6 mb-8">
                <h3 className="text-lg font-bold mb-4">Upload Songs from LST File</h3>
                <p className="text-gray-300 mb-4 text-sm">
                  Upload a setlist (.lst) file with songs in "Song Title - Artist" format
                  <br />
                  Perfect for importing existing setlists or song collections!
                </p>

                <div className="space-y-4">
                  <div>
                    <input
                      type="file"
                      accept=".lst"
                      onChange={handleLstFileSelect}
                      className="block w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-orange-600 file:text-white hover:file:bg-orange-700"
                    />
                  </div>

                  {lstFile && (
                    <div className="bg-gray-700 rounded-lg p-4">
                      <p className="text-sm font-medium">Selected: {lstFile.name}</p>
                      <p className="text-xs text-gray-400">Size: {(lstFile.size / 1024).toFixed(1)} KB</p>
                      
                      {/* Auto-enrich option */}
                      <div className="mt-3">
                        <label className="flex items-center space-x-3 text-sm">
                          <input
                            type="checkbox"
                            checked={lstAutoEnrich}
                            onChange={(e) => setLstAutoEnrich(e.target.checked)}
                            className="rounded bg-gray-600 border-gray-500 text-orange-600 focus:ring-orange-500 focus:ring-offset-0"
                          />
                          <span className="text-gray-300">
                            Auto-enrich metadata (adds year information via Spotify)
                          </span>
                        </label>
                      </div>
                    </div>
                  )}

                  {lstFile && (
                    <div className="flex space-x-4">
                      <button
                        onClick={previewLst}
                        disabled={lstUploading}
                        className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                      >
                        {lstUploading ? 'Processing...' : 'Preview'}
                      </button>
                      {lstPreview && (
                        <button
                          onClick={uploadLst}
                          disabled={lstUploading}
                          className="bg-orange-600 hover:bg-orange-700 px-4 py-2 rounded-lg font-bold transition duration-300 disabled:opacity-50"
                        >
                          {lstUploading ? 'Uploading...' : `Import ${lstPreview.total_songs} Songs`}
                        </button>
                      )}
                    </div>
                  )}

                  {/* LST Preview */}
                  {lstPreview && (
                    <div className="bg-gray-700 rounded-lg p-4">
                      <h4 className="font-bold mb-2">
                        Preview: {lstPreview.total_songs} songs found
                      </h4>
                      
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-600">
                              <th className="text-left p-2">Title</th>
                              <th className="text-left p-2">Artist</th>
                              <th className="text-left p-2">Genre</th>
                              <th className="text-left p-2">Mood</th>
                            </tr>
                          </thead>
                          <tbody>
                            {lstPreview.songs.map((song, index) => (
                              <tr key={index} className="border-b border-gray-600">
                                <td className="p-2">{song.title}</td>
                                <td className="p-2">{song.artist}</td>
                                <td className="p-2">{song.genres?.join(', ')}</td>
                                <td className="p-2">{song.moods?.join(', ')}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {lstError && (
                    <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-red-200">
                      {lstError}
                    </div>
                  )}
                </div>
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
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 col-span-1 md:col-span-1"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Artist"
                    value={songForm.artist}
                    onChange={(e) => setSongForm({...songForm, artist: e.target.value})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 col-span-1 md:col-span-1"
                    required
                  />
                  
                  {/* NEW: Auto-fill Metadata Button */}
                  <div className="col-span-1 md:col-span-2 mb-4">
                    <button
                      type="button"
                      onClick={handleAutoFillMetadata}
                      disabled={autoFillLoading || !songForm.title.trim() || !songForm.artist.trim()}
                      className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-medium transition duration-300 disabled:cursor-not-allowed flex items-center justify-center sm:justify-start space-x-2"
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
                  
                  {/* NEW: Multi-select Genres Dropdown - EDIT MODAL */}
                  <div className="col-span-1 md:col-span-1">
                    <label className="block text-sm font-medium text-gray-300 mb-2">Genres</label>
                    <div className="space-y-2">
                      {/* Selected Genres Display */}
                      <div className="flex flex-wrap gap-2 min-h-[2rem] p-2 bg-gray-700 border border-gray-600 rounded-lg">
                        {songForm.genres.length === 0 ? (
                          <span className="text-gray-400 text-sm">Select genres...</span>
                        ) : (
                          songForm.genres.map((genre, index) => (
                            <span
                              key={index}
                              className="bg-blue-600 text-white px-2 py-1 rounded text-sm flex items-center space-x-1"
                            >
                              <span>{genre}</span>
                              <button
                                type="button"
                                onClick={() => {
                                  const newGenres = songForm.genres.filter((_, i) => i !== index);
                                  setSongForm({...songForm, genres: newGenres});
                                }}
                                className="text-blue-200 hover:text-white ml-1"
                              >
                                ×
                              </button>
                            </span>
                          ))
                        )}
                      </div>
                      
                      {/* Genre Selection Dropdown */}
                      <select
                        value=""
                        onChange={(e) => {
                          if (e.target.value && !songForm.genres.includes(e.target.value)) {
                            setSongForm({...songForm, genres: [...songForm.genres, e.target.value]});
                          }
                        }}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                      >
                        <option value="">Add genre...</option>
                        {filterOptions.genres?.filter(genre => !songForm.genres.includes(genre)).map(genre => (
                          <option key={genre} value={genre}>{genre}</option>
                        ))}
                      </select>
                      
                      {/* Add New Genre */}
                      {showAddGenre ? (
                        <div className="flex space-x-2">
                          <input
                            type="text"
                            value={newGenre}
                            onChange={(e) => setNewGenre(e.target.value)}
                            placeholder="New genre name"
                            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                            onKeyPress={(e) => e.key === 'Enter' && handleAddNewGenre()}
                          />
                          <button
                            type="button"
                            onClick={handleAddNewGenre}
                            className="bg-green-600 hover:bg-green-700 px-3 py-2 rounded-lg text-sm"
                          >
                            Add
                          </button>
                          <button
                            type="button"
                            onClick={() => {setShowAddGenre(false); setNewGenre('');}}
                            className="bg-gray-600 hover:bg-gray-700 px-3 py-2 rounded-lg text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setShowAddGenre(true)}
                          className="text-green-400 hover:text-green-300 text-sm flex items-center space-x-1"
                        >
                          <span>+</span>
                          <span>Add new genre</span>
                        </button>
                      )}
                    </div>
                  </div>
                  
                  {/* NEW: Multi-select Moods Dropdown - EDIT MODAL */}
                  <div className="col-span-1 md:col-span-1">
                    <label className="block text-sm font-medium text-gray-300 mb-2">Moods</label>
                    <div className="space-y-2">
                      {/* Selected Moods Display */}
                      <div className="flex flex-wrap gap-2 min-h-[2rem] p-2 bg-gray-700 border border-gray-600 rounded-lg">
                        {songForm.moods.length === 0 ? (
                          <span className="text-gray-400 text-sm">Select moods...</span>
                        ) : (
                          songForm.moods.map((mood, index) => (
                            <span
                              key={index}
                              className="bg-green-600 text-white px-2 py-1 rounded text-sm flex items-center space-x-1"
                            >
                              <span>{mood}</span>
                              <button
                                type="button"
                                onClick={() => {
                                  const newMoods = songForm.moods.filter((_, i) => i !== index);
                                  setSongForm({...songForm, moods: newMoods});
                                }}
                                className="text-green-200 hover:text-white ml-1"
                              >
                                ×
                              </button>
                            </span>
                          ))
                        )}
                      </div>
                      
                      {/* Mood Selection Dropdown */}
                      <select
                        value=""
                        onChange={(e) => {
                          if (e.target.value && !songForm.moods.includes(e.target.value)) {
                            setSongForm({...songForm, moods: [...songForm.moods, e.target.value]});
                          }
                        }}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                      >
                        <option value="">Add mood...</option>
                        {filterOptions.moods?.filter(mood => !songForm.moods.includes(mood)).map(mood => (
                          <option key={mood} value={mood}>{mood}</option>
                        ))}
                      </select>
                      
                      {/* Add New Mood */}
                      {showAddMood ? (
                        <div className="flex space-x-2">
                          <input
                            type="text"
                            value={newMood}
                            onChange={(e) => setNewMood(e.target.value)}
                            placeholder="New mood name"
                            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                            onKeyPress={(e) => e.key === 'Enter' && handleAddNewMood()}
                          />
                          <button
                            type="button"
                            onClick={handleAddNewMood}
                            className="bg-green-600 hover:bg-green-700 px-3 py-2 rounded-lg text-sm"
                          >
                            Add
                          </button>
                          <button
                            type="button"
                            onClick={() => {setShowAddMood(false); setNewMood('');}}
                            className="bg-gray-600 hover:bg-gray-700 px-3 py-2 rounded-lg text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setShowAddMood(true)}
                          className="text-green-400 hover:text-green-300 text-sm flex items-center space-x-1"
                        >
                          <span>+</span>
                          <span>Add new mood</span>
                        </button>
                      )}
                    </div>
                  </div>
                  <input
                    type="number"
                    placeholder="Year"
                    value={songForm.year}
                    onChange={(e) => setSongForm({...songForm, year: e.target.value})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 col-span-1 md:col-span-1"
                  />
                  <input
                    type="text"
                    placeholder="Notes (optional)"
                    value={songForm.notes}
                    onChange={(e) => setSongForm({...songForm, notes: e.target.value})}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 col-span-1 md:col-span-1"
                  />
                  <div className="col-span-1 md:col-span-2">
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
            {/* Help Button and Manage Songs in same row above playlists */}
            <div className="flex justify-between items-center mb-4">
              <button
                onClick={() => setShowSongsHelp(true)}
                className="bg-gray-600 hover:bg-gray-500 active:bg-gray-700 px-3 py-2 rounded-lg transition duration-300 flex items-center space-x-1 text-sm"
                title="Songs Tab Help"
              >
                <span className="text-gray-400">❓</span>
                <span className="text-gray-300 font-medium">Help</span>
              </button>
              
              {/* Song Management Dropdown */}
              <div className="relative song-management-dropdown">
                <button
                  onClick={() => setShowSongManagementDropdown(!showSongManagementDropdown)}
                  className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg font-bold transition duration-300 flex items-center space-x-2"
                >
                  <span>⚙️ Manage Songs</span>
                  <svg className={`w-4 h-4 transition-transform ${showSongManagementDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {/* Dropdown Menu */}
                {showSongManagementDropdown && (
                  <div className="absolute right-0 mt-2 w-56 bg-gray-800 rounded-lg shadow-xl border border-gray-700 z-50">
                    <div className="py-2">
                      {/* Add New Song - First */}
                      <button
                        onClick={() => {
                          setShowAddSong(!showAddSong);
                          setShowSongManagementDropdown(false);
                        }}
                        className="w-full text-left px-4 py-3 hover:bg-gray-700 flex items-center space-x-3"
                      >
                        <span className="text-lg">➕</span>
                        <span>Add New Song</span>
                      </button>
                      
                      {/* Import Playlist - Second */}
                      <button
                        onClick={() => {
                          setShowPlaylistImport(!showPlaylistImport);
                          setShowSongManagementDropdown(false);
                        }}
                        className="w-full text-left px-4 py-3 hover:bg-gray-700 flex items-center space-x-3"
                      >
                        <span className="text-lg">🎵</span>
                        <span>Import Playlist</span>
                      </button>
                      
                      {/* Upload CSV - Third */}
                      <button
                        onClick={() => {
                          setShowCsvUpload(!showCsvUpload);
                          setShowSongManagementDropdown(false);
                        }}
                        className="w-full text-left px-4 py-3 hover:bg-gray-700 flex items-center space-x-3"
                      >
                        <span className="text-lg">📄</span>
                        <span>Upload CSV</span>
                      </button>
                      
                      {/* Upload LST - Fourth */}
                      <button
                        onClick={() => {
                          setShowLstUpload(!showLstUpload);
                          setShowSongManagementDropdown(false);
                        }}
                        className="w-full text-left px-4 py-3 hover:bg-gray-700 flex items-center space-x-3"
                      >
                        <span className="text-lg">📝</span>
                        <span>Upload LST</span>
                      </button>
                      
                      {/* Auto-fill All - Fifth */}
                      <button
                        onClick={() => {
                          handleBatchEnrich();
                          setShowSongManagementDropdown(false);
                        }}
                        disabled={batchEnrichLoading}
                        className="w-full text-left px-4 py-3 hover:bg-gray-700 disabled:bg-gray-600 disabled:opacity-50 flex items-center space-x-3"
                      >
                        <span className="text-lg">✨</span>
                        <span>
                          {batchEnrichLoading ? 'Auto-filling...' : 'Auto-fill All'}
                        </span>
                      </button>
                      
                      {/* Divider */}
                      <div className="border-t border-gray-600 my-2"></div>
                      
                      {/* Export CSV - Last */}
                      <button
                        onClick={() => {
                          exportSongsToCSV();
                          setShowSongManagementDropdown(false);
                        }}
                        className="w-full text-left px-4 py-3 hover:bg-gray-700 flex items-center space-x-3"
                      >
                        <span className="text-lg">💾</span>
                        <span>Export CSV</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* NEW: Compact Playlists Dropdown */}
            {subscriptionStatus && ['trial', 'pro', 'canceled'].includes(subscriptionStatus.plan) && (
              <div className="bg-gray-800 rounded-xl p-4 mb-6">
                <div 
                  className="flex justify-between items-center cursor-pointer hover:bg-gray-700 rounded-lg p-2 transition duration-200"
                  onClick={() => setPlaylistsExpanded(!playlistsExpanded)}
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">🎵</span>
                    <h3 className="text-lg font-medium">Playlists</h3>
                    <span className="text-sm text-gray-400">
                      ({playlists.filter(p => p.id !== 'all_songs').length})
                    </span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowManagePlaylistsModal(true);
                      }}
                      className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded text-sm font-medium transition duration-300"
                    >
                      Manage
                    </button>
                    <span className={`transition-transform duration-200 ${playlistsExpanded ? 'rotate-180' : ''}`}>
                      ▼
                    </span>
                  </div>
                </div>

                {playlistsExpanded && (
                  <div className="mt-4 border-t border-gray-700 pt-4">
                    {playlists.filter(p => p.id !== 'all_songs').length === 0 ? (
                      <div className="text-center py-6">
                        <div className="text-3xl mb-3">🎵</div>
                        <p className="text-gray-400 mb-3">No playlists yet</p>
                        <button
                          onClick={() => setShowManagePlaylistsModal(true)}
                          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-medium transition duration-300"
                        >
                          Create First Playlist
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {playlists.filter(p => p.id !== 'all_songs').map(playlist => (
                          <div key={playlist.id} className="bg-gray-700 rounded-lg p-3 flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              {editingPlaylist === playlist.id ? (
                                <div className="flex items-center space-x-2">
                                  <input
                                    type="text"
                                    value={editingPlaylistName}
                                    onChange={(e) => setEditingPlaylistName(e.target.value)}
                                    className="bg-gray-600 border border-gray-500 rounded px-2 py-1 text-white flex-1 text-sm"
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') {
                                        e.preventDefault();
                                        savePlaylistName(playlist.id);
                                      } else if (e.key === 'Escape') {
                                        e.preventDefault();
                                        cancelEditingPlaylistName();
                                      }
                                    }}
                                    onBlur={() => {
                                      if (editingPlaylistName.trim()) {
                                        savePlaylistName(playlist.id);
                                      } else {
                                        cancelEditingPlaylistName();
                                      }
                                    }}
                                    autoFocus
                                  />
                                  {!editingPlaylistName.trim() && (
                                    <span className="text-red-400 text-xs">Name required</span>
                                  )}
                                </div>
                              ) : (
                                <div>
                                  <div className="flex items-center space-x-2">
                                    <h4 className="font-medium text-white truncate">{playlist.name}</h4>
                                    <div className="flex items-center space-x-1 flex-shrink-0">
                                      {playlist.is_active && (
                                        <span className="bg-green-500 text-white px-1.5 py-0.5 rounded-full text-xs font-medium">
                                          Active
                                        </span>
                                      )}
                                      <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
                                        playlist.is_public 
                                          ? 'bg-blue-500 text-white' 
                                          : 'bg-gray-500 text-white'
                                      }`}>
                                        {playlist.is_public ? '🌐' : '🔒'}
                                      </span>
                                    </div>
                                  </div>
                                  <p className="text-gray-400 text-xs mt-0.5">
                                    {playlist.song_count} songs
                                  </p>
                                </div>
                              )}
                            </div>
                            
                            {editingPlaylist !== playlist.id && (
                              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-1 sm:space-x-1 ml-2 flex-shrink-0">
                                {/* Mobile: Stack buttons vertically, Desktop: Side by side */}
                                <div className="flex items-center space-x-1">
                                  <button
                                    onClick={() => openEditPlaylistSongsModal(playlist.id)}
                                    className="bg-purple-600 hover:bg-purple-700 px-2 py-1 rounded text-xs text-white transition duration-300"
                                    title="Edit songs"
                                  >
                                    ✏️
                                  </button>
                                  
                                  <button
                                    onClick={() => togglePlaylistVisibility(playlist.id, playlist.is_public)}
                                    className={`px-2 py-1 rounded text-xs transition duration-300 ${
                                      playlist.is_public
                                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                        : 'bg-gray-600 hover:bg-gray-500 text-white'
                                    }`}
                                    title={playlist.is_public ? 'Make private' : 'Make public'}
                                  >
                                    {playlist.is_public ? '🔒' : '🌐'}
                                  </button>
                                </div>
                                
                                {/* 3-Dot Menu - Full width on mobile */}
                                <div className="relative w-full sm:w-auto">
                                  <button
                                    onClick={() => {
                                      setOpenDropdownId(openDropdownId === playlist.id ? null : playlist.id);
                                    }}
                                    className="w-full sm:w-auto bg-gray-600 hover:bg-gray-500 px-2 py-1 rounded text-xs text-white transition duration-300"
                                    title="More options"
                                  >
                                    ⋮
                                  </button>
                                  
                                  {openDropdownId === playlist.id && (
                                    <div className="absolute right-0 top-full mt-1 bg-gray-800 border border-gray-600 rounded-lg shadow-lg z-10 min-w-[140px]">
                                      <button
                                        onClick={() => {
                                          startEditingPlaylistName(playlist.id, playlist.name);
                                          setOpenDropdownId(null);
                                        }}
                                        className="w-full text-left px-3 py-2 text-xs text-white hover:bg-gray-700 flex items-center space-x-2"
                                      >
                                        <span>✏️</span>
                                        <span>Rename</span>
                                      </button>
                                      <button
                                        onClick={() => {
                                          activatePlaylist(playlist.id);
                                          setOpenDropdownId(null);
                                        }}
                                        disabled={playlist.is_active}
                                        className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-700 flex items-center space-x-2 ${
                                          playlist.is_active ? 'text-gray-400 cursor-not-allowed' : 'text-white'
                                        }`}
                                      >
                                        <span>⭐</span>
                                        <span>{playlist.is_active ? 'Active' : 'Set Active'}</span>
                                      </button>
                                      <button
                                        onClick={() => {
                                          alert('Adding songs is almost ready. For now, use Edit Playlist to remove/reorder.');
                                          setOpenDropdownId(null);
                                        }}
                                        className="w-full text-left px-3 py-2 text-xs text-white hover:bg-gray-700 flex items-center space-x-2"
                                      >
                                        <span>➕</span>
                                        <span>Add Songs</span>
                                      </button>
                                      <hr className="border-gray-600 my-1" />
                                      <button
                                        onClick={() => {
                                          confirmDeletePlaylist(playlist);
                                          setOpenDropdownId(null);
                                        }}
                                        className="w-full text-left px-3 py-2 text-xs text-red-300 hover:bg-gray-700 hover:text-red-200 flex items-center space-x-2"
                                      >
                                        <span>🗑️</span>
                                        <span>Delete</span>
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="bg-gray-800 rounded-xl p-6">
              {/* NEW: Filter and Batch Edit Controls */}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-4">
                  <div>
                    <h2 className="text-xl font-bold">Your Songs ({filteredSongs.length})</h2>
                  </div>
                  <div className="flex space-x-2 items-center">
                    {/* NEW: Sort By Dropdown with "Sort by:" label */}
                    <div className="flex items-center space-x-2">
                      <span className="text-gray-400 text-xs">Sort by:</span>
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
                        <option value="random">🎲 Random</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* NEW: Redesigned Filter Layout - No Labels, Matches Audience View */}
                <div className="space-y-3 mb-4">
                  {/* Search Bar and Clear Filters Button Row */}
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      placeholder="Search Song Title or Artist"
                      value={songFilter}
                      onChange={(e) => setSongFilter(e.target.value)}
                      className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm"
                    />
                    <button
                      onClick={() => {
                        setSongFilter('');
                        setGenreFilter('');
                        setMoodFilter('');
                        setYearFilter('');
                        setDecadeFilter('');
                        setNotesFilter('');
                        setPlaylistFilter('');
                      }}
                      className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded-lg text-white text-sm font-medium transition duration-300"
                    >
                      Clear Filters
                    </button>
                  </div>
                  
                  {/* Playlists Dropdown - Full Width */}
                  <div className="flex items-center space-x-2">
                    <select
                      value={playlistFilter}
                      onChange={(e) => setPlaylistFilter(e.target.value)}
                      className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                    >
                      <option value="">All Playlists</option>
                      {playlists.map((playlist) => (
                        <option key={playlist.id} value={playlist.id}>
                          {playlist.name} ({playlist.song_count} songs)
                        </option>
                      ))}
                    </select>
                    {playlistFilter && playlistFilter !== 'all_songs' && (
                      <button
                        onClick={() => openEditPlaylistSongsModal(playlistFilter)}
                        className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-2 rounded-lg text-sm font-medium flex items-center space-x-1 transition duration-300"
                        title="Edit Playlist"
                      >
                        <span>✏️</span>
                        <span>Edit</span>
                      </button>
                    )}
                  </div>

                  {/* Playlist filter mode toggle - only when a playlist is selected */}
                  {playlistFilter && playlistFilter !== 'all_songs' && (
                    <div className="flex items-center gap-2" data-testid="playlist-filter-mode-toggle">
                      <button
                        type="button"
                        onClick={() => setPlaylistFilterMode('in')}
                        className={`px-3 py-1 rounded-full text-xs font-medium transition duration-200 ${
                          playlistFilterMode === 'in'
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                        data-testid="playlist-filter-mode-in"
                      >
                        In playlist
                      </button>
                      <button
                        type="button"
                        onClick={() => setPlaylistFilterMode('not_in')}
                        className={`px-3 py-1 rounded-full text-xs font-medium transition duration-200 ${
                          playlistFilterMode === 'not_in'
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                        data-testid="playlist-filter-mode-not-in"
                      >
                        Not in playlist
                      </button>
                    </div>
                  )}
                  
                  {/* Row 1: Genres (left) + Moods (right) */}
                  <div className="grid grid-cols-2 gap-3">
                    <select
                      value={genreFilter}
                      onChange={(e) => setGenreFilter(e.target.value)}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                    >
                      <option value="">All Genres</option>
                      <option value="__NO_GENRE__">🚫 No Genre</option>
                      {filterOptions.genres?.map((genre) => (
                        <option key={genre} value={genre}>{genre}</option>
                      ))}
                    </select>
                    
                    <select
                      value={moodFilter}
                      onChange={(e) => setMoodFilter(e.target.value)}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                    >
                      <option value="">All Moods</option>
                      <option value="__NO_MOOD__">🚫 No Mood</option>
                      {filterOptions.moods?.map((mood) => (
                        <option key={mood} value={mood}>{mood}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* Row 2: Years (left) + Decades (right) */}
                  <div className="grid grid-cols-2 gap-3">
                    <select
                      value={yearFilter}
                      onChange={(e) => setYearFilter(e.target.value)}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                    >
                      <option value="">All Years</option>
                      <option value="__NO_YEAR__">🚫 No Year</option>
                      {filterOptions.years?.map((year) => (
                        <option key={year} value={year}>{year}</option>
                      ))}
                    </select>
                    
                    <select
                      value={decadeFilter}
                      onChange={(e) => setDecadeFilter(e.target.value)}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                    >
                      <option value="">All Decades</option>
                      {filterOptions.decades?.map((decade) => (
                        <option key={decade} value={decade}>{decade}</option>
                      ))}
                    </select>
                  </div>
                  
                  {/* Notes Search - Full Width */}
                  <input
                    type="text"
                    placeholder="Search notes..."
                    value={notesFilter}
                    onChange={(e) => setNotesFilter(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm"
                  />
                </div>

                {/* Learn Later Toggle and Section */}
                <div className="mb-4">
                  <button
                    onClick={() => setShowLearnLater(!showLearnLater)}
                    className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition duration-300 ${
                      showLearnLater 
                        ? 'bg-yellow-600 text-white' 
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    <span>📚</span>
                    <span>Learn Later</span>
                    {songSuggestions.filter(s => s.status === 'learn_later').length > 0 && (
                      <span className="bg-yellow-500 text-white text-xs px-2 py-0.5 rounded-full ml-1">
                        {songSuggestions.filter(s => s.status === 'learn_later').length}
                      </span>
                    )}
                  </button>
                </div>

                {/* Learn Later Content */}
                {showLearnLater && (
                  <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4 mb-6">
                    <h3 className="text-lg font-bold text-yellow-400 mb-3">📚 Songs to Learn Later</h3>
                    {songSuggestions.filter(s => s.status === 'learn_later').length === 0 ? (
                      <p className="text-gray-400 text-sm">
                        No songs marked as "Learn Later" yet. Use the Learn Later action on suggestions to add songs here.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {songSuggestions.filter(s => s.status === 'learn_later').map((suggestion) => (
                          <div key={suggestion.id} className="bg-gray-700 p-3 rounded-lg flex items-center justify-between">
                            <div>
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-yellow-400">{suggestion.suggested_title}</span>
                                <span className="text-gray-400">by {suggestion.suggested_artist}</span>
                              </div>
                              <p className="text-xs text-gray-400 mt-1">
                                Suggested by {suggestion.requester_name}
                                {suggestion.message && <span className="italic ml-1">- "{suggestion.message}"</span>}
                              </p>
                            </div>
                            <div className="flex items-center space-x-1">
                              <button
                                onClick={() => setMatchingSuggestion(suggestion)}
                                className="bg-green-600 hover:bg-green-700 text-xs px-2 py-1 rounded"
                                title="Match to existing song in your library"
                              >
                                Match
                              </button>
                              <button
                                onClick={() => handleSuggestionAction(suggestion.id, 'added', suggestion.suggested_title)}
                                className="bg-blue-600 hover:bg-blue-700 text-xs px-2 py-1 rounded"
                                title="Add as new song"
                              >
                                Add
                              </button>
                              <button
                                onClick={() => handleDeleteSuggestion(suggestion.id, suggestion.suggested_title)}
                                className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1 rounded"
                                title="Delete permanently"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

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
                      <div className="flex flex-wrap gap-2 justify-center sm:justify-start">
                        {(() => {
                          const isRealPlaylistFilter = playlistFilter && playlistFilter !== 'all_songs';
                          const selectedPlaylist = isRealPlaylistFilter ? playlists.find(p => p.id === playlistFilter) : null;
                          if (selectedPlaylist && playlistFilterMode === 'in') {
                            return (
                              <button
                                onClick={bulkRemoveFromFilteredPlaylist}
                                className="bg-orange-600 hover:bg-orange-700 px-3 py-1 rounded text-sm font-medium transition duration-300 flex-shrink-0"
                                data-testid="bulk-remove-from-playlist-btn"
                              >
                                Remove from Playlist ({selectedSongs.size})
                              </button>
                            );
                          }
                          if (selectedPlaylist && playlistFilterMode === 'not_in') {
                            return (
                              <button
                                onClick={bulkAddToFilteredPlaylist}
                                className="bg-yellow-600 hover:bg-yellow-700 px-3 py-1 rounded text-sm font-medium transition duration-300 flex-shrink-0"
                                data-testid="bulk-add-to-filtered-playlist-btn"
                              >
                                Add to {selectedPlaylist.name} ({selectedSongs.size})
                              </button>
                            );
                          }
                          return (
                            <button
                              onClick={() => setShowPlaylistModal(true)}
                              className="bg-yellow-600 hover:bg-yellow-700 px-3 py-1 rounded text-sm font-medium transition duration-300 flex-shrink-0"
                            >
                              Add to Playlist ({selectedSongs.size})
                            </button>
                          );
                        })()}
                        <button
                          onClick={() => setShowBatchEdit(!showBatchEdit)}
                          className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm font-medium transition duration-300 flex-shrink-0"
                        >
                          Edit Selected ({selectedSongs.size})
                        </button>
                        <button
                          onClick={handleBatchDelete}
                          className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm font-medium transition duration-300 flex-shrink-0"
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
                        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start">
                          <div className="flex-1">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2 mb-1">
                              <h3 className={`font-bold text-base sm:text-lg ${song.hidden ? 'text-gray-400' : 'text-white'} break-words`}>
                                {song.title}
                              </h3>
                              {song.hidden && (
                                <span className="bg-gray-600 text-gray-300 text-xs px-2 py-1 rounded-full font-medium self-start mt-1 sm:mt-0">
                                  👁️‍🗨️ Hidden
                                </span>
                              )}
                            </div>
                            <p className={`text-sm sm:text-base ${song.hidden ? 'text-gray-500' : 'text-gray-300'} break-words`}>
                              by {song.artist}
                            </p>
                            <div className="flex flex-wrap gap-1 sm:gap-2 mt-2">
                              {song.genres.map((genre, index) => (
                                <span key={index} className="bg-purple-600 text-xs px-2 py-1 rounded-full whitespace-nowrap">
                                  {genre}
                                </span>
                              ))}
                              {song.moods.map((mood, index) => (
                                <span key={index} className="bg-blue-600 text-xs px-2 py-1 rounded-full whitespace-nowrap">
                                  {mood}
                                </span>
                              ))}
                              {song.year && (
                                <span className="bg-green-600 text-xs px-2 py-1 rounded-full whitespace-nowrap">
                                  {song.year}
                                </span>
                              )}
                              {/* Request Count Badge: show-scoped, hidden when zero */}
                              {(song.requests_this_show || 0) > 0 && (
                                <span
                                  data-testid={`song-tonight-badge-${song.id}`}
                                  className="bg-orange-600 text-xs px-2 py-1 rounded-full font-semibold whitespace-nowrap"
                                >
                                  🔥 {song.requests_this_show} tonight
                                </span>
                              )}
                            </div>
                            {song.notes && (
                              <p className={`text-sm mt-1 ${song.hidden ? 'text-gray-500' : 'text-gray-400'}`}>
                                {song.notes}
                              </p>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1 sm:gap-2 ml-2 sm:ml-4 mt-2 sm:mt-0">
                            <button
                              onClick={() => handleEditSong(song)}
                              className="bg-blue-600 hover:bg-blue-700 px-2 sm:px-3 py-1 rounded text-xs sm:text-sm font-medium transition duration-300 whitespace-nowrap"
                            >
                              Edit
                            </button>
                            {renderLearnLaterBookmark({ song, size: 20 })}
                            {/* NEW: Hide/Show Button */}
                            <button
                              onClick={() => handleToggleSongVisibility(song.id)}
                              className={`px-2 sm:px-3 py-1 rounded text-xs sm:text-sm font-medium transition duration-300 whitespace-nowrap ${
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
                              className="bg-red-600 hover:bg-red-700 px-2 sm:px-3 py-1 rounded text-xs sm:text-sm font-medium transition duration-300 whitespace-nowrap"
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
                      setPlaylistFilter('');
                      setMoodFilter('');
                      setYearFilter('');
                      setDecadeFilter('');
                      setNotesFilter('');
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
            {/* NEW: Redesigned Header with Action Buttons */}
            <div className="mb-6">
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
                {/* Song Suggestions Button */}
                <button
                  onClick={() => {
                    // Auto-scroll to Song Suggestions section
                    setTimeout(() => {
                      const suggestionSection = document.getElementById('song-suggestions-section');
                      if (suggestionSection) {
                        suggestionSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      }
                    }, 100);
                  }}
                  className="flex-1 px-4 py-3 rounded-lg font-medium transition duration-300 flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700"
                >
                  <span>💡</span>
                  <span>Song Suggestions</span>
                  {songSuggestions.filter(s => s.status === 'pending').length > 0 && (
                    <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                      {songSuggestions.filter(s => s.status === 'pending').length}
                    </span>
                  )}
                </button>
                
                {/* Start/Stop Show Button — per-profile live banners (Sprint 2: shows are profile-scoped) */}
                {(() => {
                  const liveProfiles = (profiles || []).filter(p => p && p.current_show_id);
                  if (liveProfiles.length === 0) {
                    return (
                      <button
                        onClick={() => setShowStartModal(true)}
                        className="flex-1 px-4 py-3 rounded-lg font-medium transition duration-300 flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700"
                        data-testid="start-a-show-btn"
                      >
                        <span>🎭</span>
                        <span>Start a Show</span>
                      </button>
                    );
                  }
                  return (
                    <div className="flex-1 flex flex-col gap-2" data-testid="live-shows-banners">
                      {liveProfiles.map(p => (
                        <div
                          key={p.id}
                          data-testid={`live-show-banner-${p.id}`}
                          className="flex items-center justify-between bg-green-600 px-4 py-3 rounded-lg"
                        >
                          <div className="flex items-center space-x-2 min-w-0">
                            <span className="text-sm font-medium truncate">
                              🎤 Live: {p.name} ({p.current_show_name})
                            </span>
                          </div>
                          <button
                            onClick={() => handleStopShowForProfile(p.id, p.current_show_name)}
                            className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm font-medium transition duration-300 shrink-0 ml-3"
                            data-testid={`stop-show-btn-${p.id}`}
                          >
                            Stop Show
                          </button>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Batch Actions Bar */}
            {selectedRequests.size > 0 && (
              <div className="bg-purple-900/30 border border-purple-500/50 rounded-lg p-4 mb-6">
                <div className="flex items-center justify-between">
                  <span className="text-purple-200 font-medium">
                    {selectedRequests.size} request(s) selected
                  </span>
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => batchUpdateRequestStatus('played')}
                      className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
                    >
                      🎵 Mark as Played
                    </button>
                    <button
                      onClick={() => batchUpdateRequestStatus('rejected')}
                      className="bg-red-600 hover:bg-red-700 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
                    >
                      ❌ Mark as Skipped
                    </button>
                    <button
                      onClick={batchArchiveRequests}
                      className="bg-gray-600 hover:bg-gray-700 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
                      title="Archive selected requests (hide from active view)"
                    >
                      📦 Archive
                    </button>
                    <button
                      onClick={batchDeleteRequests}
                      className="bg-gray-700 hover:bg-red-700 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
                      title="Permanently delete selected requests"
                    >
                      🗑️ Delete
                    </button>
                    <button
                      onClick={clearRequestSelection}
                      className="bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded-lg text-sm font-medium transition duration-300"
                    >
                      Clear Selection
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Profile + Event Filters */}
            {profiles.length > 0 && (
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <span className="text-gray-400 text-sm">Filter:</span>
                <select
                  data-testid="request-profile-filter"
                  value={profileFilterId}
                  onChange={(e) => setProfileFilterId(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm"
                >
                  <option value="">All Profiles</option>
                  <option value="main">Main (no profile)</option>
                  {profiles.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                {events.length > 0 && (
                  <select
                    data-testid="request-event-filter"
                    value={eventFilterId}
                    onChange={(e) => setEventFilterId(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm"
                  >
                    <option value="">All Events</option>
                    <option value="__none__">No event</option>
                    {events.map(ev => (
                      <option key={ev.id} value={ev.id}>{ev.name}</option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {/* Empty State: No Active Show */}
            {!currentShow && (
              <div>
                <div className="bg-gray-700/50 rounded-lg p-8 text-center mb-6">
                  <div className="text-4xl mb-4">🎤</div>
                  <h3 className="text-xl font-semibold mb-2">No Active Show</h3>
                  <p className="text-gray-400 mb-4">
                    Start a show or wait for your first request to arrive.
                  </p>
                </div>
              </div>
            )}
            
            {/* Active Shows Folders (MOVED ABOVE ALL REQUESTS) */}
            {shows.filter(show => show.status !== 'archived').length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4">🎭 Shows</h3>
                <div className="space-y-3">
                  {shows.filter(show => show.status !== 'archived').map((show) => (
                    <details key={show.id} className="bg-gray-700 rounded-lg">
                      <summary className="cursor-pointer p-4 font-medium hover:bg-gray-600 rounded-lg transition duration-300">
                        <div className="flex flex-col gap-2">
                          <div className="break-words">
                            📁 {show.name} ({show.date || 'No date'})
                          </div>
                          <div className="flex justify-between items-center gap-3">
                            <span className="text-gray-400 text-sm">
                              {requests.filter(r => r.show_id === show.id).length} requests · {songSuggestions.filter(s => s.show_id === show.id && s.status === 'pending').length} suggestions
                            </span>
                            <div className="flex items-center space-x-1 shrink-0">
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  exportShowRequestsCSV(show);
                                }}
                                data-testid={`export-csv-${show.id}`}
                                className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition duration-300"
                                title={`Export CSV of requests for "${show.name}"`}
                                aria-label={`Export CSV for ${show.name}`}
                              >
                                📤
                              </button>
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleArchiveShow(show.id, show.name);
                                }}
                                className="bg-orange-600 hover:bg-orange-700 text-white text-xs px-2 py-1 rounded transition duration-300"
                                title={`Archive show "${show.name}" (moves to bottom, preserves requests)`}
                                aria-label={`Archive ${show.name}`}
                              >
                                📦
                              </button>
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleDeleteShow(show.id, show.name);
                                }}
                                className="bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-1 rounded transition duration-300"
                                title={`Delete show "${show.name}" and all requests permanently`}
                                aria-label={`Delete ${show.name}`}
                              >
                                🗑️
                              </button>
                            </div>
                          </div>
                        </div>
                      </summary>
                      <div className="px-4 pb-4 space-y-4">
                        {/* Requests Section */}
                        <details open className="bg-gray-600/50 rounded-lg">
                          <summary className="cursor-pointer p-3 font-medium hover:bg-gray-600 rounded-lg transition duration-300 flex justify-between items-center">
                            <div className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                onClick={(e) => e.stopPropagation()}
                                onChange={(e) => {
                                  const showRequests = requests.filter(r => r.show_id === show.id);
                                  if (e.target.checked) {
                                    selectAllRequests(showRequests);
                                  } else {
                                    clearRequestSelection();
                                  }
                                }}
                                className="rounded bg-gray-600 border-gray-500 text-purple-600 focus:ring-purple-500 focus:ring-offset-0"
                                title="Select all requests"
                              />
                              <span>🎵 Requests ({requests.filter(r => r.show_id === show.id).length})</span>
                            </div>
                          </summary>
                          <div className="p-3 space-y-2">
                            {requests.filter(r => r.show_id === show.id).length === 0 ? (
                              <p className="text-gray-400 text-sm italic">No requests for this show</p>
                            ) : (
                              requests.filter(r => r.show_id === show.id)
                                .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                                .map((request) => (
                                <div
                                  key={request.id}
                                  data-testid={`request-card-${request.id}`}
                                  className="bg-gray-600 p-3 rounded flex items-center gap-3"
                                >
                                  <label className="flex items-center justify-center p-2 -m-2 cursor-pointer" onClick={(e) => e.stopPropagation()}>
                                    <input
                                      type="checkbox"
                                      checked={selectedRequests.has(request.id)}
                                      onChange={() => toggleRequestSelection(request.id)}
                                      className="h-5 w-5 rounded bg-gray-600 border-gray-500 text-purple-600 focus:ring-purple-500 focus:ring-offset-0"
                                      data-testid={`request-checkbox-${request.id}`}
                                    />
                                  </label>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      if (selectedRequests.size >= 2) {
                                        setBulkRequestModalOpen(true);
                                      } else {
                                        setSingleRequestModal(request);
                                      }
                                    }}
                                    data-testid={`request-card-body-${request.id}`}
                                    className="flex-1 min-w-0 flex items-center justify-between gap-2 text-left"
                                  >
                                    <div className="min-w-0">
                                      <div className="font-medium text-blue-400 text-sm truncate">{request.song_title}</div>
                                      <div className="text-xs text-gray-300 truncate">From: {request.requester_name}</div>
                                    </div>
                                    <span className={`shrink-0 px-2 py-1 rounded text-xs font-medium ${
                                      request.status === 'pending' ? 'bg-yellow-600/20 text-yellow-400' :
                                      request.status === 'played' ? 'bg-blue-600/20 text-blue-400' :
                                      request.status === 'archived' ? 'bg-gray-500/30 text-gray-300' :
                                      'bg-red-600/20 text-red-400'
                                    }`}>
                                      {getStatusLabel(request.status)}
                                    </span>
                                  </button>
                                </div>
                              ))
                            )}
                          </div>
                        </details>
                        
                        {/* Suggestions Section */}
                        <details className="bg-gray-600/50 rounded-lg">
                          <summary className="cursor-pointer p-3 font-medium hover:bg-gray-600 rounded-lg transition duration-300 flex justify-between items-center">
                            <div className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                onClick={(e) => e.stopPropagation()}
                                onChange={(e) => {
                                  const showSuggestions = songSuggestions.filter(s => s.show_id === show.id && s.status === 'pending');
                                  if (e.target.checked) {
                                    selectAllSuggestions(showSuggestions);
                                  } else {
                                    clearSuggestionSelection();
                                  }
                                }}
                                className="rounded bg-gray-600 border-gray-500 text-yellow-600 focus:ring-yellow-500 focus:ring-offset-0"
                                title="Select all suggestions"
                              />
                              <span>💡 Suggestions ({songSuggestions.filter(s => s.show_id === show.id && s.status === 'pending').length})</span>
                            </div>
                            {selectedSuggestions.size > 0 && songSuggestions.filter(s => s.show_id === show.id && selectedSuggestions.has(s.id)).length > 0 && (
                              <div className="flex space-x-1" onClick={(e) => e.stopPropagation()}>
                                <button
                                  onClick={() => batchSuggestionAction('learn_later')}
                                  className="bg-yellow-600 hover:bg-yellow-700 text-white text-xs px-2 py-1 rounded"
                                  title="Mark selected as Learn Later"
                                >
                                  📚 Learn Later
                                </button>
                                <button
                                  onClick={() => batchSuggestionAction('rejected')}
                                  className="bg-orange-600 hover:bg-orange-700 text-white text-xs px-2 py-1 rounded"
                                  title="Skip selected"
                                >
                                  ⏭️ Skip
                                </button>
                                <button
                                  onClick={() => batchDeleteSuggestions()}
                                  className="bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-1 rounded"
                                  title="Delete selected permanently"
                                >
                                  🗑️ Trash
                                </button>
                              </div>
                            )}
                          </summary>
                          <div className="p-3 space-y-2">
                            {songSuggestions.filter(s => s.show_id === show.id && s.status === 'pending').length === 0 ? (
                              <p className="text-gray-400 text-sm italic">No suggestions for this show</p>
                            ) : (
                              songSuggestions.filter(s => s.show_id === show.id && s.status === 'pending')
                                .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                                .map((suggestion) => (
                                <div key={suggestion.id} className="bg-gray-600 p-3 rounded flex items-center space-x-3">
                                  <input
                                    type="checkbox"
                                    checked={selectedSuggestions.has(suggestion.id)}
                                    onChange={() => toggleSuggestionSelection(suggestion.id)}
                                    className="rounded bg-gray-600 border-gray-500 text-yellow-600 focus:ring-yellow-500 focus:ring-offset-0"
                                  />
                                  <div className="flex-1">
                                    <div className="flex items-center space-x-2 mb-1">
                                      <span className="font-medium text-yellow-400 text-sm">{suggestion.suggested_title}</span>
                                      <span className="text-gray-400 text-sm">by {suggestion.suggested_artist}</span>
                                    </div>
                                    <p className="text-xs text-gray-300">
                                      Suggested by: {suggestion.requester_name}
                                      {suggestion.message && <span className="italic ml-1">"{suggestion.message}"</span>}
                                    </p>
                                  </div>
                                  <div className="flex items-center space-x-1">
                                    <button
                                      onClick={() => setMatchingSuggestion(suggestion)}
                                      className="bg-green-600 hover:bg-green-700 text-xs px-2 py-1 rounded"
                                      title="Match to existing song"
                                    >
                                      🎯 Match
                                    </button>
                                    <button
                                      onClick={() => handleLearnLater(suggestion.id)}
                                      className="bg-yellow-600 hover:bg-yellow-700 text-xs px-2 py-1 rounded"
                                      title="Learn it later"
                                    >
                                      📚
                                    </button>
                                    <button
                                      onClick={() => handleSuggestionAction(suggestion.id, 'rejected', suggestion.suggested_title)}
                                      className="bg-orange-600 hover:bg-orange-700 text-xs px-2 py-1 rounded"
                                      title="Skip"
                                    >
                                      ⏭️
                                    </button>
                                    <button
                                      onClick={() => handleDeleteSuggestion(suggestion.id, suggestion.suggested_title)}
                                      className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1 rounded"
                                      title="Delete permanently"
                                    >
                                      🗑️
                                    </button>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </details>
                      </div>
                    </details>
                  ))}
                </div>
              </div>
            )}
            
            {/* All Requests Section (NOW COLLAPSIBLE) */}
            {currentShow && (
              <div className="mb-6">
                <details open={showAllRequests} className="bg-gray-700 rounded-lg">
                  <summary 
                    className="cursor-pointer p-4 font-medium hover:bg-gray-600 rounded-lg transition duration-300 flex justify-between items-center"
                    onClick={(e) => {
                      e.preventDefault();
                      setShowAllRequests(!showAllRequests);
                    }}
                  >
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          e.stopPropagation();
                          const currentShowRequests = requests.filter(r => r.show_id === currentShow.id);
                          if (e.target.checked) {
                            selectAllRequests(currentShowRequests);
                          } else {
                            clearRequestSelection();
                          }
                        }}
                        className="rounded bg-gray-600 border-gray-500 text-purple-600 focus:ring-purple-500 focus:ring-offset-0"
                        title="Select all requests in current show"
                      />
                      <span>📥 Current Show: {currentShow.name}</span>
                      <span className="text-gray-400 text-sm">
                        ({requests.filter(r => r.show_id === currentShow.id).length} requests)
                      </span>
                    </div>
                  </summary>
                  <div className="px-4 pb-4 space-y-3">
                    {requests
                      .filter(r => r.show_id === currentShow.id)
                      .filter(r => !profileFilterId || (profileFilterId === 'main' ? !r.profile_id : r.profile_id === profileFilterId))
                      .filter(r => !eventFilterId || (eventFilterId === '__none__' ? !r.event_id : r.event_id === eventFilterId))
                      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at)) // Most recent first
                      .slice(0, 50).map((request) => (
                    <div
                      key={request.id}
                      data-testid={`request-card-${request.id}`}
                      className="p-4 rounded-lg flex items-center gap-3 bg-gray-600 border-l-4 border-green-500"
                    >
                      <label className="flex items-center justify-center p-2 -m-2 cursor-pointer" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedRequests.has(request.id)}
                          onChange={() => toggleRequestSelection(request.id)}
                          className="h-5 w-5 rounded bg-gray-600 border-gray-500 text-purple-600 focus:ring-purple-500 focus:ring-offset-0"
                          data-testid={`request-checkbox-${request.id}`}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => {
                          if (selectedRequests.size >= 2) {
                            setBulkRequestModalOpen(true);
                          } else {
                            setSingleRequestModal(request);
                          }
                        }}
                        data-testid={`request-card-body-${request.id}`}
                        className="flex-1 min-w-0 flex items-center justify-between gap-3 text-left"
                      >
                        <div className="min-w-0">
                          <div className="font-medium text-blue-400 truncate">{request.song_title}</div>
                          <div className="text-sm text-gray-300 truncate">
                            From: <span className="text-white">{request.requester_name}</span>
                          </div>
                        </div>
                        <span className={`shrink-0 px-2 py-1 rounded text-xs font-medium ${
                          request.status === 'pending' ? 'bg-yellow-600/20 text-yellow-400' :
                          request.status === 'played' ? 'bg-blue-600/20 text-blue-400' :
                          request.status === 'archived' ? 'bg-gray-500/30 text-gray-300' :
                          'bg-red-600/20 text-red-400'
                        }`}>
                          {getStatusLabel(request.status)}
                        </span>
                      </button>
                    </div>
                  ))}
                  {(currentShow ? 
                    requests.filter(r => r.show_id === currentShow.id).length === 0 :
                    requests.length === 0
                  ) && (
                    <p className="text-gray-400 text-center py-8">
                      {currentShow ? 
                        `No requests yet for ${currentShow.name}. Share your audience link to start receiving requests!` :
                        'No requests yet. Share your audience link to start receiving requests!'
                      }
                    </p>
                  )}
                  {(currentShow ? 
                    requests.filter(r => r.show_id === currentShow.id).length :
                    requests.length
                  ) > 50 && (
                    <p className="text-gray-400 text-center text-sm">
                      Showing 50 of {requests.filter(r => r.show_id === currentShow.id).length} requests
                    </p>
                  )}
                </div>
              </details>
            </div>
            )}
            
          </div>
        )}

        {/* Orphaned Suggestions Section - Only shows suggestions without a show_id (legacy data) */}
        {activeTab === 'requests' && songSuggestions.filter(s => !s.show_id && s.status === 'pending').length > 0 && (
          <div className="bg-gray-800 rounded-xl p-6 mb-6" id="song-suggestions-section">
            <details open={!suggestionsSectionCollapsed}>
              <summary 
                className="cursor-pointer list-none"
                onClick={(e) => {
                  e.preventDefault();
                  setSuggestionsSectionCollapsed(!suggestionsSectionCollapsed);
                }}
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-2">
                    <span className={`transition-transform ${suggestionsSectionCollapsed ? '' : 'rotate-90'}`}>▶</span>
                    <h3 className="text-lg font-bold text-yellow-400">💡 Unassigned Suggestions</h3>
                    <span className="bg-yellow-500 text-white text-xs px-2 py-1 rounded-full">
                      {songSuggestions.filter(s => !s.show_id && s.status === 'pending').length}
                    </span>
                  </div>
                </div>
              </summary>
              {!suggestionsSectionCollapsed && (
                <div className="mt-4 space-y-2">
                  <p className="text-gray-400 text-sm mb-3">These suggestions were submitted before show assignment was implemented. They will appear in future shows automatically.</p>
                  {songSuggestions.filter(s => !s.show_id && s.status === 'pending').map((suggestion) => (
                    <div key={suggestion.id} className="bg-gray-700 p-3 rounded flex items-center space-x-3">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="font-medium text-yellow-400 text-sm">{suggestion.suggested_title}</span>
                          <span className="text-gray-400 text-sm">by {suggestion.suggested_artist}</span>
                        </div>
                        <p className="text-xs text-gray-300">
                          Suggested by: {suggestion.requester_name}
                          {suggestion.message && <span className="italic ml-1">"{suggestion.message}"</span>}
                        </p>
                      </div>
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => setMatchingSuggestion(suggestion)}
                          className="bg-green-600 hover:bg-green-700 text-xs px-2 py-1 rounded"
                        >
                          🎯 Match
                        </button>
                        <button
                          onClick={() => handleLearnLater(suggestion.id)}
                          className="bg-yellow-600 hover:bg-yellow-700 text-xs px-2 py-1 rounded"
                        >
                          📚
                        </button>
                        <button
                          onClick={() => handleSuggestionAction(suggestion.id, 'rejected', suggestion.suggested_title)}
                          className="bg-orange-600 hover:bg-orange-700 text-xs px-2 py-1 rounded"
                        >
                          ⏭️
                        </button>
                        <button
                          onClick={() => handleDeleteSuggestion(suggestion.id, suggestion.suggested_title)}
                          className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1 rounded"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </details>
          </div>
        )}
        
        {/* Requests Tab — Single Request Action Modal (mobile-first post-show review) */}
        {activeTab === 'requests' && singleRequestModal && (
          <div
            className="fixed inset-0 bg-black/60 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4"
            onClick={() => setSingleRequestModal(null)}
            data-testid="single-request-modal"
          >
            <div
              className="bg-gray-800 rounded-t-2xl sm:rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-5 border-b border-gray-700 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-lg font-bold text-white truncate" data-testid="single-request-modal-title">
                    {singleRequestModal.song_title}
                  </h3>
                  <p className="text-sm text-gray-400 truncate">by {singleRequestModal.song_artist}</p>
                </div>
                <button
                  onClick={() => setSingleRequestModal(null)}
                  className="text-gray-400 hover:text-white text-2xl leading-none"
                  data-testid="single-request-modal-close"
                  aria-label="Close"
                >
                  ×
                </button>
              </div>
              <div className="p-5 space-y-3 text-sm">
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500 mb-0.5">Requester</div>
                  <div className="text-white">{singleRequestModal.requester_name || 'Anonymous'}</div>
                </div>
                {singleRequestModal.requester_email && (
                  <div>
                    <div className="text-xs uppercase tracking-wide text-gray-500 mb-0.5">Email</div>
                    <div className="text-gray-200 break-all">{singleRequestModal.requester_email}</div>
                  </div>
                )}
                {singleRequestModal.dedication && (
                  <div>
                    <div className="text-xs uppercase tracking-wide text-gray-500 mb-0.5">Dedication</div>
                    <div className="text-gray-200 italic">"{singleRequestModal.dedication}"</div>
                  </div>
                )}
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500 mb-0.5">Submitted</div>
                  <div className="text-gray-300">{formatTimestamp(singleRequestModal.created_at)}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500 mb-0.5">Profile</div>
                  <div>
                    {singleRequestModal.profile_id ? (
                      <span className="bg-purple-600/20 text-purple-300 px-2 py-0.5 rounded text-xs">
                        {profiles.find(p => p.id === singleRequestModal.profile_id)?.name || 'Profile'}
                      </span>
                    ) : (
                      <span className="bg-gray-700/50 text-gray-400 px-2 py-0.5 rounded text-xs">Main</span>
                    )}
                    {singleRequestModal.event_id && (
                      <span className="ml-2 bg-yellow-600/20 text-yellow-300 px-2 py-0.5 rounded text-xs">
                        {events.find(ev => ev.id === singleRequestModal.event_id)?.name || 'Event'}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="p-4 border-t border-gray-700 grid grid-cols-2 gap-2">
                <button
                  onClick={async () => {
                    const id = singleRequestModal.id;
                    setSingleRequestModal(null);
                    await updateRequestStatus(id, 'played');
                  }}
                  className="bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium"
                  data-testid="single-request-action-played"
                >
                  Played
                </button>
                <button
                  onClick={async () => {
                    const id = singleRequestModal.id;
                    setSingleRequestModal(null);
                    await updateRequestStatus(id, 'rejected');
                  }}
                  className="bg-orange-600 hover:bg-orange-700 text-white py-3 rounded-lg font-medium"
                  data-testid="single-request-action-skip"
                >
                  Skip
                </button>
                <button
                  onClick={async () => {
                    const id = singleRequestModal.id;
                    setSingleRequestModal(null);
                    await archiveRequest(id);
                  }}
                  className="bg-gray-600 hover:bg-gray-700 text-white py-3 rounded-lg font-medium"
                  data-testid="single-request-action-archive"
                >
                  Archive
                </button>
                <button
                  onClick={() => {
                    const { id, song_title } = singleRequestModal;
                    setSingleRequestModal(null);
                    handleDeleteRequest(id, song_title);
                  }}
                  className="bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg font-medium"
                  data-testid="single-request-action-delete"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Requests Tab — Bulk Action Modal (2+ selected) */}
        {activeTab === 'requests' && bulkRequestModalOpen && selectedRequests.size >= 2 && (
          <div
            className="fixed inset-0 bg-black/60 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4"
            onClick={() => setBulkRequestModalOpen(false)}
            data-testid="bulk-request-modal"
          >
            <div
              className="bg-gray-800 rounded-t-2xl sm:rounded-2xl w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-5 border-b border-gray-700 flex items-center justify-between">
                <h3 className="text-lg font-bold text-white" data-testid="bulk-request-modal-count">
                  {selectedRequests.size} requests selected
                </h3>
                <button
                  onClick={() => setBulkRequestModalOpen(false)}
                  className="text-gray-400 hover:text-white text-2xl leading-none"
                  data-testid="bulk-request-modal-close"
                  aria-label="Close"
                >
                  ×
                </button>
              </div>
              <div className="p-4 space-y-2">
                <button
                  onClick={async () => {
                    setBulkRequestModalOpen(false);
                    await batchUpdateRequestStatus('played');
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium"
                  data-testid="bulk-request-action-played"
                >
                  Mark as Played
                </button>
                <button
                  onClick={async () => {
                    setBulkRequestModalOpen(false);
                    await batchArchiveRequests();
                  }}
                  className="w-full bg-gray-600 hover:bg-gray-700 text-white py-3 rounded-lg font-medium"
                  data-testid="bulk-request-action-archive"
                >
                  Archive
                </button>
                <button
                  onClick={async () => {
                    setBulkRequestModalOpen(false);
                    await batchDeleteRequests();
                  }}
                  className="w-full bg-red-600 hover:bg-red-700 text-white py-3 rounded-lg font-medium"
                  data-testid="bulk-request-action-delete"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Start Show Modal */}
        {showStartModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
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
                    data-testid="show-name-input"
                  />
                </div>
                
                {/* Playlist Filter Mode */}
                <div>
                  <label className="block text-gray-300 text-sm font-bold mb-2">Song Selection</label>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="playlistFilterMode"
                        value="all"
                        checked={showPlaylistFilterMode === 'all'}
                        onChange={() => setShowPlaylistFilterMode('all')}
                        className="w-4 h-4 text-blue-600"
                        data-testid="playlist-mode-all"
                      />
                      <span className="text-white">All songs</span>
                    </label>
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="playlistFilterMode"
                        value="selected"
                        checked={showPlaylistFilterMode === 'selected'}
                        onChange={() => setShowPlaylistFilterMode('selected')}
                        className="w-4 h-4 text-blue-600"
                        data-testid="playlist-mode-selected"
                      />
                      <span className="text-white">Selected playlists only</span>
                    </label>
                  </div>
                </div>
                
                {/* Playlist Checklist (only shown when "selected" mode) */}
                {showPlaylistFilterMode === 'selected' && (
                  <div className="bg-gray-700/50 rounded-lg p-3 max-h-48 overflow-y-auto">
                    <label className="block text-gray-400 text-xs font-medium mb-2">
                      Select playlists to enable for this show:
                    </label>
                    {playlists.filter(p => !p.is_deleted).length === 0 ? (
                      <p className="text-gray-500 text-sm italic">No playlists available. Create playlists in the Songs tab first.</p>
                    ) : (
                      <div className="space-y-2">
                        {playlists.filter(p => !p.is_deleted).map(playlist => (
                          <label key={playlist.id} className="flex items-center space-x-3 cursor-pointer hover:bg-gray-600/50 p-2 rounded">
                            <input
                              type="checkbox"
                              checked={showEnabledPlaylistIds.includes(playlist.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setShowEnabledPlaylistIds([...showEnabledPlaylistIds, playlist.id]);
                                } else {
                                  setShowEnabledPlaylistIds(showEnabledPlaylistIds.filter(id => id !== playlist.id));
                                }
                              }}
                              className="w-4 h-4 text-blue-600 rounded"
                              data-testid={`playlist-checkbox-${playlist.id}`}
                            />
                            <span className="text-white text-sm">{playlist.name}</span>
                            <span className="text-gray-400 text-xs">({playlist.song_ids?.length || 0} songs)</span>
                          </label>
                        ))}
                      </div>
                    )}
                    {showPlaylistFilterMode === 'selected' && showEnabledPlaylistIds.length === 0 && (
                      <p className="text-yellow-400 text-xs mt-2">⚠️ Select at least one playlist</p>
                    )}
                  </div>
                )}
                
                <p className="text-gray-400 text-sm">
                  {showPlaylistFilterMode === 'all' 
                    ? 'Audience will see all non-hidden songs.'
                    : `Audience will only see songs from selected playlist${showEnabledPlaylistIds.length !== 1 ? 's' : ''}.`}
                </p>
                <div className="flex space-x-3 mt-6">
                  <button
                    onClick={() => {
                      setShowStartModal(false);
                      setNewShowName('');
                      setShowPlaylistFilterMode('all');
                      setShowEnabledPlaylistIds([]);
                    }}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleStartShow}
                    disabled={!newShowName.trim() || (showPlaylistFilterMode === 'selected' && showEnabledPlaylistIds.length === 0)}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 py-2 rounded-lg font-medium transition duration-300 disabled:cursor-not-allowed"
                    data-testid="start-show-btn"
                  >
                    Start Show
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* NEW: Archived Shows Section - Bottom of Requests Tab */}
        {activeTab === 'requests' && shows.filter(show => show.status === 'archived').length > 0 && (
          <div className="bg-gray-800 rounded-xl p-6 mb-6">
            <details open={!archivedShowsCollapsed}>
              <summary 
                className="cursor-pointer list-none"
                onClick={(e) => {
                  e.preventDefault();
                  setArchivedShowsCollapsed(!archivedShowsCollapsed);
                }}
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-2">
                    <span className={`transition-transform ${archivedShowsCollapsed ? '' : 'rotate-90'}`}>▶</span>
                    <h3 className="text-lg font-bold text-gray-400">📦 Archived Shows</h3>
                    <span className="bg-gray-500 text-white text-xs px-2 py-1 rounded-full">
                      {shows.filter(show => show.status === 'archived').length}
                    </span>
                  </div>
                </div>
              </summary>

              {/* Archived Shows Content */}
              {!archivedShowsCollapsed && (
                <div className="mt-4 space-y-3">
                  {shows.filter(show => show.status === 'archived').map((show) => (
                    <details key={show.id} className="bg-gray-700 rounded-lg">
                      <summary className="cursor-pointer p-4 font-medium hover:bg-gray-600 rounded-lg transition duration-300 flex justify-between items-center">
                        <div className="flex items-center space-x-3">
                          <span>📁 {show.name} ({show.date || 'No date'})</span>
                          <span className="text-gray-400 text-xs">
                            Archived • {requests.filter(r => r.show_id === show.id).length} requests
                          </span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleRestoreShow(show.id, show.name);
                            }}
                            className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1 rounded transition duration-300"
                            title={`Restore show "${show.name}" to active status`}
                          >
                            🔄 Restore
                          </button>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleDeleteShow(show.id, show.name);
                            }}
                            className="bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-1 rounded transition duration-300"
                            title={`Delete show "${show.name}" and all requests permanently`}
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </summary>
                      
                      {/* Archived Show Requests */}
                      <div className="px-4 pb-4 space-y-2">
                        {requests.filter(r => r.show_id === show.id)
                          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at)) // Most recent first
                          .map((request) => (
                          <div key={request.id} className="bg-gray-600 p-3 rounded flex items-center justify-between opacity-75">
                            <div>
                              <h4 className="font-medium text-white">
                                {request.requester_email && <span className="text-gray-400 mr-2" title="Email provided">📧</span>}
                                {request.song_title}
                              </h4>
                              <p className="text-gray-300 text-sm">{request.song_artist}</p>
                              <p className="text-gray-400 text-xs">
                                From: {request.requester_name} • {formatTimestamp(request.created_at)}
                              </p>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              request.status === 'played' ? 'bg-green-600/50 text-green-200' :
                              request.status === 'rejected' ? 'bg-red-600/50 text-red-200' :
                              'bg-gray-600/50 text-gray-300'
                            }`}>
                              {request.status.toUpperCase()}
                            </span>
                          </div>
                        ))}
                        
                        {requests.filter(r => r.show_id === show.id).length === 0 && (
                          <div className="text-center py-4 text-gray-500">
                            <p className="text-sm">No requests in this archived show</p>
                          </div>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </details>
          </div>
        )}

        {/* NEW: Unassigned Requests panel — Requests tab bottom. Only rendered when at least one orphan exists. */}
        {activeTab === 'requests' && unassignedRequests.length > 0 && (
          <div className="mt-6" data-testid="unassigned-requests-panel">
            <button
              type="button"
              onClick={() => setUnassignedPanelOpen((v) => !v)}
              className="w-full flex items-center justify-between bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded-xl px-4 py-3 text-left transition"
              data-testid="unassigned-requests-toggle"
              aria-expanded={unassignedPanelOpen}
            >
              <div className="flex items-center gap-2">
                <span className="text-yellow-400">📥</span>
                <span className="font-semibold text-white">
                  Unassigned Requests ({unassignedRequests.length})
                </span>
              </div>
              <svg
                className={`w-4 h-4 text-gray-400 transition-transform ${unassignedPanelOpen ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {unassignedPanelOpen && (
              <div className="mt-3 space-y-3" data-testid="unassigned-requests-list">
                {unassignedRequests.map((r) => {
                  const sortedShows = [...(shows || [])].sort(
                    (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
                  );
                  return (
                    <div
                      key={r.id}
                      className="bg-gray-800 border border-gray-700 rounded-lg p-4"
                      data-testid={`unassigned-request-${r.id}`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-blue-300 truncate">{r.song_title}</p>
                          <p className="text-sm text-gray-300">
                            From: <span className="text-white">{r.requester_name || 'Anonymous'}</span>
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            Submitted {formatTimestamp(r.created_at)}
                          </p>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 shrink-0">
                          {unassignedAssignFor === r.id ? (
                            <select
                              autoFocus
                              defaultValue=""
                              data-testid={`unassigned-assign-select-${r.id}`}
                              onChange={(e) => {
                                const sid = e.target.value;
                                if (sid) handleAssignUnassignedToShow(r.id, sid);
                              }}
                              onBlur={() => setUnassignedAssignFor(null)}
                              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-white"
                            >
                              <option value="" disabled>
                                Select a show…
                              </option>
                              {sortedShows.length === 0 ? (
                                <option value="" disabled>
                                  No shows available
                                </option>
                              ) : (
                                sortedShows.map((s) => {
                                  const d =
                                    s.date ||
                                    (s.created_at ? new Date(s.created_at).toISOString().slice(0, 10) : '');
                                  return (
                                    <option key={s.id} value={s.id}>
                                      {s.name}{d ? ` (${d})` : ''}
                                    </option>
                                  );
                                })
                              )}
                            </select>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setUnassignedAssignFor(r.id)}
                              data-testid={`unassigned-assign-btn-${r.id}`}
                              className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-3 py-1 rounded transition"
                            >
                              Assign to Show
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleArchiveUnassigned(r.id)}
                            data-testid={`unassigned-archive-btn-${r.id}`}
                            className="bg-gray-600 hover:bg-gray-500 text-white text-xs px-3 py-1 rounded transition"
                          >
                            Archive
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteUnassigned(r.id, r.song_title)}
                            data-testid={`unassigned-delete-btn-${r.id}`}
                            className="bg-red-600 hover:bg-red-700 text-white text-xs px-3 py-1 rounded transition"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}



        {/* On Stage Tab - Dedicated tab for live performance management */}
        {activeTab === 'onstage' && (
          <div className="space-y-6">
            {/* Sprint 2 Prompt 4: Profile/Event selector (collapsible) */}
            <div data-testid="onstage-context-selector" className="bg-gray-800 rounded-xl">
              {(() => {
                const sel = onstageSelection ? onstageSelection.split(':') : [];
                const kind = sel[0];
                const id = sel[1];
                const ref = kind === 'profile' ? profiles.find(p => p.id === id)
                          : kind === 'event'   ? events.find(ev => ev.id === id)
                          : null;
                const parent = ref && kind === 'event' ? profiles.find(p => p.id === ref.profile_id) : null;
                const summaryLabel = ref
                  ? (kind === 'event'
                      ? `${ref.name} — ${parent?.name || 'profile'}${ref.status === 'live' ? ' • LIVE' : ''}`
                      : `${ref.name}${ref.is_default ? ' (Default)' : ''}`)
                  : 'Choose context';
                return (
                  <>
                    <button
                      type="button"
                      data-testid="onstage-selector-toggle"
                      onClick={() => setOnstageSelectorExpanded(!onstageSelectorExpanded)}
                      className="w-full p-3 flex items-center justify-between text-left hover:bg-gray-750"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="text-gray-400 text-sm shrink-0">Performing as:</span>
                        <span className="text-sm font-medium truncate" data-testid="onstage-selector-summary">{summaryLabel}</span>
                      </div>
                      <svg className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${onstageSelectorExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {onstageSelectorExpanded && (
                      <div className="px-3 pb-3 flex flex-wrap items-center gap-3 border-t border-gray-700 pt-3">
                        <select
                          data-testid="onstage-selector"
                          value={onstageSelection}
                          onChange={(e) => setOnstageSelection(e.target.value)}
                          className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm flex-1 min-w-[260px]"
                        >
                          <option value="">— choose context —</option>
                          {profiles.length > 0 && (
                            <optgroup label="Profiles">
                              {profiles.map(p => (
                                <option key={`p-${p.id}`} value={`profile:${p.id}`}>
                                  {p.name}{p.is_default ? ' (Default)' : ''}
                                </option>
                              ))}
                            </optgroup>
                          )}
                          {events.filter(ev => ev.status === 'live' || ev.status === 'upcoming').length > 0 && (
                            <optgroup label="Events">
                              {events.filter(ev => ev.status === 'live' || ev.status === 'upcoming').map(ev => {
                                const pp = profiles.find(p => p.id === ev.profile_id);
                                return (
                                  <option key={`e-${ev.id}`} value={`event:${ev.id}`}>
                                    {ev.name} — {pp?.name || 'profile'}{ev.status === 'live' ? ' • LIVE' : ''}
                                  </option>
                                );
                              })}
                            </optgroup>
                          )}
                        </select>
                        {ref && (
                          <span className="text-xs text-gray-400">
                            {ref.current_show_id
                              ? <>Active show: <span className="text-green-300">{ref.current_show_name}</span></>
                              : <>No active show on this {kind}</>}
                          </span>
                        )}
                      </div>
                    )}
                  </>
                );
              })()}
            </div>

            {/* Show empty state if no active show */}
            {!currentShow ? (
              <div className="text-center py-16 bg-gray-800/50 rounded-xl">
                <div className="text-6xl mb-4">🎤</div>
                <h2 className="text-2xl font-bold text-white mb-2">No Active Show</h2>
                <p className="text-gray-400 mb-6">Start a show to see live requests and manage your performance.</p>
                <button
                  onClick={() => setShowStartModal(true)}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-lg font-bold transition duration-300"
                  data-testid="start-show-btn"
                >
                  Start Show
                </button>
              </div>
            ) : (
            <>
            {/* Three-Panel Layout: Up Next | Active Requests | Completed Requests */}
            {/* NOTE: Up Next panel is conditionally rendered only when there are up_next songs */}
            {/* SCOPED: Only show requests/suggestions for the current active show */}
            <div className={`grid grid-cols-1 gap-6 ${
              requests.filter(r => r.show_id === currentShow.id && r.status === 'up_next').length > 0 
                ? 'lg:grid-cols-3' 
                : 'lg:grid-cols-2'
            }`}>
              
              {/* Up Next Panel - Only show if there are up_next songs for current show */}
              {requests.filter(r => r.show_id === currentShow.id && r.status === 'up_next').length > 0 && (
                <div className="bg-blue-900/50 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-blue-300">🎵 Up Next</h3>
                    <div className="text-sm text-gray-400">
                      {requests.filter(r => r.show_id === currentShow.id && r.status === 'up_next').length} songs
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    {requests
                      .filter(r => r.show_id === currentShow.id && r.status === 'up_next')
                      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
                      .map((request) => (
                        <div key={request.id} className="bg-blue-800/50 rounded-lg p-4">
                          <h4 className="font-bold text-lg text-white flex items-center gap-2">
                            {request.requester_email && <span className="text-gray-400" title="Email provided">📧</span>}
                            <span>{request.song_title}</span>
                            {renderLearnLaterBookmark({ songId: request.song_id, size: 18 })}
                          </h4>
                          <p className="text-blue-200">{request.song_artist}</p>
                          <p className="text-sm text-gray-300 mt-2">
                            From: <strong className="text-white">{request.requester_name}</strong>
                          </p>
                          {request.dedication && (
                            <p className="text-sm text-blue-200 mt-1 italic">
                              "{request.dedication}"
                            </p>
                          )}
                          
                          <div className="flex space-x-2 mt-3">
                            <button
                              onClick={() => updateRequestStatus(request.id, 'played')}
                              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition duration-300"
                            >
                              ✓ Played
                            </button>
                            <button
                              onClick={() => updateRequestStatus(request.id, 'rejected')}
                              className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition duration-300"
                            >
                              ✗ Skip
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Active Requests Panel - Scoped to current show */}
              <div className="bg-purple-900/50 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-purple-300">🎸 Live Requests</h3>
                  <div className="text-sm text-gray-400">
                    {(() => {
                      const activeReqs = requests.filter(r => r.show_id === currentShow.id && ['pending', 'accepted'].includes(r.status));
                      const pendingSuggs = songSuggestions.filter(s => s.show_id === currentShow.id && s.status === 'pending');
                      const totalActive = activeReqs.length + pendingSuggs.length;
                      return `${totalActive} active`;
                    })()}
                  </div>
                </div>
                
                <div className="space-y-3">
                  {(() => {
                    // Merge active requests and pending suggestions - scoped to current show
                    const activeReqs = requests.filter(r => r.show_id === currentShow.id && ['pending', 'accepted'].includes(r.status)).map(r => ({...r, type: 'request'}));
                    const pendingSuggs = songSuggestions.filter(s => s.show_id === currentShow.id && s.status === 'pending').map(s => ({
                      ...s,
                      type: 'suggestion',
                      song_title: s.suggested_title,
                      song_artist: s.suggested_artist,
                      dedication: s.message,
                      requester_name: s.requester_name
                    }));
                    const activeItems = [...activeReqs, ...pendingSuggs].sort((a, b) => 
                      new Date(a.created_at) - new Date(b.created_at)
                    );
                    
                    if (activeItems.length === 0) {
                      return (
                        <div className="text-center py-8 text-gray-400">
                          <p>No active requests or suggestions</p>
                        </div>
                      );
                    }
                    
                    return activeItems.map((item) => (
                      item.type === 'suggestion' ? (
                        // Render suggestion
                        <div key={item.id} className="bg-orange-900/30 rounded-lg p-4 border-l-4 border-orange-400">
                          <div className="flex justify-between items-start mb-2">
                            <span className="px-2 py-1 rounded-full text-xs font-bold bg-orange-600 text-white">
                              SUGGESTION
                            </span>
                          </div>
                          <h4 className="font-bold text-lg text-orange-100">
                            {item.suggested_title || item.song_title}
                          </h4>
                          <p className="text-orange-200">by {item.suggested_artist || item.song_artist}</p>
                          <p className="text-sm text-gray-300 mt-2">
                            From: <strong className="text-white">{item.requester_name}</strong>
                          </p>
                          {item.message && (
                            <p className="text-sm text-orange-200 mt-1 italic">
                              "{item.message}"
                            </p>
                          )}
                          <div className="flex space-x-2 mt-3">
                            <button
                              onClick={() => {
                                setMatchingSuggestion(item);
                                setSongSearchTerm('');
                                setSelectedMatchSongId('');
                              }}
                              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition duration-300"
                            >
                              Match to Song
                            </button>
                            <button
                              onClick={async () => {
                                try {
                                  const token = localStorage.getItem('token');
                                  await axios.put(
                                    `${API}/song-suggestions/${item.id}/learn-later`,
                                    {},
                                    { headers: { 'Authorization': `Bearer ${token}` } }
                                  );
                                  fetchSongSuggestions();
                                  fetchRequests(); // Also refetch requests
                                } catch (error) {
                                  showErrorToast(error.response?.data?.detail || 'Failed to mark as learn later', error);
                                }
                              }}
                              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition duration-300"
                            >
                              Learn it later
                            </button>
                            <button
                              onClick={async () => {
                                try {
                                  const token = localStorage.getItem('token');
                                  await axios.put(
                                    `${API}/song-suggestions/${item.id}/status`,
                                    { status: 'rejected' },
                                    { headers: { 'Authorization': `Bearer ${token}` } }
                                  );
                                  fetchSongSuggestions();
                                  fetchRequests(); // Also refetch requests
                                } catch (error) {
                                  showErrorToast(error.response?.data?.detail || 'Failed to skip suggestion', error);
                                }
                              }}
                              className="bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded text-sm transition duration-300"
                              title="Skip"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      ) : (
                        // Render normal request
                        <div key={item.id} className="bg-purple-800/50 rounded-lg p-4">
                          <h4 className="font-bold text-lg text-white flex items-center gap-2">
                            {item.requester_email && <span className="text-gray-400" title="Email provided">📧</span>}
                            <span>{item.song_title}</span>
                            {renderLearnLaterBookmark({ songId: item.song_id, size: 18 })}
                          </h4>
                          <p className="text-purple-200">{item.song_artist}</p>
                          <p className="text-sm text-gray-300 mt-2">
                            From: <strong className="text-white">{item.requester_name}</strong>
                          </p>
                          {item.dedication && (
                            <p className="text-sm text-purple-200 mt-1 italic">
                              "{item.dedication}"
                            </p>
                          )}
                          {item.tip_amount > 0 && (
                            <div className="text-sm text-green-400 mt-1 font-medium">
                              💰 ${item.tip_amount} tip
                            </div>
                          )}
                          
                          <div className="flex space-x-2 mt-3">
                            <button
                              onClick={() => updateRequestStatus(item.id, 'up_next')}
                              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition duration-300"
                            >
                              ↗ Up Next
                            </button>
                            <button
                              onClick={() => updateRequestStatus(item.id, 'played')}
                              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition duration-300"
                            >
                              ✓ Played
                            </button>
                            <button
                              onClick={() => updateRequestStatus(item.id, 'rejected')}
                              className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition duration-300"
                            >
                              ✗ Skip
                            </button>
                          </div>
                        </div>
                      )
                    ));
                  })()}
                </div>
              </div>

              {/* Handled Requests Panel - Scoped to current show */}
              <div className="bg-green-900/50 rounded-xl p-6">
                <div className="mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-bold text-green-300">✅ Handled</h3>
                      <p className="text-sm text-gray-400 mt-1">Played, skipped, or saved for later.</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="text-sm text-gray-400">
                        {requests.filter(r => r.show_id === currentShow.id && ['played', 'rejected'].includes(r.status)).length} done
                      </div>
                      <button
                        onClick={() => setCompletedSectionCollapsed(!completedSectionCollapsed)}
                        className="text-gray-400 hover:text-white transition-colors"
                      >
                        {completedSectionCollapsed ? '▼' : '▲'}
                      </button>
                    </div>
                  </div>
                </div>
                
                {!completedSectionCollapsed && (
                  <div className="space-y-3">
                    {(() => {
                      // Merge completed requests and handled suggestions - scoped to current show
                      const completedReqs = requests.filter(r => r.show_id === currentShow.id && ['played', 'rejected'].includes(r.status)).map(r => ({...r, type: 'request'}));
                      const handledSuggs = songSuggestions.filter(s => s.show_id === currentShow.id && (s.status === 'learn_later' || s.status === 'rejected')).map(s => ({
                        ...s,
                        type: 'suggestion',
                        song_title: s.suggested_title,
                        song_artist: s.suggested_artist,
                        dedication: s.message,
                        requester_name: s.requester_name,
                        status: s.status === 'learn_later' ? 'learn_later' : 'rejected'
                      }));
                      const completedItems = [...completedReqs, ...handledSuggs].sort((a, b) => 
                        new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)
                      ).slice(0, 10);
                      
                      if (completedItems.length === 0) {
                        return (
                          <div className="text-center py-8 text-gray-400">
                            <p>No completed requests yet</p>
                            <p className="text-sm mt-1">Played and skipped songs will appear here</p>
                          </div>
                        );
                      }
                      
                      return completedItems.map((item) => (
                        <CompletedRequestItem
                          key={item.id}
                          request={item}
                          onRestore={(itemId) => {
                            if (item.type === 'suggestion') {
                              // Restore suggestion by setting status back to pending
                              const token = localStorage.getItem('token');
                              axios.put(
                                `${API}/song-suggestions/${itemId}/status`,
                                { status: 'pending' },
                                { headers: { 'Authorization': `Bearer ${token}` } }
                              ).then(() => {
                                fetchSongSuggestions();
                              }).catch((error) => {
                                showErrorToast(error.response?.data?.detail || 'Failed to restore suggestion', error);
                              });
                            } else {
                              updateRequestStatus(itemId, 'accepted');
                            }
                          }}
                          compact={true}
                        />
                      ));
                    })()}
                  </div>
                )}
                
                {completedSectionCollapsed && (
                  <div className="text-center py-4 text-gray-400">
                    <p className="text-sm">Collapsed - Click to expand</p>
                  </div>
                )}
              </div>
            </div>
            </>
            )}
          </div>
        )}

        {/* Song Picker Modal for Matching Suggestions */}
        {matchingSuggestion && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
              <h3 className="text-xl font-bold mb-4">Match "{matchingSuggestion.suggested_title}" to a Song</h3>
              
              <input
                type="text"
                placeholder="Search your songs..."
                value={songSearchTerm}
                onChange={(e) => setSongSearchTerm(e.target.value)}
                className="w-full p-3 mb-4 rounded bg-gray-700 text-white border border-gray-600"
                autoFocus
              />
              
              <div className="space-y-2 mb-4 max-h-96 overflow-y-auto">
                {songs
                  .filter(song => 
                    song.title.toLowerCase().includes(songSearchTerm.toLowerCase()) ||
                    song.artist.toLowerCase().includes(songSearchTerm.toLowerCase())
                  )
                  .slice(0, 20)
                  .map(song => (
                    <div
                      key={song.id}
                      onClick={() => setSelectedMatchSongId(song.id)}
                      className={`p-3 rounded cursor-pointer transition ${
                        selectedMatchSongId === song.id 
                          ? 'bg-purple-600' 
                          : 'bg-gray-700 hover:bg-gray-600'
                      }`}
                    >
                      <div className="font-bold">{song.title}</div>
                      <div className="text-sm text-gray-400">{song.artist}</div>
                    </div>
                  ))}
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={async () => {
                    if (!selectedMatchSongId) {
                      showErrorToast('Please select a song first');
                      return;
                    }
                    
                    try {
                      const token = localStorage.getItem('token');
                      await axios.put(
                        `${API}/song-suggestions/${matchingSuggestion.id}/match`,
                        { song_id: selectedMatchSongId },
                        { headers: { 'Authorization': `Bearer ${token}` } }
                      );
                      setMatchingSuggestion(null);
                      fetchSongSuggestions();
                      fetchRequests(); // Refetch to show new request
                    } catch (error) {
                      showErrorToast(error.response?.data?.detail || 'Failed to match suggestion to song', error);
                    }
                  }}
                  disabled={!selectedMatchSongId}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed py-3 px-4 rounded-lg font-bold text-white transition"
                >
                  Confirm Match
                </button>
                <button
                  onClick={() => setMatchingSuggestion(null)}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 py-3 px-4 rounded-lg font-bold text-white transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div data-testid="profiles-tab">
            {/* Create New Profile Button */}
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Performance Profiles</h2>
              <button
                data-testid="create-profile-btn"
                onClick={() => openProfileEditor()}
                className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg font-medium transition duration-300"
              >
                + Create New Profile
              </button>
            </div>

            {/* Profile List */}
            {profiles.length === 0 ? (
              <div className="bg-gray-800 rounded-xl p-8 text-center mb-8">
                <div className="text-4xl mb-4">🎭</div>
                <h3 className="text-lg font-semibold mb-2">No Profiles Yet</h3>
                <p className="text-gray-400 mb-4">Create performance profiles to give each gig its own audience URL, playlist selection, and tip settings.</p>
                <button
                  onClick={() => openProfileEditor()}
                  className="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded-lg font-medium transition duration-300"
                >
                  Create Your First Profile
                </button>
              </div>
            ) : (
              <div className="space-y-4 mb-8">
                {profiles.map(p => {
                  const profileUrl = p.is_default
                    ? `${AUDIENCE_BASE_URL}/musician/${musician.slug}`
                    : `${AUDIENCE_BASE_URL}/musician/${musician.slug}/${p.slug}`;
                  return (
                    <div key={p.id} data-testid={`profile-card-${p.slug}`} className={`bg-gray-800 rounded-xl p-5 ${p.is_default ? 'ring-1 ring-purple-500/50' : ''}`}>
                      <div className="flex flex-col gap-3">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h3 className="text-lg font-semibold text-white">{p.name}</h3>
                              {p.is_default && (
                                <span className="text-xs bg-purple-600 text-white px-2 py-0.5 rounded-full">Default</span>
                              )}
                            </div>
                            <a href={profileUrl} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 text-sm truncate block underline">{profileUrl}</a>
                            <div className="flex flex-wrap gap-2 mt-2">
                              {p.active_playlist_ids.includes('__all__') ? (
                                <span className="text-xs bg-green-600/30 text-green-300 px-2 py-1 rounded">All Songs</span>
                              ) : p.active_playlist_ids.length > 0 && (
                                <span className="text-xs bg-purple-600/30 text-purple-300 px-2 py-1 rounded">
                                  {p.active_playlist_ids.length} playlist{p.active_playlist_ids.length !== 1 ? 's' : ''}
                                </span>
                              )}
                              {!p.show_tips_in_success_screen && (
                                <span className="text-xs bg-gray-700 text-gray-400 px-2 py-1 rounded">Tips hidden (success)</span>
                              )}
                              {!p.show_tips_in_orientation && (
                                <span className="text-xs bg-gray-700 text-gray-400 px-2 py-1 rounded">Tips hidden (info)</span>
                              )}
                              {p.musician_name && (
                                <span className="text-xs bg-blue-600/20 text-blue-300 px-2 py-1 rounded">Name: {p.musician_name}</span>
                              )}
                            </div>
                          </div>
                        </div>
                        {/* Action buttons - always visible */}
                        <div className="flex items-center gap-2 flex-wrap border-t border-gray-700 pt-3">
                          <button
                            data-testid={`copy-url-${p.slug}`}
                            onClick={(e) => {
                              const btn = e.currentTarget;
                              navigator.clipboard.writeText(profileUrl).then(() => {
                                btn.textContent = 'Copied!';
                                setTimeout(() => { btn.textContent = 'Copy URL'; }, 2000);
                              }).catch(() => {});
                            }}
                            className="bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded-lg text-sm transition duration-300"
                          >
                            Copy URL
                          </button>
                          <button
                            data-testid={`qr-btn-${p.slug}`}
                            onClick={async () => {
                              try {
                                const response = await axios.get(`${API}/qr-code?url=${encodeURIComponent(profileUrl)}`);
                                const qrWindow = window.open('', '_blank');
                                qrWindow.document.write(`<html><body style="display:flex;justify-content:center;align-items:center;min-height:100vh;background:#1a1a2e;margin:0"><img src="${response.data.qr_code}" style="max-width:400px" /></body></html>`);
                              } catch (err) { alert('Error generating QR code'); }
                            }}
                            className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-lg text-sm transition duration-300"
                          >
                            QR
                          </button>
                          <button
                            data-testid={`edit-profile-${p.slug}`}
                            onClick={() => openProfileEditor(p)}
                            className="bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded-lg text-sm transition duration-300"
                          >
                            Edit
                          </button>
                          {!p.is_default && (
                            <button
                              data-testid={`set-default-${p.slug}`}
                              onClick={async () => {
                                try {
                                  await axios.put(`${API}/profiles/${p.id}`, { is_default: true });
                                  fetchProfiles();
                                } catch (err) { alert(err.response?.data?.detail || 'Error setting default'); }
                              }}
                              className="bg-yellow-600/20 hover:bg-yellow-600 text-yellow-400 hover:text-white px-3 py-2 rounded-lg text-sm transition duration-300"
                            >
                              Set Default
                            </button>
                          )}
                          {!p.is_default && (
                            <button
                              data-testid={`delete-profile-${p.slug}`}
                              onClick={() => handleDeleteProfile(p.id)}
                              className="bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white px-3 py-2 rounded-lg text-sm transition duration-300"
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Profile Editor Modal */}
            {showProfileEditor && (
              <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={(e) => { if (e.target === e.currentTarget) setShowProfileEditor(false); }}>
                <div data-testid="profile-editor-modal" className="bg-gray-800 rounded-xl p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto">
                  <h2 className="text-xl font-bold mb-4">{editingProfile ? 'Edit Profile' : 'Create New Profile'}</h2>
                  {/* Copy from Default Profile button */}
                  <button
                    data-testid="copy-from-default-btn"
                    type="button"
                    onClick={() => {
                      const defaultProfile = profiles.find(p => p.is_default);
                      if (!defaultProfile) {
                        alert('No default profile found');
                        return;
                      }
                      setProfileForm(prev => ({
                        ...prev,
                        musician_name: defaultProfile.musician_name || '',
                        bio: defaultProfile.bio || '',
                        website: defaultProfile.website || '',
                        venmo_username: defaultProfile.venmo_username || '',
                        paypal_username: defaultProfile.paypal_username || '',
                        cashapp_username: defaultProfile.cashapp_username || '',
                        zelle_info: defaultProfile.zelle_info || '',
                        instagram_username: defaultProfile.instagram_username || '',
                        tiktok_username: defaultProfile.tiktok_username || '',
                        facebook_url: defaultProfile.facebook_url || '',
                        spotify_url: defaultProfile.spotify_url || '',
                        apple_music_url: defaultProfile.apple_music_url || '',
                        design_color_scheme: defaultProfile.design_color_scheme || '',
                        design_artist_photo: defaultProfile.design_artist_photo || '',
                        design_show_year: defaultProfile.design_show_year !== false,
                        design_show_notes: defaultProfile.design_show_notes !== false,
                      }));
                    }}
                    className="w-full mb-4 bg-gray-700 hover:bg-gray-600 border border-dashed border-gray-500 px-4 py-2 rounded-lg text-sm text-gray-300 hover:text-white transition duration-300"
                  >
                    Copy from Default Profile
                  </button>
                  <div className="space-y-4">
                    {/* Name & Slug */}
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-1">Profile Name</label>
                      <input data-testid="profile-name-input" type="text" value={profileForm.name}
                        onChange={(e) => {
                          const name = e.target.value;
                          setProfileForm(prev => ({ ...prev, name, slug: editingProfile ? prev.slug : generateSlugFromName(name) }));
                        }}
                        placeholder="e.g. Smith Wedding, Friday Night Jazz" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white" />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-1">URL Slug</label>
                      <input data-testid="profile-slug-input" type="text" value={profileForm.slug}
                        onChange={(e) => setProfileForm({...profileForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '')})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white" />
                      <p className="text-gray-400 text-xs mt-1">URL: {AUDIENCE_BASE_URL}/musician/{musician.slug}/{profileForm.slug || '...'}</p>
                    </div>

                    {/* Display Name Override */}
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-1">Display Name (override)</label>
                      <input type="text" value={profileForm.musician_name || ''} onChange={(e) => setProfileForm({...profileForm, musician_name: e.target.value})}
                        placeholder={musician.name + ' (master default)'} className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500" />
                      <p className="text-gray-400 text-xs mt-1">Leave blank to use master account name</p>
                    </div>

                    {/* Bio Override */}
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-1">Bio (override)</label>
                      <textarea value={profileForm.bio || ''} onChange={(e) => setProfileForm({...profileForm, bio: e.target.value})}
                        placeholder="Leave blank to use master bio" rows="2" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500" />
                    </div>

                    {/* Website Override */}
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-1">Website (override)</label>
                      <input type="url" value={profileForm.website || ''} onChange={(e) => setProfileForm({...profileForm, website: e.target.value})}
                        placeholder="Leave blank to use master website" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-500" />
                    </div>

                    {/* Active Playlists */}
                    <div>
                      <label className="block text-gray-300 text-sm font-bold mb-1">Active Playlists</label>
                      <p className="text-gray-400 text-xs mb-2">Select which songs are available for this profile</p>
                      <div className="space-y-2 max-h-40 overflow-y-auto bg-gray-700/50 rounded-lg p-3">
                        <label className="flex items-center space-x-2 cursor-pointer border-b border-gray-600 pb-2 mb-1">
                          <input type="checkbox" checked={profileForm.active_playlist_ids.includes('__all__')}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setProfileForm({...profileForm, active_playlist_ids: ['__all__']});
                              } else {
                                setProfileForm({...profileForm, active_playlist_ids: []});
                              }
                            }}
                            className="w-4 h-4 text-purple-600 bg-gray-800 border-gray-600 rounded" />
                          <span className="text-white text-sm font-semibold">All Songs (full library)</span>
                        </label>
                        {playlists.filter(pl => pl.id !== 'all_songs').map(pl => (
                          <label key={pl.id} className="flex items-center space-x-2 cursor-pointer">
                            <input type="checkbox" disabled={profileForm.active_playlist_ids.includes('__all__')}
                              checked={profileForm.active_playlist_ids.includes('__all__') || profileForm.active_playlist_ids.includes(pl.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setProfileForm({...profileForm, active_playlist_ids: [...profileForm.active_playlist_ids, pl.id]});
                                } else {
                                  setProfileForm({...profileForm, active_playlist_ids: profileForm.active_playlist_ids.filter(id => id !== pl.id)});
                                }
                              }}
                              className="w-4 h-4 text-purple-600 bg-gray-800 border-gray-600 rounded" />
                            <span className={`text-sm ${profileForm.active_playlist_ids.includes('__all__') ? 'text-gray-500' : 'text-white'}`}>{pl.name} ({pl.song_count} songs)</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Tip Visibility Toggles */}
                    <div className="space-y-3">
                      <label className="flex items-center justify-between cursor-pointer">
                        <span className="text-gray-300 text-sm">Show tip prompt after request</span>
                        <input type="checkbox" checked={profileForm.show_tips_in_success_screen}
                          onChange={(e) => setProfileForm({...profileForm, show_tips_in_success_screen: e.target.checked})}
                          className="w-5 h-5 text-purple-600 bg-gray-800 border-gray-600 rounded" />
                      </label>
                      <label className="flex items-center justify-between cursor-pointer">
                        <span className="text-gray-300 text-sm">Show tip option in artist info</span>
                        <input type="checkbox" checked={profileForm.show_tips_in_orientation}
                          onChange={(e) => setProfileForm({...profileForm, show_tips_in_orientation: e.target.checked})}
                          className="w-5 h-5 text-purple-600 bg-gray-800 border-gray-600 rounded" />
                      </label>
                      <div>
                        <label className="block text-gray-300 text-sm mb-1">Email capture from requesters</label>
                        <select
                          value={profileForm.email_capture_mode || 'optional'}
                          onChange={(e) => setProfileForm({...profileForm, email_capture_mode: e.target.value})}
                          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                          data-testid="profile-email-capture-mode"
                        >
                          <option value="optional">Optional (ask but skippable)</option>
                          <option value="off">Off (no email step)</option>
                          <option value="required">Required (must provide email)</option>
                        </select>
                      </div>
                    </div>

                    {/* Tip Platform Overrides */}
                    <div className="border-t border-gray-600 pt-4">
                      <h3 className="text-sm font-bold text-gray-300 mb-2">Tip Platform Overrides</h3>
                      <p className="text-gray-400 text-xs mb-3">Leave blank to use master account values</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">Venmo Username</label>
                          <input type="text" value={profileForm.venmo_username || ''} onChange={(e) => setProfileForm({...profileForm, venmo_username: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">PayPal Username</label>
                          <input type="text" value={profileForm.paypal_username || ''} onChange={(e) => setProfileForm({...profileForm, paypal_username: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">Cash App Username</label>
                          <input type="text" value={profileForm.cashapp_username || ''} onChange={(e) => setProfileForm({...profileForm, cashapp_username: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">Zelle Info (email or phone)</label>
                          <input type="text" value={profileForm.zelle_info || ''} onChange={(e) => setProfileForm({...profileForm, zelle_info: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                      </div>
                    </div>

                    {/* Social Link Overrides */}
                    <div className="border-t border-gray-600 pt-4">
                      <h3 className="text-sm font-bold text-gray-300 mb-2">Social Link Overrides</h3>
                      <p className="text-gray-400 text-xs mb-3">Leave blank to use master account values</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">Instagram</label>
                          <input type="text" value={profileForm.instagram_username || ''} onChange={(e) => setProfileForm({...profileForm, instagram_username: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">TikTok</label>
                          <input type="text" value={profileForm.tiktok_username || ''} onChange={(e) => setProfileForm({...profileForm, tiktok_username: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">Facebook URL</label>
                          <input type="text" value={profileForm.facebook_url || ''} onChange={(e) => setProfileForm({...profileForm, facebook_url: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                        <div>
                          <label className="block text-gray-400 text-xs mb-1">Spotify URL</label>
                          <input type="text" value={profileForm.spotify_url || ''} onChange={(e) => setProfileForm({...profileForm, spotify_url: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                        <div className="sm:col-span-2">
                          <label className="block text-gray-400 text-xs mb-1">Apple Music URL</label>
                          <input type="text" value={profileForm.apple_music_url || ''} onChange={(e) => setProfileForm({...profileForm, apple_music_url: e.target.value})}
                            placeholder="Master default" className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-gray-500" />
                        </div>
                      </div>
                    </div>

                    {/* Design Settings */}
                    <div className="border-t border-gray-600 pt-4">
                      <h3 className="text-sm font-bold text-gray-300 mb-3">Design Settings</h3>
                      
                      {/* Color Theme */}
                      <div className="mb-4">
                        <label className="block text-gray-400 text-xs mb-2">Color Theme</label>
                        <div className="grid grid-cols-5 gap-2">
                          {[
                            { name: 'purple', color: 'bg-purple-600', label: 'Purple' },
                            { name: 'blue', color: 'bg-blue-600', label: 'Blue' },
                            { name: 'green', color: 'bg-green-600', label: 'Green' },
                            { name: 'red', color: 'bg-red-600', label: 'Red' },
                            { name: 'orange', color: 'bg-orange-600', label: 'Orange' }
                          ].map((theme) => (
                            <button key={theme.name} type="button"
                              onClick={() => setProfileForm({...profileForm, design_color_scheme: theme.name})}
                              className={`p-2 rounded-lg border-2 transition duration-300 ${
                                profileForm.design_color_scheme === theme.name ? 'border-white shadow-lg' : 'border-gray-600 hover:border-gray-400'
                              }`}>
                              <div className={`w-full h-5 ${theme.color} rounded mb-1`}></div>
                              <span className="text-xs text-gray-300">{theme.label}</span>
                            </button>
                          ))}
                        </div>
                        <p className="text-gray-500 text-xs mt-1">Leave unselected to use global default</p>
                      </div>

                      {/* Artist Photo */}
                      <div className="mb-4">
                        <label className="block text-gray-400 text-xs mb-2">Artist Photo</label>
                        <div className="flex items-center space-x-3">
                          {profileForm.design_artist_photo ? (
                            <div className="relative">
                              <img src={profileForm.design_artist_photo} alt="Artist" className="w-14 h-14 rounded-full object-cover" />
                              <button type="button" onClick={() => setProfileForm({...profileForm, design_artist_photo: ''})}
                                className="absolute -top-1 -right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-red-700">x</button>
                            </div>
                          ) : (
                            <div className="w-14 h-14 rounded-full bg-gray-700 flex items-center justify-center">
                              <span className="text-gray-400 text-xs">None</span>
                            </div>
                          )}
                          <div>
                            <input type="file" accept="image/*" onChange={handleProfilePhotoUpload} className="hidden" id="profile-photo-upload" />
                            <label htmlFor="profile-photo-upload" className="inline-flex items-center px-3 py-1.5 rounded-lg cursor-pointer transition duration-300 bg-blue-600 hover:bg-blue-700 text-white text-sm">Upload Photo</label>
                            <p className="text-xs text-gray-500 mt-1">Max 2MB, JPG/PNG</p>
                          </div>
                        </div>
                      </div>

                      {/* Display Options */}
                      <div className="space-y-2">
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input type="checkbox" checked={profileForm.design_show_year}
                            onChange={(e) => setProfileForm({...profileForm, design_show_year: e.target.checked})}
                            className="w-4 h-4 text-purple-600 bg-gray-800 border-gray-600 rounded" />
                          <span className="text-gray-300 text-sm">Show song year</span>
                        </label>
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input type="checkbox" checked={profileForm.design_show_notes}
                            onChange={(e) => setProfileForm({...profileForm, design_show_notes: e.target.checked})}
                            className="w-4 h-4 text-purple-600 bg-gray-800 border-gray-600 rounded" />
                          <span className="text-gray-300 text-sm">Show song notes</span>
                        </label>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 pt-2">
                      <button data-testid="profile-save-btn" onClick={editingProfile ? handleUpdateProfileById : handleCreateProfile}
                        className="flex-1 bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300">
                        {editingProfile ? 'Save Changes' : 'Create Profile'}
                      </button>
                      <button onClick={() => setShowProfileEditor(false)}
                        className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition duration-300">Cancel</button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Collapsible Account Settings */}
            <div className="bg-gray-800 rounded-xl overflow-hidden">
              <button
                data-testid="account-settings-toggle"
                onClick={() => {
                  const next = !accountSettingsExpanded;
                  if (next) {
                    setAccountEmailInput(profile?.email || musician?.email || '');
                    setAccountSlugInput(musician?.slug || '');
                    setAccountEmailMsg({ type: '', text: '' });
                    setAccountSlugMsg({ type: '', text: '' });
                  }
                  setAccountSettingsExpanded(next);
                }}
                className="w-full p-5 flex justify-between items-center text-left hover:bg-gray-750"
              >
                <h2 className="text-lg font-bold">Account Settings</h2>
                <svg className={`w-5 h-5 transition-transform ${accountSettingsExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {accountSettingsExpanded && (
                <div className="p-6 pt-0 space-y-6">
                  {/* Email */}
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">Email</label>
                    <div className="flex space-x-2">
                      <input
                        type="email"
                        data-testid="account-email-input"
                        value={accountEmailInput}
                        onChange={(e) => setAccountEmailInput(e.target.value)}
                        className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                        placeholder="you@example.com"
                      />
                      <button
                        type="button"
                        data-testid="account-email-save-btn"
                        onClick={handleSaveAccountEmail}
                        disabled={savingAccountEmail}
                        className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-bold text-sm transition duration-300"
                      >
                        {savingAccountEmail ? 'Saving...' : 'Save'}
                      </button>
                    </div>
                    {accountEmailMsg.text && (
                      <p data-testid="account-email-msg" className={`mt-2 text-xs ${accountEmailMsg.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                        {accountEmailMsg.text}
                      </p>
                    )}
                  </div>
                  {/* Master Slug */}
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">Master Slug</label>
                    <p className="text-gray-400 text-xs mb-1">{AUDIENCE_BASE_URL}/musician/{accountSlugInput || musician.slug}</p>
                    <div className="flex space-x-2">
                      <input
                        type="text"
                        data-testid="account-slug-input"
                        value={accountSlugInput}
                        onChange={(e) => setAccountSlugInput(e.target.value)}
                        className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                        placeholder="your-slug"
                      />
                      <button
                        type="button"
                        data-testid="account-slug-save-btn"
                        onClick={handleSaveAccountSlug}
                        disabled={savingAccountSlug}
                        className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-bold text-sm transition duration-300"
                      >
                        {savingAccountSlug ? 'Saving...' : 'Save'}
                      </button>
                    </div>
                    {accountSlugMsg.text && (
                      <p data-testid="account-slug-msg" className={`mt-2 text-xs ${accountSlugMsg.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                        {accountSlugMsg.text}
                      </p>
                    )}
                  </div>
                  {/* Change Password */}
                  <div className="border-t border-gray-600 pt-4">
                    <h3 className="text-sm font-bold text-gray-300 mb-3">Change Password</h3>
                    {changePasswordError && (
                      <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-3 text-red-200 text-sm">{changePasswordError}</div>
                    )}
                    <div className="space-y-3">
                      <input type="password" placeholder="Current password" value={changePasswordForm.current_password}
                        onChange={(e) => setChangePasswordForm({...changePasswordForm, current_password: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 text-sm" />
                      <input type="password" placeholder="New password" value={changePasswordForm.new_password}
                        onChange={(e) => setChangePasswordForm({...changePasswordForm, new_password: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 text-sm" />
                      <input type="password" placeholder="Confirm new password" value={changePasswordForm.confirm_password}
                        onChange={(e) => setChangePasswordForm({...changePasswordForm, confirm_password: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 text-sm" />
                      <button type="button" onClick={handleChangePassword} disabled={changingPassword}
                        className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 py-2 rounded-lg font-bold transition duration-300 text-sm">
                        {changingPassword ? 'Changing...' : 'Change Password'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Events Tab (Sprint 2 Prompt 3) */}
        {activeTab === 'events' && (
          <div data-testid="events-tab" className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">Events</h2>
                <p className="text-gray-400 text-sm">Time-bounded engagements nested under a profile. Each event has its own audience URL, playlists, and overrides.</p>
              </div>
              <button
                data-testid="create-event-btn"
                onClick={() => openEventEditor(null)}
                className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg font-bold transition duration-300"
              >
                + New Event
              </button>
            </div>

            {/* Live + Upcoming events */}
            {events.filter(ev => ev.status !== 'completed').length === 0 ? (
              <div className="bg-gray-800 rounded-xl p-8 text-center text-gray-400">
                No active events yet. Create one to share a wedding pre-show link, a private gig URL, or any time-bounded request inbox.
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {events.filter(ev => ev.status !== 'completed').map(ev => {
                  const parent = profiles.find(p => p.id === ev.profile_id);
                  const url = buildEventUrl(ev);
                  return (
                    <div key={ev.id} data-testid={`event-card-${ev.id}`} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="text-lg font-bold">{ev.name}</h3>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${ev.status === 'live' ? 'bg-red-600' : 'bg-blue-700'}`}>
                              {ev.status === 'live' ? 'LIVE' : 'Upcoming'}
                            </span>
                          </div>
                          <p className="text-gray-400 text-sm">Profile: {parent?.name || '—'}</p>
                          {ev.event_date && (
                            <p className="text-gray-400 text-xs">Date: {String(ev.event_date).slice(0, 10)}</p>
                          )}
                        </div>
                      </div>
                      <a href={url} target="_blank" rel="noopener noreferrer" data-testid={`event-url-${ev.id}`} className="block bg-gray-900 rounded px-3 py-2 text-xs text-purple-300 hover:text-purple-200 break-all mb-3 font-mono underline">{url}</a>
                      <div className="flex flex-wrap gap-2">
                        <button data-testid={`event-copy-url-${ev.id}`} onClick={async () => {
                          try {
                            if (navigator.clipboard?.writeText) {
                              await navigator.clipboard.writeText(url);
                            } else {
                              const ta = document.createElement('textarea');
                              ta.value = url; document.body.appendChild(ta); ta.select();
                              document.execCommand('copy'); document.body.removeChild(ta);
                            }
                            showErrorToast('URL copied');
                          } catch {
                            showErrorToast('Could not copy URL');
                          }
                        }} className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded">Copy URL</button>
                        <button data-testid={`event-edit-${ev.id}`} onClick={() => openEventEditor(ev)} className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded">Edit</button>
                        {ev.status === 'upcoming' && (
                          <>
                            <button data-testid={`event-go-live-${ev.id}`} onClick={() => handleEventStatusChange(ev, 'live')} className="text-xs px-3 py-1 bg-green-700 hover:bg-green-600 rounded">Go Live</button>
                            <button data-testid={`event-delete-${ev.id}`} onClick={() => handleDeleteEvent(ev)} className="text-xs px-3 py-1 bg-red-700 hover:bg-red-600 rounded">Delete</button>
                          </>
                        )}
                        {ev.status === 'live' && (
                          <button data-testid={`event-end-${ev.id}`} onClick={() => { setMergeForEventId(ev.id); setMergeDestProfileId(ev.profile_id); setShowMergeDialog(true); }} className="text-xs px-3 py-1 bg-yellow-700 hover:bg-yellow-600 rounded">End Event</button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Past Events (collapsed) */}
            {events.filter(ev => ev.status === 'completed').length > 0 && (
              <div className="bg-gray-800 rounded-xl border border-gray-700">
                <button
                  data-testid="past-events-toggle"
                  onClick={() => setShowPastEvents(!showPastEvents)}
                  className="w-full p-4 flex justify-between items-center hover:bg-gray-750 text-left"
                >
                  <span className="font-bold">Past Events ({events.filter(ev => ev.status === 'completed').length})</span>
                  <span>{showPastEvents ? '−' : '+'}</span>
                </button>
                {showPastEvents && (
                  <div className="p-4 border-t border-gray-700 space-y-2">
                    {events.filter(ev => ev.status === 'completed').map(ev => {
                      const merged = profiles.find(p => p.id === ev.merged_into_profile_id);
                      return (
                        <div key={ev.id} className="bg-gray-900 rounded p-3 flex justify-between items-center text-sm">
                          <div>
                            <span className="font-medium">{ev.name}</span>
                            {ev.event_date && <span className="text-gray-500 text-xs ml-2">{String(ev.event_date).slice(0, 10)}</span>}
                            {merged && <span className="text-gray-500 text-xs ml-2">→ merged into {merged.name}</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Event Editor Modal */}
            {showEventEditor && (
              <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
                <div className="bg-gray-800 rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xl font-bold">{editingEvent ? 'Edit Event' : 'New Event'}</h3>
                    <button onClick={() => { setShowEventEditor(false); setEditingEvent(null); }} className="text-gray-400 hover:text-white">✕</button>
                  </div>
                  <form onSubmit={handleEventFormSubmit} className="space-y-4">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Event Name *</label>
                      <input
                        type="text"
                        required
                        value={eventForm.name}
                        onChange={(e) => setEventForm({ ...eventForm, name: e.target.value, slug: editingEvent ? eventForm.slug : slugifyForEvent(e.target.value) })}
                        className="w-full bg-gray-700 rounded px-3 py-2 text-sm"
                        data-testid="event-form-name"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Slug (URL identifier)</label>
                      <input
                        type="text"
                        value={eventForm.slug}
                        onChange={(e) => setEventForm({ ...eventForm, slug: slugifyForEvent(e.target.value) })}
                        className="w-full bg-gray-700 rounded px-3 py-2 text-sm font-mono"
                        data-testid="event-form-slug"
                      />
                      {musician && eventForm.profile_id && eventForm.slug && (
                        <p className="text-xs text-purple-300 mt-1 font-mono break-all">
                          {AUDIENCE_BASE_URL}/musician/{musician.slug}/{profiles.find(p => p.id === eventForm.profile_id)?.slug || '?'}/{eventForm.slug}
                        </p>
                      )}
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Parent Profile *</label>
                      <select
                        required
                        value={eventForm.profile_id}
                        onChange={(e) => setEventForm({ ...eventForm, profile_id: e.target.value })}
                        className="w-full bg-gray-700 rounded px-3 py-2 text-sm"
                        data-testid="event-form-profile"
                      >
                        <option value="">— choose profile —</option>
                        {profiles.map(p => (
                          <option key={p.id} value={p.id}>{p.name} ({p.slug})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Event Date (optional)</label>
                      <input
                        type="date"
                        value={eventForm.event_date}
                        onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
                        className="w-full bg-gray-700 rounded px-3 py-2 text-sm"
                        data-testid="event-form-date"
                      />
                    </div>
                    {!editingEvent && (
                      <div>
                        <label className="block text-xs text-gray-400 mb-1">Copy settings from</label>
                        <select
                          value={eventForm.copy_from_source}
                          onChange={(e) => setEventForm({ ...eventForm, copy_from_source: e.target.value })}
                          className="w-full bg-gray-700 rounded px-3 py-2 text-sm"
                        >
                          <option value="">— blank —</option>
                          <optgroup label="Profiles">
                            {profiles.map(p => <option key={p.id} value={`profile:${p.id}`}>{p.name}</option>)}
                          </optgroup>
                          <optgroup label="Events">
                            {events.map(ev => <option key={ev.id} value={`event:${ev.id}`}>{ev.name}</option>)}
                          </optgroup>
                        </select>
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                      <label className="flex items-center space-x-2 text-sm">
                        <input type="checkbox" checked={eventForm.show_tips_in_success_screen} onChange={(e) => setEventForm({ ...eventForm, show_tips_in_success_screen: e.target.checked })} />
                        <span>Show tips on success screen</span>
                      </label>
                      <label className="flex items-center space-x-2 text-sm">
                        <input type="checkbox" checked={eventForm.show_tips_in_orientation} onChange={(e) => setEventForm({ ...eventForm, show_tips_in_orientation: e.target.checked })} />
                        <span>Show tips in orientation</span>
                      </label>
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm mb-1">Email capture from requesters</label>
                      <select
                        value={eventForm.email_capture_mode || 'optional'}
                        onChange={(e) => setEventForm({ ...eventForm, email_capture_mode: e.target.value })}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                        data-testid="event-email-capture-mode"
                      >
                        <option value="optional">Optional (ask but skippable)</option>
                        <option value="off">Off (no email step)</option>
                        <option value="required">Required (must provide email)</option>
                      </select>
                    </div>
                    <details className="bg-gray-900 rounded p-3">
                      <summary className="cursor-pointer text-sm font-semibold">Override fields (optional)</summary>
                      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                        {[
                          ['musician_name', 'Display name'],
                          ['bio', 'Bio'],
                          ['venmo_username', 'Venmo'],
                          ['paypal_username', 'PayPal'],
                          ['cashapp_username', 'Cash App'],
                          ['zelle_info', 'Zelle'],
                          ['instagram_username', 'Instagram'],
                          ['tiktok_username', 'TikTok'],
                          ['facebook_url', 'Facebook URL'],
                          ['spotify_url', 'Spotify URL'],
                          ['apple_music_url', 'Apple Music URL'],
                          ['website', 'Website'],
                        ].map(([key, label]) => (
                          <div key={key}>
                            <label className="block text-xs text-gray-400 mb-1">{label}</label>
                            <input
                              type="text"
                              value={eventForm[key] || ''}
                              onChange={(e) => setEventForm({ ...eventForm, [key]: e.target.value })}
                              className="w-full bg-gray-700 rounded px-2 py-1"
                            />
                          </div>
                        ))}
                      </div>
                    </details>
                    <div className="flex justify-end space-x-2 pt-2">
                      <button type="button" onClick={() => { setShowEventEditor(false); setEditingEvent(null); }} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded">Cancel</button>
                      <button type="submit" data-testid="event-form-save" className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded font-bold">
                        {editingEvent ? 'Save Changes' : 'Create Event'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* End Event / Merge Dialog */}
            {showMergeDialog && (
              <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
                <div className="bg-gray-800 rounded-xl p-6 max-w-md w-full">
                  <h3 className="text-lg font-bold mb-2">End Event</h3>
                  <p className="text-gray-400 text-sm mb-4">Optionally merge shows and requests from this event into a destination profile. Leave empty to keep them tagged on the event only.</p>
                  <label className="block text-xs text-gray-400 mb-1">Merge into profile (optional)</label>
                  <select value={mergeDestProfileId} onChange={(e) => setMergeDestProfileId(e.target.value)} className="w-full bg-gray-700 rounded px-3 py-2 text-sm mb-4">
                    <option value="">— do not merge —</option>
                    {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <div className="flex justify-end space-x-2">
                    <button onClick={() => { setShowMergeDialog(false); setMergeForEventId(null); }} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded">Cancel</button>
                    <button
                      data-testid="event-end-confirm"
                      onClick={async () => {
                        const ev = events.find(e => e.id === mergeForEventId);
                        if (ev) await handleEventStatusChange(ev, 'completed', mergeDestProfileId || null);
                        setShowMergeDialog(false); setMergeForEventId(null); setMergeDestProfileId('');
                      }}
                      className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 rounded font-bold"
                    >
                      Complete Event
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Subscription Tab - NEW: Freemium Model */}
        {activeTab === 'subscription' && (
          <div className="space-y-6">
            {/* Subscription Status Card */}
            <div className="bg-gray-800 rounded-xl p-6">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-xl font-bold">Subscription & Billing</h2>
                  <p className="text-gray-300 text-sm">Manage your RequestWave subscription</p>
                </div>
              </div>

              {subscriptionStatus && (
                <div className="space-y-6">
                  {/* Current Status */}
                  <div className={`p-4 rounded-lg border ${
                    subscriptionStatus.audience_link_active 
                      ? 'bg-green-900/20 border-green-500/30' 
                      : 'bg-red-900/20 border-red-500/30'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className={`font-bold ${
                          subscriptionStatus.audience_link_active ? 'text-green-300' : 'text-red-300'
                        }`}>
                          {subscriptionStatus.plan === 'trial' && 'Free Trial Active'}
                          {subscriptionStatus.plan === 'active' && 'Subscription Active'}
                          {subscriptionStatus.plan === 'canceled' && 'Subscription Canceled'}
                          {subscriptionStatus.plan === 'free' && 'Free Plan'}
                        </h3>
                        <p className="text-gray-300 text-sm">
                          {subscriptionStatus.audience_link_active 
                            ? 'Your audience link is active and receiving requests'
                            : 'Your audience link is paused - upgrade to reactivate'
                          }
                        </p>
                      </div>
                      <div className={`w-4 h-4 rounded-full ${
                        subscriptionStatus.audience_link_active ? 'bg-green-500' : 'bg-red-500'
                      }`} />
                    </div>

                    {/* Trial Information */}
                    {subscriptionStatus.trial_active && (
                      <div className="mt-4 p-3 bg-blue-900/20 border border-blue-500/30 rounded">
                        <p className="text-blue-300 font-medium">
                          🎉 Your 14-day free trial is live!
                        </p>
                        <p className="text-gray-300 text-sm mt-1">
                          Trial ends on {subscriptionStatus.trial_ends_at ? 
                            new Date(subscriptionStatus.trial_ends_at).toLocaleDateString() : 
                            'Unknown'}
                          {subscriptionStatus.days_remaining && ` (${subscriptionStatus.days_remaining} days remaining)`}
                        </p>
                        <p className="text-gray-300 text-sm">
                          Your audience link is active. You won't be charged until your trial ends.
                        </p>
                      </div>
                    )}

                    {/* Grace Period Warning */}
                    {subscriptionStatus.grace_period_active && (
                      <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded">
                        <p className="text-yellow-300 font-medium">
                          ⚠️ Payment Issue - Grace Period Active
                        </p>
                        <p className="text-gray-300 text-sm mt-1">
                          Your payment failed, but your audience link is still active until{' '}
                          {subscriptionStatus.grace_period_ends_at ? 
                            new Date(subscriptionStatus.grace_period_ends_at).toLocaleDateString() : 
                            'soon'}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Upgrade/Reactivate Section */}
                  {(!subscriptionStatus.audience_link_active || subscriptionStatus.plan === 'free') && (
                    <div className="bg-gradient-to-r from-purple-900/50 to-green-900/50 rounded-lg p-6">
                      <h3 className="text-xl font-bold text-white mb-4">
                        {subscriptionStatus.can_reactivate ? 'Reactivate Your Audience Link' : 'Activate Your Audience Link'}
                      </h3>
                      <p className="text-gray-300 mb-6">
                        {subscriptionStatus.can_reactivate 
                          ? 'Welcome back! Reactivate your audience link to start receiving requests again.'
                          : 'Get unlimited song requests with a low monthly fee and 14-day free trial.'
                        }
                      </p>

                      {/* Plan Selection */}
                      <div className="grid md:grid-cols-2 gap-4 mb-6">
                        <div 
                          className={`p-4 rounded-lg border cursor-pointer transition ${
                            selectedPlan === 'annual' 
                              ? 'border-green-500 bg-green-900/20' 
                              : 'border-gray-600 bg-gray-700/50'
                          }`}
                          onClick={() => setSelectedPlan('annual')}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-bold text-green-300">Annual Plan</h4>
                            <span className="bg-green-600 text-white px-2 py-1 rounded text-xs font-bold">
                              BEST VALUE
                            </span>
                          </div>
                          <p className="text-2xl font-bold text-white">
                            $48<span className="text-sm text-gray-400">/year</span>
                          </p>
                          <p className="text-gray-300 text-sm">Equivalent to $4/month</p>
                          <p className="text-gray-400 text-sm mt-2">
                            + $15 one-time startup fee
                          </p>
                        </div>

                        <div 
                          className={`p-4 rounded-lg border cursor-pointer transition ${
                            selectedPlan === 'monthly' 
                              ? 'border-purple-500 bg-purple-900/20' 
                              : 'border-gray-600 bg-gray-700/50'
                          }`}
                          onClick={() => setSelectedPlan('monthly')}
                        >
                          <h4 className="font-bold text-purple-300">Monthly Plan</h4>
                          <p className="text-2xl font-bold text-white">
                            $5<span className="text-sm text-gray-400">/month</span>
                          </p>
                          <p className="text-gray-300 text-sm">Billed monthly</p>
                          <p className="text-gray-400 text-sm mt-2">
                            + $15 one-time startup fee
                          </p>
                        </div>
                      </div>

                      <div className="text-center">
                        <button
                          onClick={handleUpgrade}
                          disabled={upgrading}
                          className="bg-gradient-to-r from-purple-600 to-green-600 hover:from-purple-700 hover:to-green-700 px-8 py-3 rounded-lg font-bold text-white transition duration-300 disabled:opacity-50"
                        >
                          {upgrading ? 'Processing...' : 'Start Free Trial Now'}
                        </button>
                        <p className="text-gray-400 text-sm mt-2">
                          {subscriptionStatus.can_reactivate 
                            ? 'Immediate activation after payment'
                            : '14-day free trial, then subscription begins'
                          }
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Active Subscription Management */}
                  {subscriptionStatus.audience_link_active && subscriptionStatus.plan === 'active' && (
                    <div className="bg-gray-700/50 rounded-lg p-6">
                      <h3 className="text-lg font-bold text-white mb-4">Manage Subscription</h3>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-gray-300">
                            Next billing: {subscriptionStatus.subscription_ends_at ? 
                              new Date(subscriptionStatus.subscription_ends_at).toLocaleDateString() : 
                              'Unknown'}
                          </p>
                          <p className="text-gray-400 text-sm">
                            You can cancel anytime. Your data will remain saved.
                          </p>
                        </div>
                        <button
                          onClick={handleCancelSubscription}
                          className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg font-medium text-white transition duration-300"
                        >
                          Cancel Subscription
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Plan Benefits */}
                  <div className="bg-gray-700/50 rounded-lg p-6">
                    <h3 className="text-lg font-bold text-white mb-4">What's Included</h3>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="font-medium text-green-300 mb-2">✅ Always Free</h4>
                        <ul className="text-gray-300 text-sm space-y-1">
                          <li>• Full musician dashboard</li>
                          <li>• Song management</li>
                          <li>• Request history</li>
                          <li>• Analytics & insights</li>
                        </ul>
                      </div>
                      <div>
                        <h4 className="font-medium text-purple-300 mb-2">🎵 Paid Subscription</h4>
                        <ul className="text-gray-300 text-sm space-y-1">
                          <li>• Active audience link</li>
                          <li>• QR code access</li>
                          <li>• Unlimited song requests</li>
                          <li>• Real-time request notifications</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* NEW: Account Management Section */}
            <div className="bg-gray-800 rounded-xl p-6 mb-6">
              <h3 className="text-xl font-bold mb-4">🔐 Account Management</h3>
              
              <div className="space-y-6">
                {/* Change Email Section */}
                <div className="border-b border-gray-700 pb-6">
                  <h4 className="font-bold text-green-300 mb-4">Change Email</h4>
                  
                  {!showChangeEmail ? (
                    <button
                      onClick={() => setShowChangeEmail(true)}
                      className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium transition duration-300"
                    >
                      Change Email Address
                    </button>
                  ) : (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-gray-300 text-sm font-bold mb-2">New Email</label>
                          <input
                            type="email"
                            value={changeEmailForm.new_email}
                            onChange={(e) => setChangeEmailForm({...changeEmailForm, new_email: e.target.value})}
                            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                            placeholder="new@email.com"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-300 text-sm font-bold mb-2">Confirm New Email</label>
                          <input
                            type="email"
                            value={changeEmailForm.confirm_email}
                            onChange={(e) => setChangeEmailForm({...changeEmailForm, confirm_email: e.target.value})}
                            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                            placeholder="new@email.com"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-gray-300 text-sm font-bold mb-2">Current Password</label>
                        <input
                          type="password"
                          value={changeEmailForm.current_password}
                          onChange={(e) => setChangeEmailForm({...changeEmailForm, current_password: e.target.value})}
                          className="w-full max-w-xs bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                          placeholder="Enter current password"
                        />
                      </div>
                      
                      {changeEmailError && (
                        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                          <p className="text-red-300 text-sm">{changeEmailError}</p>
                        </div>
                      )}
                      
                      <div className="flex space-x-3">
                        <button
                          onClick={handleChangeEmail}
                          disabled={changingEmail}
                          className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium transition duration-300 disabled:opacity-50"
                        >
                          {changingEmail ? 'Updating...' : 'Update Email'}
                        </button>
                        <button
                          onClick={() => {
                            setShowChangeEmail(false);
                            setChangeEmailForm({ new_email: '', confirm_email: '', current_password: '' });
                            setChangeEmailError('');
                          }}
                          className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded-lg font-medium transition duration-300"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Change Password Section */}
                <div>
                  <h4 className="font-bold text-green-300 mb-4">Change Password</h4>
                  
                  {!showChangePassword ? (
                    <button
                      onClick={() => setShowChangePassword(true)}
                      className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium transition duration-300"
                    >
                      Change Password
                    </button>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-gray-300 text-sm font-bold mb-2">Current Password</label>
                        <input
                          type="password"
                          value={changePasswordForm.current_password}
                          onChange={(e) => setChangePasswordForm({...changePasswordForm, current_password: e.target.value})}
                          className="w-full max-w-xs bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                          placeholder="Enter current password"
                        />
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-gray-300 text-sm font-bold mb-2">New Password</label>
                          <input
                            type="password"
                            value={changePasswordForm.new_password}
                            onChange={(e) => setChangePasswordForm({...changePasswordForm, new_password: e.target.value})}
                            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                            placeholder="Enter new password"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-300 text-sm font-bold mb-2">Confirm New Password</label>
                          <input
                            type="password"
                            value={changePasswordForm.confirm_password}
                            onChange={(e) => setChangePasswordForm({...changePasswordForm, confirm_password: e.target.value})}
                            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                            placeholder="Confirm new password"
                          />
                        </div>
                      </div>
                      
                      {/* Password Strength Indicator */}
                      {changePasswordForm.new_password && (
                        <div className="text-sm">
                          <p className="text-gray-300 mb-2">Password Requirements:</p>
                          <ul className="space-y-1">
                            <li className={changePasswordForm.new_password.length >= 8 ? 'text-green-400' : 'text-red-400'}>
                              {changePasswordForm.new_password.length >= 8 ? '✓' : '✗'} At least 8 characters
                            </li>
                            <li className={/[A-Za-z]/.test(changePasswordForm.new_password) ? 'text-green-400' : 'text-red-400'}>
                              {/[A-Za-z]/.test(changePasswordForm.new_password) ? '✓' : '✗'} Contains letters
                            </li>
                            <li className={/\d/.test(changePasswordForm.new_password) ? 'text-green-400' : 'text-red-400'}>
                              {/\d/.test(changePasswordForm.new_password) ? '✓' : '✗'} Contains numbers
                            </li>
                          </ul>
                        </div>
                      )}
                      
                      {changePasswordError && (
                        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                          <p className="text-red-300 text-sm">{changePasswordError}</p>
                        </div>
                      )}
                      
                      <div className="flex space-x-3">
                        <button
                          onClick={handleChangePassword}
                          disabled={changingPassword}
                          className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium transition duration-300 disabled:opacity-50"
                        >
                          {changingPassword ? 'Updating...' : 'Update Password'}
                        </button>
                        <button
                          onClick={() => {
                            setShowChangePassword(false);
                            setChangePasswordForm({ current_password: '', new_password: '', confirm_password: '' });
                            setChangePasswordError('');
                          }}
                          className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded-lg font-medium transition duration-300"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Account Deletion Section */}
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
              <h3 className="text-lg font-bold text-red-300 mb-4">⚠️ Danger Zone</h3>
              <p className="text-gray-300 text-sm mb-4">
                Permanently delete your account and all associated data. This action cannot be undone.
              </p>
              
              {!showDeleteConfirmation ? (
                <button
                  onClick={() => setShowDeleteConfirmation(true)}
                  className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg font-medium text-white transition duration-300"
                >
                  Delete Account
                </button>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-gray-300 text-sm font-bold mb-2">
                      Type "DELETE" to confirm account deletion:
                    </label>
                    <input
                      type="text"
                      value={deleteConfirmationText}
                      onChange={(e) => setDeleteConfirmationText(e.target.value)}
                      className="w-full max-w-xs bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                      placeholder="DELETE"
                    />
                  </div>
                  <div className="flex space-x-3">
                    <button
                      onClick={handleDeleteAccount}
                      disabled={deletingAccount || deleteConfirmationText !== 'DELETE'}
                      className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg font-medium text-white transition duration-300 disabled:opacity-50"
                    >
                      {deletingAccount ? 'Deleting...' : 'Permanently Delete Account'}
                    </button>
                    <button
                      onClick={() => {
                        setShowDeleteConfirmation(false);
                        setDeleteConfirmationText('');
                      }}
                      className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded-lg font-medium text-white transition duration-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* NEW: Redesigned Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            {/* NEW: Redesigned Analytics Header with Period Dropdown */}
            <div className="bg-gray-800 rounded-xl p-6">
              <p className="text-gray-300 mb-4">Insights into your audience and performance</p>
              
              {/* NEW: Period Dropdown (replaces Daily/Weekly/Monthly buttons) */}
              <div className="mb-6">
                <label className="block text-gray-300 text-sm font-bold mb-2">
                  Time Period 
                  <span className="text-purple-400 font-normal ml-2">
                    (Select "All time" to see all {analyticsData?.totals?.total_requests || 0} requests)
                  </span>
                </label>
                <select
                  value={analyticsPeriod}
                  onChange={(e) => {
                    const newPeriod = e.target.value;
                    setAnalyticsPeriod(newPeriod);
                    localStorage.setItem('analytics_period', newPeriod);
                    
                    // Update analytics timeframe for existing data fetching
                    const periodToDaysMap = {
                      'today': 1,
                      'last7days': 7,
                      'last30days': 30,
                      'last3months': 90,
                      'lastyear': 365,
                      'alltime': null
                    };
                    
                    const days = periodToDaysMap[newPeriod];
                    setAnalyticsDays(days); // Set to null for alltime, number for specific periods
                    handleTimeframeChange(days ? `${days}days` : 'alltime');
                    
                    // Immediately fetch analytics with new period
                    fetchAnalytics(days);
                    fetchRequesters();
                  }}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:ring-purple-500 focus:border-purple-500"
                >
                  <option value="today">Today</option>
                  <option value="last7days">Last 7 days</option>
                  <option value="last30days">Last 30 days</option>
                  <option value="last3months">Last 3 months</option>
                  <option value="lastyear">Last Year</option>
                  <option value="alltime">All time</option>
                </select>
              </div>

              {/* Analytics Summary Cards */}
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
                      <p className="text-lg font-bold text-gray-300">
                        {analyticsPeriod === 'today' ? 'Today' :
                         analyticsPeriod === 'last7days' ? 'Last 7 days' :
                         analyticsPeriod === 'last30days' ? 'Last 30 days' :
                         analyticsPeriod === 'last3months' ? 'Last 3 months' :
                         analyticsPeriod === 'lastyear' ? 'Last Year' :
                         'All time'}
                      </p>
                    </div>
                    {/* NEW: Digital Tip Percentage Metric */}
                    <div className="bg-gray-700 rounded-lg p-4">
                      <h3 className="text-sm font-medium text-gray-300">Digital Tips</h3>
                      <p className="text-2xl font-bold text-green-400">
                        {analyticsData.totals.total_requests > 0 ? 
                          Math.round(((analyticsData.totals.requests_with_tips || 0) / analyticsData.totals.total_requests) * 100) : 0}%
                      </p>
                      <p className="text-xs text-gray-400">
                        ({analyticsData.totals.requests_with_tips || 0} of {analyticsData.totals.total_requests} requests)
                      </p>
                    </div>
                  </div>
                  
                  {/* NEW: Export controls — show filter dropdown + Export Email List button */}
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <select
                      data-testid="export-show-select"
                      value={requestersExportShowId}
                      onChange={(e) => setRequestersExportShowId(e.target.value)}
                      className="bg-gray-700 border border-gray-600 rounded px-2 py-2 text-white text-sm"
                    >
                      <option value="all">All Shows</option>
                      {[...(shows || [])]
                        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
                        .map((s) => {
                          const d = s.date || (s.created_at ? new Date(s.created_at).toISOString().slice(0, 10) : '');
                          return (
                            <option key={s.id} value={s.id}>
                              {s.name}{d ? ` (${d})` : ''}
                            </option>
                          );
                        })}
                    </select>
                    <button
                      data-testid="analytics-export-requesters-btn"
                      onClick={async () => {
                        try {
                          const params = buildRequestersFilterParams(requestersFilter);
                          if (requestersExportShowId && requestersExportShowId !== 'all') {
                            params.show_id = requestersExportShowId;
                          }
                          const response = await axios.get(`${API}/analytics/export-requesters`, {
                            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                            responseType: 'blob',
                            params
                          });
                          
                          const blob = new Blob([response.data], { type: 'text/csv' });
                          const url = window.URL.createObjectURL(blob);
                          const link = document.createElement('a');
                          link.href = url;
                          link.download = `requesters-analytics-${new Date().toISOString().split('T')[0]}.csv`;
                          link.click();
                          window.URL.revokeObjectURL(url);
                        } catch (error) {
                          console.error('Error exporting CSV:', error);
                          alert('Error exporting CSV. Please try again.');
                        }
                      }}
                      className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-medium transition duration-300 flex items-center space-x-2"
                    >
                      <span>📧</span>
                      <span>Export Email List</span>
                    </button>
                  </div>
                </div>
              )}

              {!analyticsData && (
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
                  <div className="space-y-3" data-testid="most-requested-songs-list">
                    {analyticsData.top_songs.slice(0, topSongsLimit).map((item, index) => (
                      <div key={index} className="flex justify-between items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{item.song}</p>
                        </div>
                        <span
                          data-testid={`most-requested-song-shows-${index}`}
                          className="text-xs text-gray-400 whitespace-nowrap shrink-0"
                        >
                          Requested in {item.count} {item.count === 1 ? 'show' : 'shows'}
                        </span>
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
                  <div className="flex justify-between items-center mb-4 gap-2 flex-wrap">
                    <h3 className="text-xl font-bold">👥 Most Active Requesters</h3>
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* NEW: Filter by profile/event */}
                      <select
                        data-testid="requesters-filter-select"
                        value={requestersFilter}
                        onChange={(e) => {
                          const next = e.target.value;
                          setRequestersFilter(next);
                          fetchRequesters(next);
                        }}
                        className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
                      >
                        <option value="all">All Profiles</option>
                        {profiles && profiles.length > 0 && (
                          <optgroup label="Profiles">
                            {profiles.map((p) => (
                              <option key={`p-${p.id}`} value={`profile:${p.id}`}>
                                {p.name}
                              </option>
                            ))}
                          </optgroup>
                        )}
                        {events && events.length > 0 && (
                          <optgroup label="Events">
                            {events.map((ev) => (
                              <option key={`e-${ev.id}`} value={`event:${ev.id}`}>
                                {ev.name}
                              </option>
                            ))}
                          </optgroup>
                        )}
                      </select>
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
                  </div>
                  <div className="space-y-3" data-testid="most-active-requesters-list">
                    {requestersData.slice(0, topRequestersLimit).map((item, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <div className="flex-1">
                          <p className="font-medium text-sm">{item.name}</p>
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
                    
                    {requestersData.length === 0 && (
                      <div className="text-center py-8 text-gray-400">
                        <p>No requesters yet in this period</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* NEW: Show Analytics Dashboard (profile-scoped) */}
            <div className="bg-gray-800 rounded-xl p-6 mt-6" data-testid="show-analytics-dashboard">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-xl font-bold">📊 Show Analytics</h3>
                  <p className="text-gray-400 text-sm">Per-show insights and cross-show trends, scoped to a profile</p>
                </div>

                {/* View toggle */}
                <div className="inline-flex rounded-lg overflow-hidden border border-gray-600" role="tablist">
                  <button
                    data-testid="show-analytics-view-detail"
                    role="tab"
                    aria-selected={showAnalyticsView === 'detail'}
                    onClick={() => setShowAnalyticsView('detail')}
                    className={`px-4 py-2 text-sm font-medium transition ${
                      showAnalyticsView === 'detail'
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    Show Detail
                  </button>
                  <button
                    data-testid="show-analytics-view-trends"
                    role="tab"
                    aria-selected={showAnalyticsView === 'trends'}
                    onClick={() => setShowAnalyticsView('trends')}
                    className={`px-4 py-2 text-sm font-medium transition border-l border-gray-600 ${
                      showAnalyticsView === 'trends'
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    Show Trends
                  </button>
                </div>
              </div>

              {/* Profile + scope selectors */}
              <div className="flex flex-wrap items-end gap-3 mb-6">
                <div className="flex-1 min-w-[180px]">
                  <label className="block text-gray-300 text-xs font-bold mb-1">Profile</label>
                  <select
                    data-testid="show-analytics-profile-select"
                    value={showAnalyticsProfileId}
                    onChange={(e) => {
                      setShowAnalyticsProfileId(e.target.value);
                      setShowAnalyticsShowId('');
                      setShowDetailData(null);
                      setShowTrendsData(null);
                    }}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                  >
                    {profiles && profiles.length > 0 ? (
                      profiles.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}{p.is_default ? ' (Default)' : ''}
                        </option>
                      ))
                    ) : (
                      <option value="">No profiles available</option>
                    )}
                  </select>
                </div>

                {showAnalyticsView === 'detail' ? (
                  <div className="flex-1 min-w-[200px]">
                    <label className="block text-gray-300 text-xs font-bold mb-1">Show</label>
                    <select
                      data-testid="show-analytics-show-select"
                      value={showAnalyticsShowId}
                      onChange={(e) => setShowAnalyticsShowId(e.target.value)}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                      disabled={showAnalyticsScopedShows.length === 0}
                    >
                      {showAnalyticsScopedShows.length === 0 ? (
                        <option value="">No shows for this profile</option>
                      ) : (
                        showAnalyticsScopedShows.map((s) => {
                          const d = s.date || (s.created_at ? new Date(s.created_at).toISOString().slice(0, 10) : '');
                          return (
                            <option key={s.id} value={s.id}>
                              {s.name}{d ? ` (${d})` : ''}
                            </option>
                          );
                        })
                      )}
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="block text-gray-300 text-xs font-bold mb-1">Last N shows</label>
                    <select
                      data-testid="show-analytics-trends-limit"
                      value={showTrendsLimit}
                      onChange={(e) => setShowTrendsLimit(parseInt(e.target.value))}
                      className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                    </select>
                  </div>
                )}
              </div>

              {/* Show Detail View */}
              {showAnalyticsView === 'detail' && (
                <div data-testid="show-analytics-detail-view">
                  {showDetailLoading && (
                    <div className="text-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400 mx-auto"></div>
                      <p className="text-gray-400 mt-2">Loading show analytics...</p>
                    </div>
                  )}

                  {!showDetailLoading && !showDetailData && showAnalyticsScopedShows.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                      <p>No shows exist for this profile yet.</p>
                    </div>
                  )}

                  {!showDetailLoading && showDetailData && (
                    <>
                      {/* Metric Cards */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div className="bg-gray-700 rounded-lg p-4" data-testid="metric-email-capture">
                          <h4 className="text-xs font-medium text-gray-300 uppercase tracking-wide">Email Capture</h4>
                          <p className="text-2xl font-bold text-blue-400">
                            {showDetailData.metrics.email_capture_rate}%
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {showDetailData.metrics.requests_with_email} of {showDetailData.metrics.total_requests} requests
                          </p>
                        </div>
                        <div className="bg-gray-700 rounded-lg p-4" data-testid="metric-tip-revenue">
                          <h4 className="text-xs font-medium text-gray-300 uppercase tracking-wide">Tip Revenue</h4>
                          <p className="text-2xl font-bold text-green-400">
                            ${showDetailData.metrics.total_tip_revenue.toFixed(2)}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {showDetailData.metrics.tip_count} {showDetailData.metrics.tip_count === 1 ? 'tip' : 'tips'}
                          </p>
                        </div>
                        <div className="bg-gray-700 rounded-lg p-4" data-testid="metric-click-through">
                          <h4 className="text-xs font-medium text-gray-300 uppercase tracking-wide">Click-Through</h4>
                          <p className="text-2xl font-bold text-orange-400">
                            {showDetailData.metrics.click_through_rate}%
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {showDetailData.metrics.requests_with_click} clicks on tip/social
                          </p>
                        </div>
                        <div className="bg-gray-700 rounded-lg p-4" data-testid="metric-total-requests">
                          <h4 className="text-xs font-medium text-gray-300 uppercase tracking-wide">Total Requests</h4>
                          <p className="text-2xl font-bold text-purple-400">
                            {showDetailData.metrics.total_requests}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {showDetailData.show.name}
                          </p>
                        </div>
                      </div>

                      {/* Lists Grid */}
                      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {/* Top 5 Songs */}
                        <div className="bg-gray-700 rounded-lg p-4" data-testid="show-top-songs">
                          <h4 className="text-sm font-bold mb-3 text-purple-300">🎵 Top 5 Most Requested</h4>
                          {showDetailData.top_songs.length === 0 ? (
                            <p className="text-gray-400 text-sm">No requests yet</p>
                          ) : (
                            <ol className="space-y-2">
                              {showDetailData.top_songs.map((song, i) => (
                                <li key={i} className="flex justify-between items-center gap-2 text-sm">
                                  <span className="text-gray-200 truncate">
                                    <span className="text-gray-400 mr-1">{i + 1}.</span>
                                    {song.title}{song.artist ? ` — ${song.artist}` : ''}
                                  </span>
                                  <span className="text-purple-300 whitespace-nowrap text-xs">{song.count}×</span>
                                </li>
                              ))}
                            </ol>
                          )}
                        </div>

                        {/* Top 5 Tippers */}
                        <div className="bg-gray-700 rounded-lg p-4" data-testid="show-top-tippers">
                          <h4 className="text-sm font-bold mb-3 text-green-300">💵 Top 5 Tippers</h4>
                          {showDetailData.top_tippers.length === 0 ? (
                            <p className="text-gray-400 text-sm">No tips recorded yet</p>
                          ) : (
                            <ol className="space-y-2">
                              {showDetailData.top_tippers.map((t, i) => (
                                <li key={i} className="flex justify-between items-center gap-2 text-sm">
                                  <span className="text-gray-200 truncate">
                                    <span className="text-gray-400 mr-1">{i + 1}.</span>
                                    {t.name}
                                  </span>
                                  <span className="text-green-300 whitespace-nowrap text-xs">${t.amount.toFixed(2)}</span>
                                </li>
                              ))}
                            </ol>
                          )}
                        </div>

                        {/* Repeat Requesters */}
                        <div className="bg-gray-700 rounded-lg p-4" data-testid="show-repeat-requesters">
                          <h4 className="text-sm font-bold mb-3 text-blue-300">🔁 Repeat Requesters</h4>
                          <p className="text-xs text-gray-400 mb-2">Emails seen in 2+ shows for this profile</p>
                          {showDetailData.repeat_requesters.length === 0 ? (
                            <p className="text-gray-400 text-sm">No repeat requesters yet</p>
                          ) : (
                            <ol className="space-y-2">
                              {showDetailData.repeat_requesters.slice(0, 10).map((r, i) => (
                                <li key={i} className="flex justify-between items-center gap-2 text-sm">
                                  <span className="text-gray-200 truncate">
                                    <span className="text-gray-400 mr-1">{i + 1}.</span>
                                    {r.name || r.email}
                                  </span>
                                  <span className="text-blue-300 whitespace-nowrap text-xs">
                                    {r.shows_count} shows
                                  </span>
                                </li>
                              ))}
                            </ol>
                          )}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Show Trends View */}
              {showAnalyticsView === 'trends' && (
                <div data-testid="show-analytics-trends-view">
                  {showTrendsLoading && (
                    <div className="text-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400 mx-auto"></div>
                      <p className="text-gray-400 mt-2">Loading trends...</p>
                    </div>
                  )}

                  {!showTrendsLoading && showTrendsData && showTrendsData.shows.length === 0 && (
                    <div className="text-center py-8 text-gray-400">
                      <p>No shows exist for this profile yet.</p>
                    </div>
                  )}

                  {!showTrendsLoading && showTrendsData && showTrendsData.shows.length > 0 && (
                    <div className="space-y-6">
                      {/* Graph 1: Email capture count + Tip revenue (dual axis) */}
                      <div className="bg-gray-700 rounded-lg p-4" data-testid="trend-graph-email-tips">
                        <h4 className="text-sm font-bold mb-3 text-purple-300">
                          Email Captures &amp; Tip Revenue — Last {showTrendsData.shows.length} {showTrendsData.shows.length === 1 ? 'show' : 'shows'}
                        </h4>
                        <ResponsiveContainer width="100%" height={300}>
                          <ComposedChart
                            data={showTrendsData.shows}
                            margin={{ top: 10, right: 16, left: 0, bottom: 32 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis
                              dataKey="show_name"
                              stroke="#9ca3af"
                              tick={{ fontSize: 11 }}
                              angle={-20}
                              textAnchor="end"
                              height={50}
                              interval={0}
                            />
                            <YAxis
                              yAxisId="left"
                              stroke="#60a5fa"
                              tick={{ fontSize: 11 }}
                              label={{ value: 'Emails', angle: -90, position: 'insideLeft', fill: '#60a5fa', fontSize: 11 }}
                            />
                            <YAxis
                              yAxisId="right"
                              orientation="right"
                              stroke="#34d399"
                              tick={{ fontSize: 11 }}
                              label={{ value: '$ Tips', angle: 90, position: 'insideRight', fill: '#34d399', fontSize: 11 }}
                            />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }}
                              formatter={(value, name) => {
                                if (name === 'Tip Revenue') return [`$${Number(value).toFixed(2)}`, name];
                                return [value, name];
                              }}
                            />
                            <Legend wrapperStyle={{ color: '#d1d5db' }} />
                            <Bar yAxisId="left" dataKey="email_capture_count" name="Email Captures" fill="#60a5fa" radius={[4, 4, 0, 0]} />
                            <Line yAxisId="right" type="monotone" dataKey="tip_revenue" name="Tip Revenue" stroke="#34d399" strokeWidth={2} dot={{ r: 4 }} />
                          </ComposedChart>
                        </ResponsiveContainer>
                      </div>

                      {/* Graph 2: Click-through rate */}
                      <div className="bg-gray-700 rounded-lg p-4" data-testid="trend-graph-ctr">
                        <h4 className="text-sm font-bold mb-3 text-orange-300">
                          Click-Through Rate % — Last {showTrendsData.shows.length} {showTrendsData.shows.length === 1 ? 'show' : 'shows'}
                        </h4>
                        <ResponsiveContainer width="100%" height={260}>
                          <LineChart
                            data={showTrendsData.shows}
                            margin={{ top: 10, right: 16, left: 0, bottom: 32 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis
                              dataKey="show_name"
                              stroke="#9ca3af"
                              tick={{ fontSize: 11 }}
                              angle={-20}
                              textAnchor="end"
                              height={50}
                              interval={0}
                            />
                            <YAxis
                              stroke="#fb923c"
                              tick={{ fontSize: 11 }}
                              domain={[0, 100]}
                              tickFormatter={(v) => `${v}%`}
                            />
                            <Tooltip
                              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' }}
                              formatter={(value) => [`${value}%`, 'CTR']}
                            />
                            <Legend wrapperStyle={{ color: '#d1d5db' }} />
                            <Line type="monotone" dataKey="click_through_rate" name="CTR %" stroke="#fb923c" strokeWidth={2} dot={{ r: 4 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>


            
            {/* Audience Requesters Box - REMOVED per requirements */}
            {/* This section has been completely removed as requested */}
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

              {/* Artist Photo */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <label className="block text-gray-300 text-sm font-bold">Artist Photo</label>
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
                      className="inline-flex items-center px-4 py-2 rounded-lg cursor-pointer transition duration-300 bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      📷 Upload Photo
                    </label>
                    <p className="text-xs text-gray-400 mt-1">
                      Max 2MB, JPG/PNG
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
                
                {/* Song Suggestions Toggle - Available for all users */}
                <div className="flex items-center space-x-3 mb-4">
                  {/* Toggle Switch */}
                  <div className="relative inline-block w-10 mr-2 align-middle select-none">
                    <input
                      type="checkbox"
                      id="allow_song_suggestions"
                      checked={designSettings.allow_song_suggestions}
                      onChange={(e) => setDesignSettings({...designSettings, allow_song_suggestions: e.target.checked})}
                      className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer transition-transform duration-300 transform"
                      style={{
                        left: designSettings.allow_song_suggestions ? '16px' : '0px',
                        backgroundColor: '#ffffff'
                      }}
                    />
                    <label
                      htmlFor="allow_song_suggestions"
                      className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer transition-colors duration-300 ${
                        designSettings.allow_song_suggestions ? 'bg-green-500' : 'bg-gray-600'
                      }`}
                    ></label>
                  </div>
                  <label htmlFor="allow_song_suggestions" className="text-white text-sm cursor-pointer">
                    Song Suggestions {designSettings.allow_song_suggestions ? 'ON' : 'OFF'}
                  </label>
                  <div className="group relative">
                    <span className="text-gray-400 cursor-help">ℹ️</span>
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-48 text-center">
                      Let your audience suggest songs that aren't in your current repertoire
                    </div>
                  </div>
                </div>
                
                {/* Tip System Toggle - NEW */}
                <div className="flex items-center space-x-3">
                  {/* Toggle Switch */}
                  <div className="relative inline-block w-10 mr-2 align-middle select-none">
                    <input
                      type="checkbox"
                      id="tips_enabled"
                      checked={profile.tips_enabled !== false}
                      onChange={(e) => setProfile({...profile, tips_enabled: e.target.checked})}
                      className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer transition-transform duration-300 transform"
                      style={{
                        left: (profile.tips_enabled !== false) ? '16px' : '0px',
                        backgroundColor: '#ffffff'
                      }}
                    />
                    <label
                      htmlFor="tips_enabled"
                      className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer transition-colors duration-300 ${
                        (profile.tips_enabled !== false) ? 'bg-green-500' : 'bg-gray-600'
                      }`}
                    ></label>
                  </div>
                  <label htmlFor="tips_enabled" className="text-white text-sm cursor-pointer">
                    Tip System {(profile.tips_enabled !== false) ? 'ON' : 'OFF'}
                  </label>
                  <div className="group relative">
                    <span className="text-gray-400 cursor-help">ℹ️</span>
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-48 text-center">
                      Allow your audience to tip you when making song requests
                    </div>
                  </div>
              </div>
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
              <h2 className="text-2xl font-bold text-center mb-6">
                Upgrade to <span className="text-purple-400">Request</span><span className="text-green-400">Wave</span> Pro
              </h2>
              
              <div className="text-center mb-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  {/* Monthly Plan */}
                  <div 
                    className={`bg-gray-700 rounded-lg p-4 border-2 cursor-pointer transition duration-300 ${
                      selectedPlan === 'monthly' ? 'border-purple-500 bg-purple-900/30' : 'border-gray-600 hover:border-gray-500'
                    }`}
                    onClick={() => setSelectedPlan('monthly')}
                  >
                    <div className="text-center">
                      <div className="flex items-center justify-center mb-2">
                        <input 
                          type="radio" 
                          name="plan" 
                          checked={selectedPlan === 'monthly'}
                          onChange={() => setSelectedPlan('monthly')}
                          className="mr-2"
                        />
                        <h3 className="text-lg font-bold">Monthly</h3>
                      </div>
                      <div className="bg-purple-600 text-white rounded-full px-4 py-2 text-2xl font-bold mb-2">
                        $10/month
                      </div>
                      <p className="text-gray-300 text-sm">Billed monthly</p>
                      <p className="text-gray-400 text-xs mt-1">Cancel anytime</p>
                    </div>
                  </div>
                  
                  {/* Annual Plan - Recommended */}
                  <div 
                    className={`bg-gray-700 rounded-lg p-4 border-2 cursor-pointer transition duration-300 relative ${
                      selectedPlan === 'annual' ? 'border-green-500 bg-green-900/30' : 'border-green-500 hover:border-green-400'
                    }`}
                    onClick={() => setSelectedPlan('annual')}
                  >
                    <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                      <span className="bg-green-500 text-white px-3 py-1 rounded-full text-xs font-bold">SAVE 50%</span>
                    </div>
                    <div className="text-center">
                      <div className="flex items-center justify-center mb-2">
                        <input 
                          type="radio" 
                          name="plan" 
                          checked={selectedPlan === 'annual'}
                          onChange={() => setSelectedPlan('annual')}
                          className="mr-2"
                        />
                        <h3 className="text-lg font-bold">Annual</h3>
                      </div>
                      <div className="bg-green-600 text-white rounded-full px-4 py-2 text-2xl font-bold mb-2">
                        $5/month
                      </div>
                      <p className="text-gray-300 text-sm">Billed annually ($60)</p>
                      <p className="text-gray-400 text-xs mt-1">2 months free!</p>
                    </div>
                  </div>
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
                  {upgrading ? 'Processing...' : `Upgrade Now - ${selectedPlan === 'monthly' ? '$10/month' : '$5/month (Annual)'}`}
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
                
                {/* NEW: Multi-select Genres Dropdown */}
                <div className="md:col-span-1">
                  <label className="block text-sm font-medium text-gray-300 mb-2">Genres</label>
                  <div className="space-y-2">
                    {/* Selected Genres Display */}
                    <div className="flex flex-wrap gap-2 min-h-[2rem] p-2 bg-gray-700 border border-gray-600 rounded-lg">
                      {songForm.genres.length === 0 ? (
                        <span className="text-gray-400 text-sm">Select genres...</span>
                      ) : (
                        songForm.genres.map((genre, index) => (
                          <span
                            key={index}
                            className="bg-blue-600 text-white px-2 py-1 rounded text-sm flex items-center space-x-1"
                          >
                            <span>{genre}</span>
                            <button
                              type="button"
                              onClick={() => {
                                const newGenres = songForm.genres.filter((_, i) => i !== index);
                                setSongForm({...songForm, genres: newGenres});
                              }}
                              className="text-blue-200 hover:text-white ml-1"
                            >
                              ×
                            </button>
                          </span>
                        ))
                      )}
                    </div>
                    
                    {/* Genre Selection Dropdown */}
                    <select
                      value=""
                      onChange={(e) => {
                        if (e.target.value && !songForm.genres.includes(e.target.value)) {
                          setSongForm({...songForm, genres: [...songForm.genres, e.target.value]});
                        }
                      }}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                    >
                      <option value="">Add genre...</option>
                      {filterOptions.genres?.filter(genre => !songForm.genres.includes(genre)).map(genre => (
                        <option key={genre} value={genre}>{genre}</option>
                      ))}
                    </select>
                    
                    {/* Add New Genre */}
                    {showAddGenre ? (
                      <div className="flex space-x-2">
                        <input
                          type="text"
                          value={newGenre}
                          onChange={(e) => setNewGenre(e.target.value)}
                          placeholder="New genre name"
                          className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                          onKeyPress={(e) => e.key === 'Enter' && handleAddNewGenre()}
                        />
                        <button
                          type="button"
                          onClick={handleAddNewGenre}
                          className="bg-green-600 hover:bg-green-700 px-3 py-2 rounded-lg text-sm"
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={() => {setShowAddGenre(false); setNewGenre('');}}
                          className="bg-gray-600 hover:bg-gray-700 px-3 py-2 rounded-lg text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setShowAddGenre(true)}
                        className="text-green-400 hover:text-green-300 text-sm flex items-center space-x-1"
                      >
                        <span>+</span>
                        <span>Add new genre</span>
                      </button>
                    )}
                  </div>
                </div>
                
                {/* NEW: Multi-select Moods Dropdown */}
                <div className="md:col-span-1">
                  <label className="block text-sm font-medium text-gray-300 mb-2">Moods</label>
                  <div className="space-y-2">
                    {/* Selected Moods Display */}
                    <div className="flex flex-wrap gap-2 min-h-[2rem] p-2 bg-gray-700 border border-gray-600 rounded-lg">
                      {songForm.moods.length === 0 ? (
                        <span className="text-gray-400 text-sm">Select moods...</span>
                      ) : (
                        songForm.moods.map((mood, index) => (
                          <span
                            key={index}
                            className="bg-green-600 text-white px-2 py-1 rounded text-sm flex items-center space-x-1"
                          >
                            <span>{mood}</span>
                            <button
                              type="button"
                              onClick={() => {
                                const newMoods = songForm.moods.filter((_, i) => i !== index);
                                setSongForm({...songForm, moods: newMoods});
                              }}
                              className="text-green-200 hover:text-white ml-1"
                            >
                              ×
                            </button>
                          </span>
                        ))
                      )}
                    </div>
                    
                    {/* Mood Selection Dropdown */}
                    <select
                      value=""
                      onChange={(e) => {
                        if (e.target.value && !songForm.moods.includes(e.target.value)) {
                          setSongForm({...songForm, moods: [...songForm.moods, e.target.value]});
                        }
                      }}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                    >
                      <option value="">Add mood...</option>
                      {filterOptions.moods?.filter(mood => !songForm.moods.includes(mood)).map(mood => (
                        <option key={mood} value={mood}>{mood}</option>
                      ))}
                    </select>
                    
                    {/* Add New Mood */}
                    {showAddMood ? (
                      <div className="flex space-x-2">
                        <input
                          type="text"
                          value={newMood}
                          onChange={(e) => setNewMood(e.target.value)}
                          placeholder="New mood name"
                          className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
                          onKeyPress={(e) => e.key === 'Enter' && handleAddNewMood()}
                        />
                        <button
                          type="button"
                          onClick={handleAddNewMood}
                          className="bg-green-600 hover:bg-green-700 px-3 py-2 rounded-lg text-sm"
                        >
                          Add
                        </button>
                        <button
                          type="button"
                          onClick={() => {setShowAddMood(false); setNewMood('');}}
                          className="bg-gray-600 hover:bg-gray-700 px-3 py-2 rounded-lg text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setShowAddMood(true)}
                        className="text-green-400 hover:text-green-300 text-sm flex items-center space-x-1"
                      >
                        <span>+</span>
                        <span>Add new mood</span>
                      </button>
                    )}
                  </div>
                </div>
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
                    <div key={playlist.id} className="bg-gray-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex-1">
                          {editingPlaylist === playlist.id ? (
                            <div className="flex items-center space-x-2">
                              <input
                                type="text"
                                value={editingPlaylistName}
                                onChange={(e) => setEditingPlaylistName(e.target.value)}
                                className="bg-gray-600 border border-gray-500 rounded px-3 py-1 text-white flex-1"
                                onKeyPress={(e) => {
                                  if (e.key === 'Enter') {
                                    savePlaylistName(playlist.id);
                                  } else if (e.key === 'Escape') {
                                    cancelEditingPlaylistName();
                                  }
                                }}
                                onBlur={() => savePlaylistName(playlist.id)}
                                autoFocus
                              />
                              <button
                                onClick={() => savePlaylistName(playlist.id)}
                                className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm"
                              >
                                Save
                              </button>
                              <button
                                onClick={cancelEditingPlaylistName}
                                className="bg-gray-600 hover:bg-gray-700 px-3 py-1 rounded text-sm"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <div>
                              <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2">
                                <h3 className="font-medium break-words">{playlist.name}</h3>
                                <div className="flex items-center space-x-1 mt-1 sm:mt-0">
                                  {playlist.is_active && (
                                    <span className="bg-green-500 text-white px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap">
                                      Active
                                    </span>
                                  )}
                                  <span className={`px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
                                    playlist.is_public 
                                      ? 'bg-blue-500 text-white' 
                                      : 'bg-gray-500 text-white'
                                  }`}>
                                    {playlist.is_public ? 'Public' : 'Private'}
                                  </span>
                                </div>
                              </div>
                              <p className="text-gray-400 text-sm mt-1">
                                {playlist.song_count} songs
                              </p>
                            </div>
                          )}
                        </div>
                        
                        {editingPlaylist !== playlist.id && (
                          <div className="flex items-center space-x-2">
                            {/* Public/Private Toggle */}
                            <button
                              onClick={() => togglePlaylistVisibility(playlist.id, playlist.is_public)}
                              className={`px-3 py-1 rounded text-sm font-medium transition duration-300 ${
                                playlist.is_public
                                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                  : 'bg-gray-600 hover:bg-gray-700 text-white'
                              }`}
                              title={playlist.is_public ? 'Make Private' : 'Make Public'}
                            >
                              {playlist.is_public ? '🌐' : '🔒'}
                            </button>
                            
                            {/* Activate Button */}
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
                            
                            {/* Rename Button */}
                            <button
                              onClick={() => startEditingPlaylistName(playlist.id, playlist.name)}
                              className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm text-white font-medium transition duration-300"
                              title="Rename playlist"
                            >
                              ✏️
                            </button>
                            
                            {/* Delete Button */}
                            <button
                              onClick={() => confirmDeletePlaylist(playlist)}
                              className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm text-white font-medium transition duration-300"
                              title="Delete playlist"
                            >
                              🗑️
                            </button>
                          </div>
                        )}
                      </div>
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

        {/* Quick Start Guide Modal (manual access only) */}
        {showQuickStart && (
          <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
              {/* Header */}
              <div className="bg-gradient-to-r from-purple-600 to-green-600 p-6 rounded-t-xl">
                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-3">
                    <img
                      src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png"
                      alt="RequestWave"
                      className="w-10 h-10 object-contain"
                    />
                    <h2 className="text-2xl font-bold text-white">
                      🎵 Quick Start Guide for RequestWave
                    </h2>
                  </div>
                  <button
                    onClick={() => setShowQuickStart(false)}
                    className="text-white hover:text-gray-300 text-2xl font-bold"
                  >
                    ×
                  </button>
                </div>
                <p className="text-purple-100 mt-2">Welcome to RequestWave — your all-in-one tool for managing live song requests, tips, and audience interaction. Here's how to get started fast:</p>
              </div>

              {/* Content */}
              <div className="p-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Left Column */}
                  <div className="space-y-6">
                    {/* Step 1 */}
                    <div className="bg-gray-700 rounded-lg p-6">
                      <h3 className="text-xl font-bold text-purple-300 mb-4 flex items-center">
                        🎵 Step 1: Build Your Song Library
                      </h3>
                      <p className="text-gray-300 mb-3">Head to the Songs tab to load your repertoire.</p>
                      
                      <div className="space-y-2 mb-4">
                        <p className="text-gray-300 text-sm">• <span className="text-blue-300">Import Playlist</span>: Bring in songs directly from Spotify.</p>
                        <p className="text-gray-300 text-sm">• <span className="text-green-300">Upload CSV</span>: Drop in your song list (you can export from spreadsheets or download our sample file).</p>
                        <p className="text-gray-300 text-sm">• <span className="text-green-300">Add New Song</span>: Enter songs manually if you just need to add a few.</p>
                        <p className="text-gray-300 text-sm">• <span className="text-purple-300">Manage Playlists</span>: Organize songs into playlists you can use for different shows. Rename, delete, and set an active playlist from the Profile tab.</p>
                      </div>

                      {/* Download CSV Button */}
                      <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
                        <h4 className="font-bold text-green-300 mb-2">🔥 Try our Starter Pack</h4>
                        <p className="text-gray-300 text-sm mb-3">
                          <a 
                            href={`${process.env.REACT_APP_BACKEND_URL}/api/demo-csv`}
                            download="RequestWave_Popular_Songs.csv"
                            className="text-green-300 underline hover:text-green-200"
                          >
                            Download the curated CSV of 50+ crowd favorites, then upload it into the <span className="text-green-300">Songs</span> tab to instantly see how RequestWave organizes your library.
                          </a>
                        </p>
                      </div>
                    </div>

                    {/* Step 2 */}
                    <div className="bg-gray-700 rounded-lg p-6">
                      <h3 className="text-xl font-bold text-green-300 mb-4 flex items-center">
                        🎨 Step 2: Customize Your Artist Page
                      </h3>
                      <p className="text-gray-300 mb-3">Make the audience experience yours.</p>
                      
                      <div className="space-y-2">
                        <p className="text-gray-300 text-sm">• <span className="text-green-300">Design tab</span>: Choose your theme, colors, and layout.</p>
                        <p className="text-gray-300 text-sm">• <span className="text-green-300">Profile tab</span>: Add your photo, social links, and connect tip options (PayPal, Venmo, Zelle).</p>
                        <p className="text-gray-300 text-sm">• <span className="text-blue-300">Audience Link box</span>: Copy your shareable link, scan the QR code, or print a flyer.</p>
                      </div>
                    </div>
                  </div>

                  {/* Right Column */}
                  <div className="space-y-6">
                    {/* Step 3 */}
                    <div className="bg-gray-700 rounded-lg p-6">
                      <h3 className="text-xl font-bold text-blue-300 mb-4 flex items-center">
                        📱 Step 3: Go Live
                      </h3>
                      <p className="text-gray-300 text-sm mb-4">During your show, use RequestWave to handle requests in real time.</p>
                      <div className="space-y-2">
                        <p className="text-gray-300 text-sm">• Share your QR code or link with the crowd.</p>
                        <p className="text-gray-300 text-sm">• Fans browse your library and submit requests or dedications.</p>
                        <p className="text-gray-300 text-sm">• Requests appear instantly in the <span className="text-blue-300">Requests</span> tab.</p>
                        <p className="text-gray-300 text-sm">• Use the <span className="text-purple-300">Song Suggestions</span> folder to see audience picks outside your repertoire (always visible, collapsible like "All Requests").</p>
                        <p className="text-gray-300 text-sm">• In <span className="text-yellow-300">On Stage</span> mode, see a clean 3-section view:</p>
                        <div className="ml-4 space-y-1">
                          <p className="text-gray-300 text-sm">• <span className="text-blue-300">Up Next</span>: your active queue</p>
                          <p className="text-gray-300 text-sm">• <span className="text-purple-300">Requests</span>: incoming songs</p>
                          <p className="text-gray-300 text-sm">• <span className="text-green-300">Played/Skipped</span>: history log</p>
                        </div>
                        <p className="text-gray-300 text-sm">• Mark songs as Up Next, Played, or Skipped. Played songs automatically move down the list to keep the queue clear.</p>
                      </div>
                    </div>
                    
                    {/* Step 4 */}
                    <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
                      <h3 className="text-lg font-bold text-blue-300 mb-3 flex items-center">
                        📊 Step 4: Track Your Success
                      </h3>
                      <p className="text-gray-300 text-sm">After the show, head to Analytics to see:</p>
                      <div className="space-y-1 mt-2">
                        <p className="text-gray-300 text-sm">• Top requested songs</p>
                        <p className="text-gray-300 text-sm">• Total requests by day, week, or month</p>
                        <p className="text-gray-300 text-sm">• Tip activity and audience engagement</p>
                        <p className="text-gray-300 text-sm">• Export data to keep a log of your performances</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Contact Section */}
                <div className="mt-8 bg-gray-700 rounded-lg p-6">
                  <h3 className="text-lg font-bold text-white mb-4 flex items-center">
                    🔧 Need Help?
                  </h3>
                  <p className="text-gray-300 text-sm mb-4">If you ever get stuck, just reach out — we're here to help.</p>
                  
                  <form onSubmit={handleContactSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input
                      type="text"
                      placeholder="Your Name"
                      value={contactForm.name}
                      onChange={(e) => setContactForm({...contactForm, name: e.target.value})}
                      className="bg-gray-600 border border-gray-500 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      required
                    />
                    <input
                      type="email"
                      placeholder="Your Email"
                      value={contactForm.email}
                      onChange={(e) => setContactForm({...contactForm, email: e.target.value})}
                      className="bg-gray-600 border border-gray-500 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      required
                    />
                    <textarea
                      placeholder="Your Message"
                      value={contactForm.message}
                      onChange={(e) => setContactForm({...contactForm, message: e.target.value})}
                      rows="4"
                      className="md:col-span-2 bg-gray-600 border border-gray-500 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                      required
                    ></textarea>
                    <button
                      type="submit"
                      disabled={contactLoading}
                      className="md:col-span-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-4 py-2 rounded-lg font-bold transition duration-300"
                    >
                      {contactLoading ? 'Sending...' : 'Send Message'}
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* NEW: Edit Playlist Songs Modal */}
        {showEditPlaylistSongsModal && editingSongsPlaylist && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">✏️ Edit Playlist</h2>
                  <div className="text-gray-400 text-sm mt-1">
                    {editingSongsPlaylist.name} • {editPlaylistSongs.length} songs
                  </div>
                </div>
                <button
                  onClick={closeEditPlaylistSongsModal}
                  className="text-gray-400 hover:text-white text-2xl"
                  disabled={editPlaylistLoading}
                >
                  ×
                </button>
              </div>

              {/* Modal Body */}
              <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">
                {editPlaylistError && (
                  <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mb-4">
                    <p className="text-red-300 text-sm">{editPlaylistError}</p>
                  </div>
                )}

                {editPlaylistSongs.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">🎵</div>
                    <h3 className="text-xl font-bold text-gray-300 mb-2">Empty Playlist</h3>
                    <p className="text-gray-400 mb-4">This playlist doesn't have any songs yet.</p>
                    <button className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-medium">
                      Add Songs (Coming Soon)
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {editPlaylistSongs.map((song, index) => (
                      <div
                        key={song.id}
                        className="bg-gray-700 rounded-lg p-3 flex items-center space-x-3 hover:bg-gray-600 transition duration-200"
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData('text/plain', index.toString());
                          e.currentTarget.style.opacity = '0.5';
                        }}
                        onDragEnd={(e) => {
                          e.currentTarget.style.opacity = '1';
                        }}
                        onDragOver={(e) => {
                          e.preventDefault();
                        }}
                        onDrop={(e) => {
                          e.preventDefault();
                          const dragIndex = parseInt(e.dataTransfer.getData('text/plain'));
                          const hoverIndex = index;
                          if (dragIndex !== hoverIndex) {
                            reorderPlaylistSongs(dragIndex, hoverIndex);
                          }
                        }}
                      >
                        {/* Drag Handle */}
                        <div className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-white">
                          <span className="text-lg select-none">⋮⋮</span>
                        </div>
                        
                        {/* Song Number */}
                        <div className="text-gray-400 text-sm font-mono w-8 text-center">
                          {index + 1}
                        </div>
                        
                        {/* Song Info */}
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-white truncate">{song.title}</div>
                          <div className="text-gray-400 text-sm truncate">{song.artist}</div>
                        </div>
                        
                        {/* Remove Button */}
                        <button
                          onClick={() => removeSongFromEditPlaylist(song.id)}
                          className="bg-red-600/20 hover:bg-red-600 text-red-300 hover:text-white px-3 py-1 rounded text-sm transition duration-200 flex items-center space-x-1"
                          title="Remove from playlist"
                        >
                          <span>❌</span>
                          <span className="hidden sm:inline">Remove</span>
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {hasUnsavedChanges && (
                  <div className="mt-4 bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-3">
                    <p className="text-yellow-300 text-sm">
                      ⚠️ You have unsaved changes. Don't forget to save!
                    </p>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 border-t border-gray-700 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <button
                    onClick={closeEditPlaylistSongsModal}
                    className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg font-medium transition duration-300"
                    disabled={editPlaylistLoading}
                  >
                    Cancel
                  </button>
                  <button className="bg-gray-500 text-gray-300 px-4 py-2 rounded-lg font-medium cursor-not-allowed">
                    Add Songs (Coming Soon)
                  </button>
                </div>
                
                <button
                  onClick={savePlaylistSongs}
                  disabled={editPlaylistLoading || !hasUnsavedChanges}
                  className={`px-6 py-2 rounded-lg font-medium transition duration-300 ${
                    hasUnsavedChanges && !editPlaylistLoading
                      ? 'bg-purple-600 hover:bg-purple-700 text-white'
                      : 'bg-gray-500 text-gray-300 cursor-not-allowed'
                  }`}
                >
                  {editPlaylistLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* NEW: Playlist Delete Confirmation Modal */}
        {showPlaylistDeleteConfirmation && playlistToDelete && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-lg max-w-md w-full p-6">
              <div className="text-center">
                <div className="text-4xl mb-4">🗑️</div>
                <h3 className="text-xl font-bold text-white mb-2">Delete Playlist</h3>
                <p className="text-gray-300 mb-4">
                  Are you sure you want to delete "<span className="font-medium">{playlistToDelete.name}</span>"?
                </p>
                <p className="text-gray-400 text-sm mb-6">
                  This playlist has {playlistToDelete.song_count} songs. This action cannot be undone.
                </p>
                
                <div className="flex space-x-4">
                  <button
                    onClick={cancelDeletePlaylist}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={softDeletePlaylist}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Delete Playlist
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* NEW: Playlist Toast Notification */}
        {showPlaylistToast && (
          <div className="fixed top-4 right-4 z-50">
            <div className="bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-3 max-w-sm">
              <span className="text-lg">✅</span>
              <span className="font-medium">{playlistToastMessage}</span>
              <button
                onClick={() => setShowPlaylistToast(false)}
                className="text-white hover:text-gray-200 ml-2"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* NEW: Songs Tab Help Modal */}
        {showSongsHelp && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white">📚 Songs Tab Help</h2>
                <button
                  onClick={() => setShowSongsHelp(false)}
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>
              
              <div className="prose prose-invert max-w-none text-white space-y-6">
                <div>
                  <h3 className="text-xl font-semibold text-purple-300 mb-3">Options under Manage Songs:</h3>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-yellow-300 mb-2">Add a New Song</h4>
                  <p className="text-gray-300">
                    You can add songs one at a time by typing in the title and artist. RequestWave can automatically fill in details like genre, mood, and year, or you can enter them yourself.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-blue-300 mb-2">Importing a Playlist from Spotify or Apple Music</h4>
                  <p className="text-gray-300 mb-3">
                    To import a playlist from Spotify, open the playlist in your Spotify app, tap Share, then Copy Link. Paste that link into the "Import Playlist" option in RequestWave.
                  </p>
                  <p className="text-gray-300 mb-3">
                    For Apple Music, open the playlist, tap the three dots, choose Share, then Copy Link. Paste that link into the import field in RequestWave.
                  </p>
                  <p className="text-gray-300">
                    All songs from that playlist will be imported with their titles, artists, years, and metadata. Double-check the results, because cover versions or alternate recordings may sometimes have incorrect years or genres.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-green-300 mb-2">Uploading a CSV</h4>
                  <p className="text-gray-300 mb-3">
                    If you keep your songlist in a spreadsheet, you can upload a CSV file with five columns: Title, Artist, Genre, Mood, Year. We provide a blank template with these columns already set up. You can open the template in Google Sheets or Excel, fill in your songs, and upload it directly. This is a fast way to add a large number of songs.
                  </p>
                  
                  {/* CSV Download Button */}
                  <div className="bg-green-900/20 border border-green-600/30 rounded-lg p-4 mt-3">
                    <p className="text-green-300 text-sm font-medium mb-2">📥 Download CSV Template</p>
                    <button
                      onClick={() => {
                        // Create CSV template content
                        const csvContent = 'Title,Artist,Genre,Mood,Year\n"Example Song","Example Artist","Pop","Upbeat","2023"\n"Another Song","Another Artist","Rock","Energetic","2022"';
                        const blob = new Blob([csvContent], { type: 'text/csv' });
                        const url = window.URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = 'RequestWave_Song_Template.csv';
                        link.click();
                        window.URL.revokeObjectURL(url);
                      }}
                      className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white font-medium transition duration-300 flex items-center space-x-2"
                    >
                      <span>📄</span>
                      <span>Download Template</span>
                    </button>
                  </div>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-orange-300 mb-2">Uploading an LST from Songbook Pro</h4>
                  <p className="text-gray-300">
                    In Songbook Pro (sometimes referred to as Songmaker), you can export a playlist as a Text File. That file will be saved with the extension .LST. Save the file to your device, then in RequestWave use the Upload LST option to import it. This is the simplest way to bring in your existing Songbook Pro lists.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-cyan-300 mb-2">Uploading songlists in any other format</h4>
                  <p className="text-gray-300">
                    If your songs are in a word doc, or a text file, or even in a notebook you can upload that file or take a picture of your list to ChatGPT and ask Chat to format that list into a .csv file with 5 columns – Song Name, Song Artist, Genre, Mood, and Year. There's no need to even log in to ChatGPT for this task. It can even fill in missing song data by searching each song before adding it to the csv. You may need to ask it a few times if your list is long because it will try to take shortcuts and give you the list unfinished.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-purple-300 mb-2">Search Filter Options</h4>
                  <p className="text-gray-300">
                    Search for specific songs by artist or title, and order the list of the results by date added, popularity (number of requests), year, or randomize. Narrow down the search by choosing a genre, mood, year, or decade from the list. These dropdowns are populated as your songs are tagged, there is no preset list. You can also combine filters like Genre plus Decade to narrow down requests. Remember that once you've applied filters, you'll need to clear them to see all songs again.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-blue-300 mb-2">Song Tile Options</h4>
                  <p className="text-gray-300">
                    Click Edit on any song tile to change the title or artist. You can add songs to more than one artist, genre, or mood. It's a good idea to separate artists on collaboration songs so that they come up in search for any artist involved. Don't use "featuring" or "with", just add another artist. Your genre and mood lists populate as your songs are tagged. You can choose genres and moods from existing options or create new ones. To delete a genre or mood, it must be removed from all of the songs in your list. Search for the genre you want to delete and then click the small box to select all. You will see batch edit options that allow you to remove the genre from all selected songs.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-red-300 mb-2">Hiding and Deleting Songs</h4>
                  <p className="text-gray-300">
                    Hide a song if you don't want it to be included in the audience view, but still want to see it on your list. Delete a song if you never want to get a request for that song again.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-indigo-300 mb-2">Finding Songs with Missing Metadata</h4>
                  <p className="text-gray-300">
                    Use the filters for No Genre, No Mood, or No Year to quickly find songs missing information. This makes it easy to clean up your list and keep your library consistent.
                  </p>
                </div>
                
                <div>
                  <h4 className="text-lg font-semibold text-pink-300 mb-2">Working With Playlists</h4>
                  <p className="text-gray-300 mb-3">
                    Playlists help you group songs for specific shows, venues, or themes. Click the Manage button in the playlists box to set playlists to public or private. Playlists are private by default, so only you can see them. You can click the lock on a playlist to make it public, which adds a playlist filter to your audience's view. Now your requesters can choose songs from your curated playlists – super useful for things like Kids Songs and Artists Favorites that don't really fit into genres or moods but do deserve their own category.
                  </p>
                  <p className="text-gray-300 mb-3">
                    You can also choose which playlist feeds into your audience link. By default this is the All Songs playlist, but you can select a playlist to send a smaller subset of your songs to the audience link for public view. This is useful for events where certain songs are not appropriate, such as a family event, themed party, or clean-lyrics set.
                  </p>
                  <p className="text-gray-300">
                    Examples: create playlists for Irish music, Disney favorites, or Beach Vibes.
                  </p>
                </div>
              </div>
              
              <div className="mt-6 text-center">
                <button
                  onClick={() => setShowSongsHelp(false)}
                  className="bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded-lg font-medium transition duration-300"
                >
                  Got it! 👍
                </button>
              </div>
            </div>
          </div>
        )}

        {/* NEW: Song Deletion Confirmation Modal */}
        {showDeleteSongModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-sm">
              <div className="text-center">
                <div className="w-16 h-16 bg-red-600 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl">
                  🗑️
                </div>
                <h3 className="text-xl font-bold text-white mb-4">Delete Song</h3>
                <p className="text-gray-300 mb-6">
                  Are you sure you want to delete this song?
                </p>
                <div className="flex space-x-3">
                  <button
                    onClick={() => {
                      setShowDeleteSongModal(false);
                      setSongToDelete(null);
                    }}
                    className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmDeleteSong}
                    className="flex-1 bg-red-600 hover:bg-red-700 py-2 rounded-lg font-medium transition duration-300"
                  >
                    Yes
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};



const AudienceInterface = () => {
  const { slug, masterSlug, profileSlug, eventSlug } = useParams();
  const effectiveSlug = slug || masterSlug; // Use whichever is available
  const [musician, setMusician] = useState(null);
  const [profileData, setProfileData] = useState(null); // Multi-Profile context
  const [songs, setSongs] = useState([]);
  const [filteredSongs, setFilteredSongs] = useState([]);
  const [filters, setFilters] = useState({});
  const [playlists, setPlaylists] = useState([]); // NEW: Add playlists state
  const [designSettings, setDesignSettings] = useState({
    color_scheme: 'purple',
    artist_photo: null,
    show_year: true,
    show_notes: true,
    musician_name: '',
    bio: ''
  });
  const [selectedFilters, setSelectedFilters] = useState({
    genre: '',
    playlist: '', // CHANGED: Replace 'artist' with 'playlist'
    mood: '',
    year: '',
    decade: ''  // NEW: Add decade filter
  });
  const [requestForm, setRequestForm] = useState({
    requester_name: localStorage.getItem('requestwave_requester_name') || '',
    dedication: ''
  });
  const [selectedSong, setSelectedSong] = useState(null);
  const [requestStep, setRequestStep] = useState('identity'); // 'identity' (Moment 2), 'followup' (email), or 'success' (confirmation)
  const [submittedRequestId, setSubmittedRequestId] = useState(null); // Track request ID for email attachment
  const [followUpEmail, setFollowUpEmail] = useState(''); // Email captured in follow-up step
  const [loading, setLoading] = useState(true);
  // Tracks whether the initial musician/profile/event fetch has resolved
  // (either successfully or with an error). Prevents the "Musician not found"
  // screen from flashing before the musician fetch has had a chance to run.
  const [musicianFetchDone, setMusicianFetchDone] = useState(false);
  const [success, setSuccess] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  // NEW: Prominent search functionality
  const [searchQuery, setSearchQuery] = useState('');
  
  // NEW: Sort functionality state
  const [sortOption, setSortOption] = useState('most-popular'); // 'most-popular', 'alphabetical', 'newest', 'random'
  const [randomSeed, setRandomSeed] = useState(Date.now());

  // NEW: Post-request state for tip/social modal
  const [showPostRequestModal, setShowPostRequestModal] = useState(false);
  const [currentRequestId, setCurrentRequestId] = useState(null);
  
  // Phase 2: Stable anonymous audience_id for event tracking
  // Generated once per device/browser, persisted in localStorage
  const [audienceId] = useState(() => {
    const STORAGE_KEY = 'requestwave_audience_id';
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  });
  
  // NEW: Multi-step post-request flow
  const [showTipChoiceModal, setShowTipChoiceModal] = useState(false);
  const [showSocialFollowModal, setShowSocialFollowModal] = useState(false);
  const [selectedTipAmount, setSelectedTipAmount] = useState('');

  // NEW: Tip functionality state
  const [showTipModal, setShowTipModal] = useState(false);
  const [tipAmount, setTipAmount] = useState('');
  const [tipMessage, setTipMessage] = useState('');
  const [tipPlatform, setTipPlatform] = useState('paypal'); // 'paypal' or 'venmo'
  const [tipSongId, setTipSongId] = useState(null); // For integrated tips with requests
  const [showZelleModal, setShowZelleModal] = useState(false);
  const [zelleInfo, setZelleInfo] = useState({});
  const [showSocialMediaModal, setShowSocialMediaModal] = useState(false);
  
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
  
  // Orientation Side Path state (bottom sheet)
  // Entry points: header artist name tap, post-request flow
  const [showOrientation, setShowOrientation] = useState(false);
  const [orientationMode, setOrientationMode] = useState('default'); // 'default' | 'post_request'
  const [orientationScrollTarget, setOrientationScrollTarget] = useState(null); // 'tip' | null - auto-scroll to tip section
  const [tipSectionExpanded, setTipSectionExpanded] = useState(false); // Inline tip section expansion
  const [bioExpanded, setBioExpanded] = useState(false); // Bio read more/less toggle
  const tipSectionRef = React.useRef(null);
  
  // NEW: Access control state
  const [accessDenied, setAccessDenied] = useState(false);
  const [accessMessage, setAccessMessage] = useState('');

  // Debug musician data
  useEffect(() => {
    if (musician) {
      console.log('Musician data loaded:', musician);
      console.log('Has Instagram:', !!musician.instagram_username);
      console.log('Has Facebook:', !!musician.facebook_username);
      console.log('Has Spotify:', !!musician.spotify_artist_url);
      console.log('Has Apple Music:', !!musician.apple_music_artist_url);
    }
  }, [musician]);

  // NEW: Post-request click tracking
  const trackClick = async (type, platform) => {
    if (!currentRequestId) return;
    
    try {
      await axios.post(`${API}/requests/${currentRequestId}/track-click`, {
        type: type, // "tip" or "social"
        platform: platform, // "venmo", "paypal", "instagram", etc.
        audience_id: audienceId  // Phase 2: Include stable audience identifier
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
  
  // NEW: Handle tip choice flow
  const handleTipChoice = async (amount) => {
    try {
      // Submit the request with the tip amount
      const request = await submitRequestWithTip(selectedSong, amount);
      
      // Set up tip processing
      setSelectedTipAmount(amount);
      setTipAmount(amount);
      // Set default platform based on what's available
      if (musician.venmo_username) {
        setTipPlatform('venmo');
      } else if (musician.paypal_username) {
        setTipPlatform('paypal');
      } else if (musician.zelle_email || musician.zelle_phone) {
        setTipPlatform('zelle');
      }
      
      setShowTipChoiceModal(false);
      setShowTipModal(true);
      
    } catch (error) {
      // Show error instead of silently closing
      console.error('Error submitting request with tip:', error);
      alert('Error creating request. Please try again.');
      // Keep modal open so user can retry
    }
  };
  
  const handleNoTip = async () => {
    try {
      // Submit the request with no tip
      await submitRequestWithTip(selectedSong, 0);
      
      setShowTipChoiceModal(false);
      setShowSocialFollowModal(true);
      
    } catch (error) {
      // Show error instead of silently closing
      console.error('Error submitting request without tip:', error);
      alert('Error creating request. Please try again.');
      // Keep modal open so user can retry
    }
  };
  
  const closeTipFlow = () => {
    setShowTipChoiceModal(false);
    setShowSocialFollowModal(false);
    setCurrentRequestId(null);
    setSelectedTipAmount('');
    setSelectedSong(null); // Clear selected song when closing flow
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
    if (eventSlug && profileSlug && masterSlug) {
      // Event mode: fetch event-merged audience payload
      fetchDesignSettings().then(() => fetchEventData());
    } else if (profileSlug && masterSlug) {
      // Profile mode: fetch design settings first, then profile data overrides name/bio
      fetchDesignSettings().then(() => fetchProfileData());
    } else {
      // Standard mode: fetchMusician may detect a default profile and override designSettings
      fetchDesignSettings().then(() => {
        fetchMusician();
      });
      fetchSongs();
      fetchFilters();
      fetchPlaylists(); // NEW: Fetch playlists for audience filtering
    }
    
    // NEW: Handle URL parameters for sort option
    const urlParams = new URLSearchParams(window.location.search);
    const sortParam = urlParams.get('sort');
    if (sortParam && ['most-popular', 'alphabetical', 'newest', 'random'].includes(sortParam)) {
      setSortOption(sortParam);
      if (sortParam === 'random') {
        setRandomSeed(Date.now());
      }
    }
  }, [slug, masterSlug, profileSlug, eventSlug]);

  // Event-mode data fetcher (3-segment URL)
  const fetchEventData = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${masterSlug}/${profileSlug}/${eventSlug}`);
      const data = response.data;
      setMusician(data);
      setProfileData(data);
      setSongs(data.songs || []);
      setFilteredSongs(data.songs || []);
      if (data.design_settings) {
        setDesignSettings(prev => ({ ...prev, ...data.design_settings }));
      } else {
        setDesignSettings(prev => ({
          ...prev,
          musician_name: data.name || prev.musician_name,
          bio: data.bio || prev.bio,
        }));
      }
      setLoading(false);
    } catch (error) {
      console.error('Event fetch failed:', error);
      setLoading(false);
    } finally {
      setMusicianFetchDone(true);
    }
  };

  // Profile-mode data fetcher
  const fetchProfileData = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${masterSlug}/${profileSlug}`);
      const data = response.data;
      setMusician(data);
      setProfileData(data);
      setSongs(data.songs || []);
      setFilteredSongs(data.songs || []);
      // Override designSettings with profile design settings
      if (data.design_settings) {
        setDesignSettings(prev => ({
          ...prev,
          ...data.design_settings,
        }));
      } else {
        // Fallback: override name/bio at minimum
        setDesignSettings(prev => ({
          ...prev,
          musician_name: data.name || prev.musician_name,
          bio: data.bio || prev.bio,
        }));
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching profile data:', error);
      setLoading(false);
    } finally {
      setMusicianFetchDone(true);
    }
  };

  // NEW: Update URL when sort option changes
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (sortOption === 'most-popular') {
      urlParams.delete('sort');
    } else {
      urlParams.set('sort', sortOption);
    }
    
    const newUrl = urlParams.toString() ? 
      `${window.location.pathname}?${urlParams.toString()}` : 
      window.location.pathname;
    window.history.replaceState({}, '', newUrl);
  }, [sortOption]);

  useEffect(() => {
    if (musician) {
      fetchSongs(); // Use backend filtering instead of client-side
    }
  }, [selectedFilters, searchQuery, musician]); // Trigger when filters or search changes

  // NEW: Apply sorting when songs or sort options change
  useEffect(() => {
    if (songs.length > 0) {
      const sorted = applyAudienceSorting(songs);
      setFilteredSongs(sorted);
    }
  }, [songs, sortOption, randomSeed]);

  const fetchMusician = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${effectiveSlug}`);
      const data = response.data;
      setMusician(data);
      // If response includes songs (default profile active), use them directly
      if (data.songs !== undefined && data.profile_id) {
        setProfileData(data);
        setSongs(data.songs || []);
        setFilteredSongs(data.songs || []);
        // Override designSettings with profile design settings
        if (data.design_settings) {
          setDesignSettings(prev => ({
            ...prev,
            ...data.design_settings,
          }));
        } else {
          setDesignSettings(prev => ({
            ...prev,
            musician_name: data.name || prev.musician_name,
            bio: data.bio || prev.bio,
          }));
        }
        setLoading(false);
      }
    } catch (error) {
      console.error('Error fetching musician:', error);
    } finally {
      setMusicianFetchDone(true);
    }
  };

  const fetchDesignSettings = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${effectiveSlug}/design`);
      setDesignSettings(response.data);
      return response.data;
    } catch (error) {
      console.error('Error fetching design settings:', error);
    }
  };

  const fetchPlaylists = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${effectiveSlug}/playlists`);
      setPlaylists(response.data);
    } catch (error) {
      console.error('Error fetching playlists:', error);
      setPlaylists([]); // Set empty array on error
    }
  };

  const fetchSongs = async () => {
    try {
      // In profile mode, songs come from the profile endpoint
      if (profileSlug && profileData) {
        setLoading(false);
        return;
      }
      
      // First check if access is granted
      const accessResponse = await axios.get(`${API}/musicians/${effectiveSlug}/access-check`);
      
      if (!accessResponse.data.access_granted) {
        setAccessDenied(true);
        setAccessMessage(accessResponse.data.message || 'This artist\'s request page is paused');
        setLoading(false);
        return;
      }

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
      if (selectedFilters.playlist) {
        params.append('playlist', selectedFilters.playlist);
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
      const url = `${API}/musicians/${effectiveSlug}/songs${queryString ? `?${queryString}` : ''}`;
      
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
      const response = await axios.get(`${API}/musicians/${effectiveSlug}/filters`);
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
    if (selectedFilters.playlist) {
      // Note: Playlist filtering is handled by backend, this is for client-side fallback
      // The playlist filter would need access to playlist songs data to work client-side
      // For now, we rely on backend filtering
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

    // NEW: Apply sorting
    filtered = applyAudienceSorting(filtered);

    setFilteredSongs(filtered);
  };

  // NEW: Audience sorting function
  const applyAudienceSorting = (songsToSort) => {
    const sorted = [...songsToSort];
    
    switch (sortOption) {
      case 'most-popular':
        return sorted.sort((a, b) => (b.unique_show_count || 0) - (a.unique_show_count || 0));
      case 'alphabetical':
        return sorted.sort((a, b) => a.title.localeCompare(b.title));
      case 'newest':
        return sorted.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      case 'random':
        // Use seeded random for consistent results
        const seededRandom = (seed) => {
          const x = Math.sin(seed) * 10000;
          return x - Math.floor(x);
        };
        return sorted.sort((a, b) => {
          const seedA = (a.id.charCodeAt(0) + randomSeed) % 1000;
          const seedB = (b.id.charCodeAt(0) + randomSeed) % 1000;
          return seededRandom(seedA) - seededRandom(seedB);
        });
      default:
        return sorted;
    }
  };

  // NEW: Shuffle function for audience random sort
  const handleAudienceShuffle = () => {
    setRandomSeed(Date.now());
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

    // Show the request modal at identity step (Moment 2) - skip confirmation
    setRequestStep('identity');
    setSelectedSong(randomSong);
  };

  const handleRequest = async (song) => {
    if (!requestForm.requester_name) {
      alert('Please enter your name');
      return;
    }

    // Check if requests are disabled
    if (musician.requests_enabled === false) {
      alert('Song requests are currently disabled. Please try again later.');
      return;
    }

    try {
      // Submit request first
      const submittedRequest = await submitRequestWithTip(song, 0);
      if (submittedRequest) {
        // Store the request ID for potential email attachment in Moment 3
        setSubmittedRequestId(submittedRequest.id);
        
        // Persist requester name to localStorage for future requests
        localStorage.setItem('requestwave_requester_name', requestForm.requester_name);
        
        // Clear dedication for next request, but preserve requester name
        setRequestForm(prev => ({ ...prev, dedication: '' }));
        
        // Check if email already exists in localStorage - skip Moment 3 if so
        const savedEmail = localStorage.getItem('requestwave_requester_email');
        if (savedEmail) {
          // Skip Moment 3, go directly to success/tip screen
          // Initialize tip state
          setTipAmount('');
          setTipMessage('');
          if (musician?.venmo_enabled && musician.venmo_username) {
            setTipPlatform('venmo');
          } else if (musician?.paypal_enabled && musician.paypal_username) {
            setTipPlatform('paypal');
          } else if (musician?.cash_app_enabled && musician.cash_app_username) {
            setTipPlatform('cashapp');
          } else if (musician?.zelle_enabled && (musician.zelle_email || musician.zelle_phone)) {
            setTipPlatform('zelle');
          }
          setRequestStep('success_tip');
        } else {
          // No saved email - show Moment 3: Optional Email Follow-Up
          setRequestStep('followup');
          setFollowUpEmail('');
        }
      }
    } catch (error) {
      console.error('Error submitting request:', error);
      alert('Error creating request. Please try again.');
    }
  };
  
  // Handle Moment 3 completion (skip or add email)
  const [followUpError, setFollowUpError] = useState('');
  
  const handleFollowUpComplete = async (addEmail = false) => {
    setFollowUpError('');
    
    if (addEmail && followUpEmail && submittedRequestId) {
      try {
        // Call backend endpoint to attach email to request
        await axios.post(`${API}/requests/${submittedRequestId}/email`, {
          email: followUpEmail,
          audience_id: audienceId
        });
        
        // Persist email to localStorage for future requests
        localStorage.setItem('requestwave_requester_email', followUpEmail);
        
        // Clear the email input on success
        setFollowUpEmail('');
      } catch (error) {
        console.error('Error attaching email:', error);
        const errorMessage = error.response?.data?.detail || 'Failed to add email. Please try again.';
        setFollowUpError(errorMessage);
        return; // Don't proceed if email attachment failed
      }
    }
    
    // Initialize tip state for combined success+tip screen
    setTipAmount('');
    setTipMessage('');
    // Set default platform based on what's available and enabled
    if (musician?.venmo_enabled && musician.venmo_username) {
      setTipPlatform('venmo');
    } else if (musician?.paypal_enabled && musician.paypal_username) {
      setTipPlatform('paypal');
    } else if (musician?.cash_app_enabled && musician.cash_app_username) {
      setTipPlatform('cashapp');
    } else if (musician?.zelle_enabled && (musician.zelle_email || musician.zelle_phone)) {
      setTipPlatform('zelle');
    }
    
    // Go to combined success + tip step
    setRequestStep('success_tip');
  };
  
  // Handle "Send tip" from success_tip - triggers payment, closes modal, opens Orientation post_request
  const handleSendTip = async () => {
    if (!tipAmount || parseFloat(tipAmount) <= 0) return;
    
    const currentAmount = parseFloat(tipAmount);
    const currentPlatform = tipPlatform;
    
    // Record tip attempt first
    try {
      await axios.post(`${API}/musicians/${musician.slug}/tips`, {
        amount: currentAmount,
        platform: currentPlatform,
        tipper_name: requestForm.requester_name || 'Anonymous',
        message: tipMessage
      });
    } catch (error) {
      console.log('Tip tracking failed:', error);
    }
    
    // Close the success_tip modal BEFORE triggering payment
    setSelectedSong(null);
    setRequestStep('identity');
    setSubmittedRequestId(null);
    setFollowUpEmail('');
    
    // Open Orientation in post_request mode
    setOrientationMode('post_request');
    setShowOrientation(true);
    
    // Clear tip values
    setTipAmount('');
    setTipMessage('');
    
    // Trigger payment action (uses window.location.href for same-tab navigation)
    if (currentPlatform === 'zelle') {
      // Zelle: show instructions modal
      setZelleInfo({
        contact: musician.zelle_email || musician.zelle_phone,
        contactType: musician.zelle_email ? 'email' : 'phone',
        amount: currentAmount,
        message: tipMessage || 'Thanks for the music!'
      });
      setShowZelleModal(true);
    } else {
      // Venmo/PayPal/CashApp: navigate directly using window.location.assign
      let paymentUrl = null;
      // Sanitize amount: remove $ and commas
      const cleanAmount = String(currentAmount).replace(/[$,]/g, '').trim();
      
      if (currentPlatform === 'venmo') {
        paymentUrl = `venmo://paycharge?txn=pay&recipients=${musician.venmo_username}&amount=${cleanAmount}&note=${encodeURIComponent(tipMessage || 'Thanks for the music!')}`;
      } else if (currentPlatform === 'paypal') {
        // Sanitize PayPal username: trim whitespace, remove leading @
        const sanitizedPaypalUsername = (musician.paypal_username || '').trim().replace(/^@/, '');
        if (sanitizedPaypalUsername) {
          paymentUrl = cleanAmount ? `https://paypal.me/${sanitizedPaypalUsername}/${cleanAmount}` : `https://paypal.me/${sanitizedPaypalUsername}`;
        }
      } else if (currentPlatform === 'cashapp') {
        paymentUrl = `https://cash.app/$${musician.cash_app_username}/${cleanAmount}`;
      }
      
      if (paymentUrl) {
        console.log(`Opening payment URL: ${paymentUrl}`);
        window.location.assign(paymentUrl);
      }
    }
  };
  
  // Handle "Skip / I'm all set" from success_tip - closes modal, opens Orientation post_request
  const handleSkipTip = () => {
    // Close the success_tip modal
    setSelectedSong(null);
    setRequestStep('identity');
    setSubmittedRequestId(null);
    setFollowUpEmail('');
    setTipAmount('');
    setTipMessage('');
    
    // Open Orientation in post_request mode
    setOrientationMode('post_request');
    setShowOrientation(true);
  };
  
  // Handle "Leave a tip" button inside Orientation post_request - expands inline tip section
  const handleToggleTipSection = () => {
    setTipSectionExpanded(!tipSectionExpanded);
  };
  
  // Trigger external payment link from Orientation tip section
  const triggerPaymentLink = async (amount, platform) => {
    // Record tip attempt
    try {
      await axios.post(`${API}/musicians/${musician.slug}/tips`, {
        amount: amount,
        platform: platform,
        tipper_name: requestForm.requester_name || 'Anonymous',
        message: tipMessage
      });
    } catch (error) {
      console.log('Tip tracking failed:', error);
    }
    
    if (platform === 'zelle') {
      // Zelle: show Zelle modal
      setZelleInfo({
        contact: musician.zelle_email || musician.zelle_phone,
        contactType: musician.zelle_email ? 'email' : 'phone',
        amount: amount,
        message: tipMessage || 'Thanks for the music!'
      });
      setShowZelleModal(true);
    } else {
      // Venmo/PayPal/CashApp: navigate directly using window.location.assign
      let paymentUrl = null;
      // Sanitize amount: remove $ and commas, keep clean number
      const cleanAmount = String(amount).replace(/[$,]/g, '').trim();
      
      if (platform === 'venmo') {
        paymentUrl = `venmo://paycharge?txn=pay&recipients=${musician.venmo_username}&amount=${cleanAmount}&note=${encodeURIComponent(tipMessage || 'Thanks for the music!')}`;
      } else if (platform === 'paypal') {
        // Sanitize PayPal username: trim whitespace, remove leading @
        const sanitizedPaypalUsername = (musician.paypal_username || '').trim().replace(/^@/, '');
        if (sanitizedPaypalUsername) {
          paymentUrl = cleanAmount ? `https://paypal.me/${sanitizedPaypalUsername}/${cleanAmount}` : `https://paypal.me/${sanitizedPaypalUsername}`;
        }
      } else if (platform === 'cashapp') {
        paymentUrl = `https://cash.app/$${musician.cash_app_username}/${cleanAmount}`;
      }
      
      if (paymentUrl) {
        console.log(`Opening payment URL: ${paymentUrl}`);
        window.location.assign(paymentUrl);
      }
    }
    
    // Clear tip values
    setTipAmount('');
    setTipMessage('');
  };
  
  // Helper: Get sanitized PayPal URL for display/fallback
  const getPayPalUrl = (amount) => {
    const sanitizedUsername = (musician?.paypal_username || '').trim().replace(/^@/, '');
    if (!sanitizedUsername) return null;
    const cleanAmount = amount ? String(amount).replace(/[$,]/g, '').trim() : '';
    return cleanAmount ? `https://paypal.me/${sanitizedUsername}/${cleanAmount}` : `https://paypal.me/${sanitizedUsername}`;
  };
  
  // Handle "About / Follow" from success_tip - opens Orientation (same as skip now)
  const handlePostRequestOrientation = () => {
    // Close the modal and reset state
    setSelectedSong(null);
    setRequestStep('identity');
    setSubmittedRequestId(null);
    setFollowUpEmail('');
    setTipAmount('');
    setTipMessage('');
    
    // Open Orientation in post_request mode
    setOrientationMode('post_request');
    setShowOrientation(true);
  };
  
  // Handle "Back to songs" from success_tip or Orientation - closes everything
  const handleBackToSongs = () => {
    // Close the modal and reset state
    setSelectedSong(null);
    setRequestStep('identity');
    setSubmittedRequestId(null);
    setFollowUpEmail('');
    setTipAmount('');
    setTipMessage('');
    // Also close Orientation if open
    setShowOrientation(false);
  };
  
  // NEW: Actually submit the request with tip information
  const submitRequestWithTip = async (song, tipAmount = 0) => {
    try {
      const response = await axios.post(`${API}/requests`, {
        song_id: song.id,
        requester_name: requestForm.requester_name,
        requester_email: '', // Email now captured in Moment 3, not at submission
        dedication: requestForm.dedication || '',
        tip_amount: parseFloat(tipAmount) || 0.0,
        audience_id: audienceId,  // Phase 2: Include stable audience identifier
        profile_slug: profileSlug || null,  // Multi-Profile: pass profile context
        event_slug: eventSlug || null  // Events: pass event context if present
      });
      
      // Store request ID for analytics
      setCurrentRequestId(response.data.id);
      
      // Don't reset form here - keep the data for potential tip flow
      // Form will be reset later after tip/social flow completes
      
      return response.data;
      
    } catch (error) {
      if (error.response?.status === 402) {
        // Request limit reached
        const errorData = error.response.data;
        alert(`Request limit reached! ${errorData.detail.message}\n\nThe musician has reached their monthly request limit. They need to upgrade to Pro for unlimited requests.`);
      } else {
        console.error('Error submitting request:', error);
        alert('Error submitting request. Please try again.');
      }
      throw error;
    }
  };

  const clearFilters = () => {
    setSelectedFilters({
      genre: '',
      playlist: '',
      mood: '',
      year: '',
      decade: ''  // NEW: Clear decade filter
    });
    // NEW: Also clear search query
    setSearchQuery('');
  };

  // NEW: Tip functionality functions
  const getTipPresetAmounts = () => [3, 5, 10];

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
              message: tipMessage,
              audience_id: audienceId,  // Phase 2: Include stable audience identifier
              show_id: musician?.current_show_id || null  // Phase 2: Include show context if available
            });
          } catch (error) {
            console.log('Tip tracking failed:', error); // Non-critical
          }

          // Handle PayPal/Venmo payment links
          if (tipPlatform === 'venmo' && paymentUrl.startsWith('venmo://')) {
            // For Venmo deep links, implement fallback for desktop browsers
            // Extract Venmo username from the venmo link
            const venmoMatch = paymentUrl.match(/recipients=([^&]+)/);
            const venmoUsername = venmoMatch ? venmoMatch[1] : 'this musician';
            
            try {
              // Try to open the Venmo app first
              window.location.href = paymentUrl;
              
              // Show instructions for desktop users or if app isn't installed
              setTimeout(() => {
                alert(`Opening Venmo app to send $${amount} tip to @${venmoUsername}!\n\nIf Venmo app didn't open:\n1. Open Venmo app manually\n2. Search for @${venmoUsername}\n3. Send $${amount} with message: "${tipMessage || 'Thanks for the music!'}"`);
              }, 1000);
              
            } catch (error) {
              // Fallback for desktop users
              alert(`To send your $${amount} tip:\n\n1. Open Venmo app on your phone\n2. Search for @${venmoUsername}\n3. Send $${amount} with message: "${tipMessage || 'Thanks for the music!'}"`);
            }
          } else {
            // PayPal links work universally
            window.open(paymentUrl, '_blank');
            alert(`Opening ${tipPlatform === 'paypal' ? 'PayPal' : 'Venmo'} to send your $${amount} tip!`);
          }
          
          // Close modal
          setShowTipModal(false);
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

  // Handle tip submission in audience interface
  const handleAudienceInterfaceTipSubmit = async () => {
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
      const response = await axios.get(`${API}/musicians/${musician.slug}/tip-links`, {
        params: {
          amount: amount,
          message: tipMessage || `Thanks for the music!${tipSongId ? ' (with song request)' : ''}`
        }
      });

      if (response.data) {
        // Get appropriate payment link
        let paymentUrl = null;
        if (tipPlatform === 'paypal' && response.data.paypal_link) {
          paymentUrl = response.data.paypal_link;
        } else if (tipPlatform === 'venmo' && response.data.venmo_link) {
          paymentUrl = response.data.venmo_link;
        } else if (tipPlatform === 'cashapp' && response.data.cash_app_link) {
          paymentUrl = response.data.cash_app_link;
        }

        // Record the tip attempt for analytics
        try {
          await axios.post(`${API}/musicians/${musician.slug}/tips`, {
            amount: amount,
            platform: tipPlatform,
            tipper_name: requestForm.requester_name || 'Anonymous',
            message: tipMessage
          });
        } catch (error) {
          console.log('Tip tracking failed:', error); // Non-critical
        }

        if (tipPlatform === 'zelle') {
          // For Zelle, show special modal with copy functionality
          setZelleInfo({
            contact: musician.zelle_email || musician.zelle_phone,
            contactType: musician.zelle_email ? 'email' : 'phone',
            amount: amount,
            message: tipMessage || 'Thanks for the music!'
          });
          setShowTipModal(false);
          setShowZelleModal(true);
        } else if (paymentUrl) {
          // Handle PayPal/Venmo/Cash App payment links
          if (tipPlatform === 'venmo' && paymentUrl.startsWith('venmo://')) {
            const venmoMatch = paymentUrl.match(/recipients=([^&]+)/);
            const venmoUsername = venmoMatch ? venmoMatch[1] : 'this musician';
            
            try {
              window.location.href = paymentUrl;
              setTimeout(() => {
                alert(`Opening Venmo app to send $${amount} tip to @${venmoUsername}!`);
              }, 500);
            } catch (error) {
              alert(`To send your $${amount} tip:\n\n1. Open Venmo app on your phone\n2. Search for @${venmoUsername}\n3. Send $${amount} with message: "${tipMessage || 'Thanks for the music!'}"`);
            }
          } else if (tipPlatform === 'cashapp') {
            window.open(paymentUrl, '_blank');
            alert(`Opening Cash App to send your $${amount} tip!`);
          } else {
            // PayPal links work universally
            window.open(paymentUrl, '_blank');
            alert(`Opening PayPal to send your $${amount} tip!`);
          }
          
          // Close tip modal and show social media
          setShowTipModal(false);
          setShowSocialMediaModal(true);
        } else {
          const platformName = tipPlatform === 'paypal' ? 'PayPal' : 
                             tipPlatform === 'venmo' ? 'Venmo' : 
                             tipPlatform === 'cashapp' ? 'Cash App' : 'Zelle';
          alert(`${platformName} is not set up for this musician`);
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

  // Handle no tip selection - go straight to social media
  const handleAudienceNoTip = () => {
    setShowTipModal(false);
    setShowSocialMediaModal(true);
  };

  // Reset form after complete flow
  const resetRequestForm = () => {
    setRequestForm({
      requester_name: '',
      requester_email: '',
      dedication: ''
    });
    setSelectedSong(null);
    setTipSongId(null);
    setCurrentRequestId(null);
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

  if (loading || !musicianFetchDone) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  // NEW: Access denied screen for paused audience links
  if (accessDenied) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-gray-800 rounded-xl p-8 text-center">
          <div className="text-6xl mb-4">😔</div>
          <h1 className="text-2xl font-bold text-white mb-4">Request Page Paused</h1>
          <p className="text-gray-300 mb-6">
            {accessMessage || "This artist's request page is currently paused"}
          </p>
          <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
            <p className="text-blue-300 text-sm">
              <strong>For the artist:</strong> Visit your dashboard's Subscription tab to reactivate your audience link.
            </p>
          </div>
        </div>
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
      {/* Header: Stable frame with artist identity */}
      <header className="bg-gray-800/95 sticky top-0 z-40 border-b border-gray-700/50">
        <div className="max-w-4xl mx-auto px-4 py-3">
          {/* Artist identity - image + name + chevron as ONE tappable target → Orientation */}
          <button
            onClick={() => {
              setOrientationMode('default');
              setShowOrientation(true);
            }}
            className="flex items-center w-full hover:bg-gray-700/30 rounded-lg px-1.5 py-1.5 transition duration-200"
            data-testid="artist-header-orientation-trigger"
          >
            {/* Artist avatar - sized to match text height */}
            {designSettings.artist_photo && (
              <img
                src={designSettings.artist_photo}
                alt={designSettings.musician_name}
                className="w-6 h-6 rounded-full object-cover flex-shrink-0 mr-2 ring-1 ring-gray-600/50"
              />
            )}
            <div className="flex-1 min-w-0 text-left">
              <div className="flex items-center">
                {/* Live indicator dot - only visible when current_show_name exists */}
                {musician?.current_show_name && (
                  <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0 mr-1.5 animate-live-dot" />
                )}
                <h1 className={`text-lg font-semibold ${colors.accent} truncate`}>
                  {designSettings.musician_name}
                </h1>
                <svg className="w-4 h-4 text-gray-500 flex-shrink-0 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
              {/* Helper line: Left (About·Tip·Follow) + Right (Live Now with glow) */}
              <div className="flex items-center justify-between text-xs gap-2">
                <span className="text-gray-500 flex-shrink-0">About · Tip · Follow</span>
                {musician?.current_show_name && (
                  <span className="text-green-400 animate-live-glow truncate min-w-0">
                    Live Now: {musician.current_show_name}
                  </span>
                )}
              </div>
            </div>
            {/* RequestWave logo - visible brand presence with ambient glow */}
            <div className="relative flex-shrink-0 ml-3">
              <img
                src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png"
                alt="RequestWave"
                className="w-7 h-7 object-contain opacity-70 relative z-10"
              />
              <div 
                className="absolute -inset-1 rounded-full animate-logo-glow"
                style={{
                  background: 'radial-gradient(circle, rgba(139, 92, 246, 0.4) 0%, rgba(139, 92, 246, 0.15) 50%, transparent 70%)',
                  filter: 'blur(4px)',
                }}
              />
            </div>
          </button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-4 md:py-6">
        {success && (
          <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-3 md:p-4 mb-4 md:mb-6 text-green-200">
            {success}
          </div>
        )}

        {/* Moment 1A: Primary instruction - visible without scrolling */}
        {musician?.requests_enabled !== false && (
          <div className="text-center mb-5 md:mb-6">
            <p className="text-lg md:text-xl text-gray-200 font-medium tracking-wide">
              Tap a song to request it.
            </p>
            {localStorage.getItem('requestwave_requester_name') && (
              <p className="text-sm text-gray-400 mt-1">
                Welcome back, {localStorage.getItem('requestwave_requester_name')}
              </p>
            )}
          </div>
        )}

        {/* Search Bar - De-emphasized styling */}
        <div className="bg-gray-800/50 rounded-xl p-3 md:p-4 mb-3 md:mb-4">
          <div className="flex flex-col space-y-2">
            <div className="relative">
              <input
                type="text"
                placeholder="Search songs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 focus:border-blue-500 rounded-lg px-4 py-2 md:py-3 text-white placeholder-gray-400 text-sm md:text-base focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all duration-300"
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
            
            {/* Sort and Filter Controls - Compact row */}
            <div className="flex items-center justify-between gap-2">
              <select
                value={sortOption}
                onChange={(e) => setSortOption(e.target.value)}
                className="bg-gray-700 border border-gray-600 focus:border-blue-500 rounded-lg px-2 py-1.5 text-gray-300 text-xs focus:outline-none transition-all duration-300"
                aria-label="Sort by"
              >
                <option value="most-popular">Most Popular</option>
                <option value="alphabetical">A→Z</option>
                <option value="newest">Newest</option>
                <option value="random">Random</option>
              </select>
              {sortOption === 'random' && (
                <button
                  onClick={handleAudienceShuffle}
                  className="text-gray-400 hover:text-white px-2 py-1.5 rounded-lg text-xs flex items-center space-x-1 transition duration-300"
                  title="Shuffle"
                  aria-label="Shuffle songs"
                >
                  <span>🔀</span>
                  <span className="hidden sm:inline">Shuffle</span>
                </button>
              )}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="text-gray-400 hover:text-white px-2 py-1.5 rounded-lg text-xs transition duration-300"
              >
                {showFilters ? 'Hide Filters' : 'Browse / Filter'}
              </button>
            </div>
            {searchQuery && (
              <p className="text-xs text-gray-400">
                Searching: "<span className="text-gray-300">{searchQuery}</span>"
              </p>
            )}
          </div>
        </div>

        {/* Advanced Filters - Collapsed by default, de-emphasized */}
        {showFilters && (
          <div className="bg-gray-800/30 rounded-lg p-3 md:p-4 mb-3 md:mb-4 border border-gray-700/50">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-400">Browse / Filter</span>
              <button
                onClick={clearFilters}
                className="text-gray-500 hover:text-gray-300 text-xs transition duration-300"
              >
                Clear
              </button>
            </div>
            
            <div className="space-y-2">
              {/* Playlists Dropdown */}
              <select
                value={selectedFilters.playlist}
                onChange={(e) => setSelectedFilters({...selectedFilters, playlist: e.target.value})}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-300 text-sm"
              >
                <option value="">All Playlists</option>
                {playlists.map((playlist) => (
                  <option key={playlist.id} value={playlist.id}>
                    {playlist.name} ({playlist.song_count})
                  </option>
                ))}
              </select>
              
              {/* Compact filter grid */}
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={selectedFilters.genre}
                  onChange={(e) => setSelectedFilters({...selectedFilters, genre: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-gray-300 text-sm"
                >
                  <option value="">Genre</option>
                  {filters.genres?.map((genre) => (
                    <option key={genre} value={genre}>{genre}</option>
                  ))}
                </select>
                
                <select
                  value={selectedFilters.mood}
                  onChange={(e) => setSelectedFilters({...selectedFilters, mood: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-gray-300 text-sm"
                >
                  <option value="">Mood</option>
                  {filters.moods?.map((mood) => (
                    <option key={mood} value={mood}>{mood}</option>
                  ))}
                </select>
                
                <select
                  value={selectedFilters.year}
                  onChange={(e) => setSelectedFilters({...selectedFilters, year: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-gray-300 text-sm"
                >
                  <option value="">Year</option>
                  {filters.years?.map((year) => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
                
                <select
                  value={selectedFilters.decade}
                  onChange={(e) => setSelectedFilters({...selectedFilters, decade: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-2 py-1.5 text-gray-300 text-sm"
                >
                  <option value="">Decade</option>
                  {filters.decades?.map((decade) => (
                    <option key={decade} value={decade}>{decade}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Songs Display */}
        <div className="mb-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <p className="text-gray-500 text-sm">
            {filteredSongs.length} song{filteredSongs.length !== 1 ? 's' : ''}
            {(selectedFilters.genre || selectedFilters.playlist || selectedFilters.mood || selectedFilters.year || selectedFilters.decade || searchQuery) && ' matching'}
          </p>
          
          {/* Surprise Me Button */}
          {filteredSongs.length > 0 && musician?.requests_enabled !== false && (
            <button
              onClick={handleRandomSong}
              data-testid="surprise-me-btn"
              className="text-gray-400 hover:text-white px-3 py-1.5 rounded-lg text-sm transition duration-300 flex items-center space-x-2 border border-gray-700 hover:border-gray-500"
            >
              <span>🎲</span>
              <span>Surprise Me</span>
            </button>
          )}
        </div>

        {/* Songs List */}
        {musician?.requests_enabled === false ? (
          /* Requests Disabled Message */
          <div className="bg-orange-900/20 border border-orange-500/30 rounded-xl p-8 text-center">
            <div className="text-5xl mb-4">🎤</div>
            <h3 className="text-xl font-bold text-orange-300 mb-3">Song Requests Are Currently Off</h3>
            <p className="text-gray-300 mb-6">
              {musician.name} has temporarily disabled song requests. You can still:
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              {/* Allow Song Suggestions Button */}
              <button
                onClick={() => setShowSuggestionModal(true)}
                className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-6 py-3 rounded-lg font-medium transition duration-300 flex items-center space-x-2 shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <span>💡</span>
                <span>Suggest a Song</span>
              </button>
              
              {/* Show Tip Button if tips are enabled */}
              {musician?.tips_enabled !== false && (
                <button
                  onClick={() => setShowTipModal(true)}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-6 py-3 rounded-lg font-medium transition duration-300 flex items-center space-x-2 shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  <span>💰</span>
                  <span>Send a Tip</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Normal Songs Display - Tappable cards */
          <div className="space-y-2 md:space-y-3">
            {filteredSongs.map((song) => (
              <button
                key={song.id}
                onClick={() => {
                  setRequestStep('identity');
                  setSelectedSong(song);
                }}
                data-testid={`song-card-${song.id}`}
                className="w-full text-left rounded-lg py-2.5 px-3.5
                  hover:brightness-110
                  active:scale-[0.98] active:brightness-95
                  transition-all duration-150 ease-out cursor-pointer
                  border border-gray-700/30
                  flex items-center space-x-4"
                style={{
                  background: 'linear-gradient(to bottom, rgb(42, 48, 60) 0%, rgb(31, 41, 55) 100%)'
                }}
              >
                <div className="flex-1 min-w-0">
                  {/* Single-line format: Title · Artist for better density */}
                  <p className="truncate text-sm">
                    <span className="font-semibold text-white">{song.title}</span>
                    <span className="text-gray-600 mx-1.5">·</span>
                    <span className="text-gray-400">{song.artist}</span>
                  </p>
                </div>
                {(song.requests_this_show || 0) > 0 && (
                  <span
                    data-testid={`audience-song-tonight-badge-${song.id}`}
                    className="bg-orange-600 text-white text-xs px-2 py-1 rounded-full font-semibold whitespace-nowrap shrink-0"
                  >
                    🔥 {song.requests_this_show} tonight
                  </span>
                )}
              </button>
            ))}
            
            {filteredSongs.length === 0 && (
              <div className="text-center py-12 md:py-16">
                <div className="text-4xl md:text-6xl mb-4">🎵</div>
                <p className="text-gray-400 text-lg md:text-xl mb-2">No songs match your search</p>
                
                {/* NEW: Empty Search → Big Green Suggestion Button */}
                {searchQuery && (
                  <div className="mb-6">
                    <p className="text-gray-300 text-lg mb-4">Can't find the song you want?</p>
                    <button
                      onClick={() => setShowSuggestionModal(true)}
                      className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-8 py-4 rounded-xl font-bold text-lg transition duration-300 flex items-center justify-center space-x-3 shadow-lg hover:shadow-xl transform hover:scale-105 w-full sm:w-auto"
                    >
                      <span className="text-2xl">💡</span>
                      <span>Suggest a Song</span>
                    </button>
                  </div>
                )}
                
                <button
                  onClick={clearFilters}
                  className={`${colors.button} px-6 py-2 rounded-lg font-medium transition duration-300`}
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>
        )}

        {/* Request Modal - Direct to Moment 2 (Identity) */}
        {selectedSong && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-end md:items-center justify-center p-4 z-50">
            <div className="bg-gray-800 rounded-t-xl md:rounded-xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
              
              {/* Moment 2: Identity + Dedication */}
              {requestStep === 'identity' && (
                <>
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1 min-w-0 mr-4">
                      <h2 className="text-xl font-bold mb-1 truncate">Request: {selectedSong.title}</h2>
                      <p className="text-gray-400 text-sm truncate">{selectedSong.artist}</p>
                    </div>
                    <button
                      onClick={() => setSelectedSong(null)}
                      className="text-gray-400 hover:text-white text-2xl leading-none"
                    >
                      ×
                    </button>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <input
                        type="text"
                        placeholder="Your Name"
                        value={requestForm.requester_name}
                        onChange={(e) => setRequestForm({...requestForm, requester_name: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                        required
                        data-testid="request-name-input"
                      />
                    </div>
                    
                    <div>
                      <textarea
                        placeholder="Optional note for the artist (celebration or dedication)"
                        value={requestForm.dedication}
                        onChange={(e) => setRequestForm({...requestForm, dedication: e.target.value})}
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                        rows="3"
                        data-testid="request-dedication-input"
                      />
                    </div>
                  </div>
                  
                  <div className="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-4 mt-6">
                    <button
                      onClick={() => setSelectedSong(null)}
                      className="flex-1 bg-gray-600 hover:bg-gray-700 py-3 rounded-lg transition duration-300 order-2 md:order-1"
                      data-testid="identity-back-btn"
                    >
                      Back
                    </button>
                    <button
                      onClick={() => handleRequest(selectedSong)}
                      className={`flex-1 ${colors.button} py-3 rounded-lg font-bold transition duration-300 order-1 md:order-2`}
                      data-testid="request-submit-btn"
                    >
                      Send Request
                    </button>
                  </div>
                </>
              )}
              
              {/* Email Step: Identity moment (optional) */}
              {requestStep === 'followup' && (
                <>
                  <div className="text-center mb-6">
                    <h2 className="text-xl font-bold mb-2 text-white">You're on the list 🎶</h2>
                    <p className="text-gray-400 text-sm">
                      Add your email so the artist can call this out by name or follow up later.
                    </p>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1.5">Your Email (to personalize your request)</label>
                      <input
                        type="email"
                        placeholder="email@example.com"
                        value={followUpEmail}
                        onChange={(e) => {
                          setFollowUpEmail(e.target.value);
                          setFollowUpError(''); // Clear error on input change
                        }}
                        className={`w-full bg-gray-700 border rounded-lg px-4 py-3 text-white placeholder-gray-400 ${
                          followUpError ? 'border-red-500' : 'border-gray-600'
                        }`}
                        data-testid="followup-email-input"
                      />
                    </div>
                    {followUpError && (
                      <p className="text-red-400 text-sm" data-testid="followup-error">
                        {followUpError}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex flex-col space-y-3 mt-6">
                    <button
                      onClick={() => handleFollowUpComplete(true)}
                      className={`w-full py-3 rounded-lg font-bold transition duration-300 ${colors.button}`}
                      data-testid="followup-continue-btn"
                    >
                      Continue
                    </button>
                    <button
                      onClick={() => handleFollowUpComplete(false)}
                      className="w-full bg-gray-700 hover:bg-gray-600 py-3 rounded-lg text-gray-300 transition duration-300"
                      data-testid="followup-anonymous-btn"
                    >
                      Continue anonymously
                    </button>
                  </div>
                </>
              )}
              
              {/* Combined Success + Tip Screen */}
              {requestStep === 'success_tip' && (
                <>
                  {/* SUCCESS CONFIRMATION - Primary visual element */}
                  <div className="text-center mb-4">
                    <div className="w-14 h-14 bg-green-500/25 rounded-full mx-auto mb-3 flex items-center justify-center shadow-lg shadow-green-500/10">
                      <span className="text-green-400 text-2xl">✓</span>
                    </div>
                    <h2 className="text-xl font-bold mb-1 text-white">Request sent 🎶</h2>
                    <p className="text-gray-300 text-sm">Your song is in the queue</p>
                  </div>
                  
                  {/* TIP SECTION - Full tipping UI */}
                  {musician.tips_enabled !== false && (profileData ? profileData.show_tips_in_success_screen !== false : true) && (musician.venmo_username || musician.paypal_username || musician.cash_app_username || (musician.zelle_enabled && (musician.zelle_email || musician.zelle_phone))) && (
                    <div className="border-t border-gray-600/50 pt-4 mt-3">
                      <p className="text-gray-200 text-sm text-center mb-1">Want to leave a tip?</p>
                      <p className="text-gray-500 text-xs text-center mb-3">Totally optional.</p>
                      
                      {/* Amount input */}
                      <div className="mb-3">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-gray-500 text-sm">$</span>
                          <input
                            type="number"
                            placeholder="Amount"
                            value={tipAmount}
                            onChange={(e) => setTipAmount(e.target.value)}
                            min="0.01"
                            max="500"
                            step="0.01"
                            className="flex-1 bg-gray-700/50 border border-gray-600/50 rounded-lg px-3 py-2 text-white text-center text-sm"
                            data-testid="tip-amount-input"
                          />
                        </div>
                        {/* Quick amounts: $3, $5, $10 */}
                        <div className="flex justify-center gap-2">
                          {[3, 5, 10].map(amount => (
                            <button
                              key={amount}
                              type="button"
                              onClick={() => setTipAmount(amount.toString())}
                              className={`px-3 py-1 text-xs rounded-full transition duration-200 ${
                                tipAmount === amount.toString()
                                  ? 'bg-gray-600 text-gray-200'
                                  : 'bg-gray-700/50 text-gray-500 hover:text-gray-400'
                              }`}
                              data-testid={`quick-amount-${amount}`}
                            >
                              ${amount}
                            </button>
                          ))}
                        </div>
                      </div>
                      
                      {/* Payment selector */}
                      <div className="mb-3">
                        <select
                          value={tipPlatform}
                          onChange={(e) => setTipPlatform(e.target.value)}
                          className="w-full bg-gray-700/50 border border-gray-600/50 rounded-lg px-3 py-2 text-gray-300 text-sm"
                          data-testid="tip-payment-selector"
                        >
                          {musician?.venmo_enabled !== false && musician.venmo_username && (
                            <option value="venmo">Venmo</option>
                          )}
                          {musician?.paypal_enabled !== false && musician.paypal_username && (
                            <option value="paypal">PayPal</option>
                          )}
                          {musician?.cash_app_enabled !== false && musician.cash_app_username && (
                            <option value="cashapp">Cash App</option>
                          )}
                          {musician?.zelle_enabled && (musician.zelle_email || musician.zelle_phone) && (
                            <option value="zelle">Zelle</option>
                          )}
                        </select>
                      </div>
                      
                      {/* Send tip button */}
                      <button
                        onClick={handleSendTip}
                        disabled={!tipAmount || parseFloat(tipAmount) <= 0}
                        className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:text-gray-500 py-3 rounded-lg font-medium transition duration-300 disabled:cursor-not-allowed"
                        data-testid="success-tip-send-btn"
                      >
                        Send tip
                      </button>
                    </div>
                  )}
                  
                  {/* Skip button - always visible */}
                  <div className="mt-4 pt-3 border-t border-gray-700/30">
                    {(() => {
                      const tipSectionVisible = (
                        musician.tips_enabled !== false &&
                        (profileData ? profileData.show_tips_in_success_screen !== false : true) &&
                        (
                          musician.venmo_username ||
                          musician.paypal_username ||
                          musician.cash_app_username ||
                          (musician.zelle_enabled && (musician.zelle_email || musician.zelle_phone))
                        )
                      );
                      return (
                        <button
                          onClick={handleSkipTip}
                          className="w-full text-gray-400 hover:text-gray-300 py-2 text-sm transition duration-200"
                          data-testid="success-tip-skip-btn"
                        >
                          {tipSectionVisible ? "Skip / I'm all set" : 'Done'}
                        </button>
                      );
                    })()}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
        
        {/* NEW: Tip Choice Modal - Second Window */}
        {/* Removed old tip choice modal - now using integrated tip modal directly */}
        
        {/* NEW: Social Follow Modal - Third Window (No Tip Path) */}
        {showSocialFollowModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl p-6 w-full max-w-md border border-gray-700">
              {/* Header */}
              <div className="text-center mb-6">
                <div className="w-16 h-16 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl">
                  ❤️
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Even with no tip, a follow is just as good!</h3>
                <p className="text-gray-300 text-sm">Support {musician.name || 'the artist'} on their social platforms</p>
              </div>
              
              {/* Social Media Links */}
              <div className="space-y-3 mb-6">
                {musician.instagram_username && musician.instagram_username.trim() !== '' && (
                  <button
                    onClick={() => {
                      handleSocialClick('instagram');
                      closeTipFlow();
                    }}
                    className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">📷</span>
                    <span>Follow on Instagram</span>
                  </button>
                )}
                
                {musician.tiktok_username && musician.tiktok_username.trim() !== '' && (
                  <button
                    onClick={() => {
                      handleSocialClick('tiktok');
                      closeTipFlow();
                    }}
                    className="w-full bg-black hover:bg-gray-900 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🎵</span>
                    <span>Follow on TikTok</span>
                  </button>
                )}
                
                {musician.facebook_username && musician.facebook_username.trim() !== '' && (
                  <button
                    onClick={() => {
                      handleSocialClick('facebook');
                      closeTipFlow();
                    }}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">👥</span>
                    <span>Follow on Facebook</span>
                  </button>
                )}
                
                {musician.spotify_artist_url && musician.spotify_artist_url.trim() !== '' && (
                  <button
                    onClick={() => {
                      handleSocialClick('spotify');
                      closeTipFlow();
                    }}
                    className="w-full bg-green-500 hover:bg-green-600 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🎧</span>
                    <span>Listen on Spotify</span>
                  </button>
                )}
                
                {musician.apple_music_artist_url && musician.apple_music_artist_url.trim() !== '' && (
                  <button
                    onClick={() => {
                      handleSocialClick('apple_music');
                      closeTipFlow();
                    }}
                    className="w-full bg-red-500 hover:bg-red-600 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🍎</span>
                    <span>Listen on Apple Music</span>
                  </button>
                )}
              </div>
              
              {/* Close Button */}
              <button
                onClick={closeTipFlow}
                className="w-full bg-gray-600 hover:bg-gray-700 text-gray-300 hover:text-white py-3 rounded-xl font-medium transition duration-300"
              >
                Close
              </button>
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
                {musician.instagram_username && musician.instagram_username.trim() !== '' && (
                  <button
                    onClick={() => handleSocialClick('instagram')}
                    className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">📷</span>
                    <span>Follow on Instagram</span>
                  </button>
                )}
                
                {musician.tiktok_username && musician.tiktok_username.trim() !== '' && (
                  <button
                    onClick={() => handleSocialClick('tiktok')}
                    className="w-full bg-black hover:bg-gray-900 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🎵</span>
                    <span>Follow on TikTok</span>
                  </button>
                )}
                
                {musician.facebook_username && musician.facebook_username.trim() !== '' && (
                  <button
                    onClick={() => handleSocialClick('facebook')}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">👥</span>
                    <span>Follow on Facebook</span>
                  </button>
                )}
                
                {musician.spotify_artist_url && musician.spotify_artist_url.trim() !== '' && (
                  <button
                    onClick={() => handleSocialClick('spotify')}
                    className="w-full bg-green-500 hover:bg-green-600 text-white font-medium py-3 px-4 rounded-xl transition duration-300 flex items-center justify-center space-x-3"
                  >
                    <span className="text-xl">🎧</span>
                    <span>Listen on Spotify</span>
                  </button>
                )}
                
                {musician.apple_music_artist_url && musician.apple_music_artist_url.trim() !== '' && (
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
        
        {/* Orientation Side Path - Bottom Sheet */}
        {/* Entry: Artist header tap, Tip button tap */}
        {/* Exit: Close button, tap outside, swipe down */}
        {/* Per spec: Contains artist info + tip links, NO song lists */}
        {showOrientation && (
          <div 
            className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setShowOrientation(false);
                setBioExpanded(false); // Reset bio state on close
              }
            }}
            data-testid="orientation-overlay"
          >
            <div 
              className="bg-gray-800 rounded-t-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto animate-slide-up"
              style={{
                animation: 'slideUp 0.3s ease-out'
              }}
              data-testid="orientation-bottom-sheet"
            >
              {/* Drag Handle */}
              <div className="sticky top-0 bg-gray-800 pt-3 pb-2 rounded-t-2xl">
                <div className="w-12 h-1 bg-gray-600 rounded-full mx-auto mb-2"></div>
                
                {/* Post-request thanks line (only in post_request mode) */}
                {orientationMode === 'post_request' && (
                  <p className="text-center text-green-400 text-sm mb-2 px-4" data-testid="orientation-thanks-line">
                    Thanks, your request was sent.
                  </p>
                )}
                
                <div className="flex items-center justify-between px-4">
                  <div>
                    {musician?.current_show_name && (
                      <div className="flex items-center space-x-2 mb-0.5">
                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                        <span className="text-xs text-green-400 font-medium">Live Now: {musician.current_show_name}</span>
                      </div>
                    )}
                    <h2 className="text-lg font-bold text-white">
                      About the Artist
                    </h2>
                  </div>
                  <button
                    onClick={() => {
                      setShowOrientation(false);
                      setOrientationMode('default');
                      setTipSectionExpanded(false);
                      setBioExpanded(false);
                    }}
                    className="text-gray-400 hover:text-white p-2 rounded-full hover:bg-gray-700 transition"
                    data-testid="orientation-close-btn"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              
              {/* Orientation Content */}
              <div className="px-4 pb-6 space-y-5">
                
                {/* Artist Photo + Name */}
                <div className="text-center pt-2">
                  {designSettings.artist_photo ? (
                    <img
                      src={designSettings.artist_photo}
                      alt={designSettings.musician_name}
                      className="w-24 h-24 md:w-32 md:h-32 rounded-full object-cover mx-auto mb-3 border-2 border-gray-600"
                    />
                  ) : (
                    <div className="w-24 h-24 md:w-32 md:h-32 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 mx-auto mb-3 flex items-center justify-center text-3xl border-2 border-gray-600">
                      {designSettings.musician_name?.charAt(0) || '🎵'}
                    </div>
                  )}
                  <h1 className="text-xl md:text-2xl font-bold text-white">
                    {designSettings.musician_name}
                  </h1>
                </div>
                
                {/* Bio - expandable with smooth transition */}
                {designSettings.bio && (
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <div 
                      className="overflow-hidden transition-all duration-300 ease-in-out"
                      style={{ 
                        maxHeight: bioExpanded ? '1000px' : '120px'
                      }}
                    >
                      <p className="text-gray-300 text-sm leading-relaxed">
                        {bioExpanded 
                          ? designSettings.bio
                          : designSettings.bio.length > 300 
                            ? `${designSettings.bio.substring(0, 300).trim()}...`
                            : designSettings.bio
                        }
                      </p>
                    </div>
                    {designSettings.bio.length > 300 && (
                      <button
                        onClick={() => setBioExpanded(!bioExpanded)}
                        className="text-green-400 hover:text-green-300 text-xs mt-2 transition duration-200"
                        data-testid="bio-toggle-btn"
                      >
                        {bioExpanded ? 'Show less' : 'Read more'}
                      </button>
                    )}
                  </div>
                )}
                
                {/* Social Links (Follow) */}
                {musician && ((musician.instagram_username && musician.instagram_username.trim() !== '') || 
                  (musician.facebook_username && musician.facebook_username.trim() !== '') || 
                  (musician.tiktok_username && musician.tiktok_username.trim() !== '')) && (
                  <div>
                    <h3 className="text-base font-semibold text-white mb-3 flex items-center">
                      <span className="mr-2">📱</span>
                      Follow
                    </h3>
                    <div className="grid grid-cols-3 gap-2">
                      {musician.instagram_username && musician.instagram_username.trim() !== '' && (
                        <a
                          href={`https://instagram.com/${musician.instagram_username}`}
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 px-3 py-2 rounded-lg font-medium transition duration-300 flex items-center justify-center text-sm text-white"
                          data-testid="orientation-instagram-link"
                        >
                          Instagram
                        </a>
                      )}
                      {musician.facebook_username && musician.facebook_username.trim() !== '' && (
                        <a
                          href={musician.facebook_username.includes('facebook.com') ? 
                            (musician.facebook_username.startsWith('http') ? musician.facebook_username : `https://${musician.facebook_username}`) :
                            `https://facebook.com/${musician.facebook_username}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-lg font-medium transition duration-300 flex items-center justify-center text-sm text-white"
                          data-testid="orientation-facebook-link"
                        >
                          Facebook
                        </a>
                      )}
                      {musician.tiktok_username && musician.tiktok_username.trim() !== '' && (
                        <a
                          href={`https://tiktok.com/@${musician.tiktok_username}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-black hover:bg-gray-800 px-3 py-2 rounded-lg font-medium transition duration-300 flex items-center justify-center text-sm text-white border border-gray-600"
                          data-testid="orientation-tiktok-link"
                        >
                          TikTok
                        </a>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Streaming Links (Listen) */}
                {musician && ((musician.spotify_artist_url && musician.spotify_artist_url.trim() !== '') || 
                  (musician.apple_music_artist_url && musician.apple_music_artist_url.trim() !== '')) && (
                  <div>
                    <h3 className="text-base font-semibold text-white mb-3 flex items-center">
                      <span className="mr-2">🎧</span>
                      Listen
                    </h3>
                    <div className="grid grid-cols-2 gap-2">
                      {musician.spotify_artist_url && musician.spotify_artist_url.trim() !== '' && (
                        <a
                          href={musician.spotify_artist_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-green-600 hover:bg-green-700 px-3 py-2 rounded-lg font-medium transition duration-300 flex items-center justify-center text-sm text-white"
                          data-testid="orientation-spotify-link"
                        >
                          Spotify
                        </a>
                      )}
                      {musician.apple_music_artist_url && musician.apple_music_artist_url.trim() !== '' && (
                        <a
                          href={musician.apple_music_artist_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-gray-700 hover:bg-gray-600 px-3 py-2 rounded-lg font-medium transition duration-300 flex items-center justify-center text-sm text-white"
                          data-testid="orientation-apple-music-link"
                        >
                          Apple Music
                        </a>
                      )}
                    </div>
                  </div>
                )}
                
                {/* "Leave a tip" CTA button - shown in both default and post_request modes */}
                {musician?.tips_enabled !== false && (profileData ? profileData.show_tips_in_orientation !== false : true) && (musician.venmo_username || musician.paypal_username || musician.cash_app_username || (musician.zelle_enabled && (musician.zelle_email || musician.zelle_phone))) && (
                  <div ref={tipSectionRef} className="pt-3" data-testid="tip-section">
                    {!tipSectionExpanded ? (
                      /* Collapsed: Clear CTA button - Light green, distinct from Spotify green */
                      <button
                        onClick={handleToggleTipSection}
                        className="w-full bg-teal-500/90 hover:bg-teal-500 py-4 rounded-xl transition duration-300 text-center"
                        data-testid="orientation-leave-tip-btn"
                      >
                        <span className="text-white font-bold text-lg block">Leave a tip</span>
                        <span className="text-teal-100/80 text-sm block mt-0.5">(totally optional)</span>
                      </button>
                    ) : (
                      /* Expanded: Inline tip form */
                      <div className="bg-gray-700/40 rounded-xl p-4 border border-gray-600/30">
                        {/* Header */}
                        <div className="text-center mb-4">
                          <h3 className="text-base font-medium text-white">Leave a tip</h3>
                          <p className="text-gray-400 text-xs">(totally optional)</p>
                        </div>
                        
                        {/* Amount input */}
                        <div className="mb-4">
                          <div className="flex items-center gap-3 mb-3">
                            <span className="text-gray-400 text-sm">$</span>
                            <input
                              type="number"
                              placeholder="Amount"
                              value={tipAmount}
                              onChange={(e) => setTipAmount(e.target.value)}
                              min="0.01"
                              max="500"
                              step="0.01"
                              className="flex-1 bg-gray-700/50 border border-gray-600/50 rounded-lg px-4 py-3 text-white text-center"
                              data-testid="orientation-tip-amount-input"
                            />
                          </div>
                          <div className="flex justify-center gap-2">
                            {[3, 5, 10].map(amount => (
                              <button
                                key={amount}
                                type="button"
                                onClick={() => setTipAmount(amount.toString())}
                                className={`px-4 py-1.5 text-sm rounded-full transition duration-200 ${
                                  tipAmount === amount.toString()
                                    ? 'bg-emerald-600/50 text-emerald-200 border border-emerald-500/50'
                                    : 'bg-gray-700/50 text-gray-400 hover:text-gray-300 border border-gray-600/30'
                                }`}
                              >
                                ${amount}
                              </button>
                            ))}
                          </div>
                        </div>
                        
                        {/* Payment selector */}
                        <div className="mb-4">
                          <select
                            value={tipPlatform}
                            onChange={(e) => setTipPlatform(e.target.value)}
                            className="w-full bg-gray-700/50 border border-gray-600/50 rounded-lg px-4 py-3 text-gray-300"
                            data-testid="orientation-tip-payment-selector"
                          >
                            {musician?.venmo_enabled !== false && musician.venmo_username && (
                              <option value="venmo">Venmo</option>
                            )}
                            {musician?.paypal_enabled !== false && musician.paypal_username && (
                              <option value="paypal">PayPal</option>
                            )}
                            {musician?.cash_app_enabled !== false && musician.cash_app_username && (
                              <option value="cashapp">Cash App</option>
                            )}
                            {musician?.zelle_enabled && (musician.zelle_email || musician.zelle_phone) && (
                              <option value="zelle">Zelle</option>
                            )}
                          </select>
                        </div>
                        
                        {/* Dynamic CTA button */}
                        <button
                          onClick={() => {
                            if (tipAmount && parseFloat(tipAmount) > 0) {
                              triggerPaymentLink(parseFloat(tipAmount), tipPlatform);
                            }
                          }}
                          disabled={!tipAmount || parseFloat(tipAmount) <= 0}
                          className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 disabled:text-gray-500 py-3 rounded-xl font-medium transition duration-300 disabled:cursor-not-allowed"
                          data-testid="orientation-tip-send-btn"
                        >
                          {tipPlatform === 'venmo' ? 'Open Venmo' :
                           tipPlatform === 'paypal' ? 'Open PayPal' :
                           tipPlatform === 'cashapp' ? 'Open Cash App' :
                           tipPlatform === 'zelle' ? 'Show Zelle info' :
                           'Send tip'}
                        </button>
                        
                        {/* PayPal fallback link */}
                        {tipPlatform === 'paypal' && tipAmount && parseFloat(tipAmount) > 0 && (
                          <button
                            onClick={() => {
                              const url = getPayPalUrl(tipAmount);
                              if (url) {
                                console.log(`PayPal fallback URL: ${url}`);
                                window.location.assign(url);
                              }
                            }}
                            className="w-full text-gray-500 hover:text-gray-400 text-xs mt-2 underline"
                            data-testid="paypal-fallback-link"
                          >
                            Having trouble? Open in browser
                          </button>
                        )}
                        
                        {/* Collapse link */}
                        <button
                          onClick={handleToggleTipSection}
                          className="w-full text-gray-500 hover:text-gray-400 py-2 text-sm transition duration-200 mt-2"
                          data-testid="tip-collapse-btn"
                        >
                          Collapse
                        </button>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Website (default mode only) */}
                {orientationMode === 'default' && musician?.website && musician.website.trim() !== '' && (
                  <div>
                    <a
                      href={musician.website.startsWith('http') ? musician.website : `https://${musician.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full bg-gray-700 hover:bg-gray-600 px-4 py-3 rounded-lg font-medium transition duration-300 flex items-center justify-center space-x-2 text-white"
                      data-testid="orientation-website-link"
                    >
                      <span>🌐</span>
                      <span>Visit Website</span>
                    </a>
                  </div>
                )}
                
                {/* "Not you? Clear" - only show if there's saved identity */}
                {(localStorage.getItem('requestwave_requester_name') || localStorage.getItem('requestwave_requester_email')) && (
                  <div className="text-center pt-2">
                    <button
                      onClick={() => {
                        localStorage.removeItem('requestwave_requester_name');
                        localStorage.removeItem('requestwave_requester_email');
                        setRequestForm(prev => ({ ...prev, requester_name: '' }));
                        setShowOrientation(false);
                      }}
                      className="text-gray-500 hover:text-gray-400 text-xs underline transition"
                      data-testid="clear-identity-btn"
                    >
                      Not you? Clear saved info
                    </button>
                  </div>
                )}
                
                {/* Bottom padding for safe area */}
                <div className="h-4"></div>
              </div>
            </div>
          </div>
        )}
        
        {/* NEW: Zelle Instructions Modal */}
        {showZelleModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-white">🏦 Zelle Instructions</h3>
                <button
                  onClick={() => {
                    setShowZelleModal(false);
                    // Return to support mode if Orientation is open, otherwise return to song list
                    if (showOrientation && orientationMode === 'support') {
                      // Stay in support mode (Orientation is already open underneath)
                    } else if (tipSongId) {
                      setShowSocialMediaModal(true);
                    }
                  }}
                  className="text-gray-400 hover:text-white text-xl"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-4 text-white">
                <div className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-4">
                  <h4 className="font-bold mb-3">📱 How to send via Zelle:</h4>
                  <ol className="space-y-2 text-sm">
                    <li>1. Open your bank app or Zelle app</li>
                    <li>2. Select "Send Money" or "Send with Zelle"</li>
                    <li>3. Use the contact info below:</li>
                  </ol>
                </div>
                
                <div className="bg-gray-700 rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-300 text-sm">
                      {zelleInfo.contactType === 'email' ? 'Email:' : 'Phone:'}
                    </span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(zelleInfo.contact);
                        alert('Copied to clipboard!');
                      }}
                      className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-xs font-medium transition duration-300"
                    >
                      📋 Copy
                    </button>
                  </div>
                  <p className="font-mono text-green-300 text-lg">{zelleInfo.contact}</p>
                </div>
                
                <div className="bg-gray-700 rounded-lg p-4">
                  <p className="text-gray-300 text-sm mb-1">Amount:</p>
                  <p className="font-bold text-xl text-green-300">${zelleInfo.amount}</p>
                </div>
                
                <div className="bg-gray-700 rounded-lg p-4">
                  <p className="text-gray-300 text-sm mb-1">Message (optional):</p>
                  <p className="text-white">{zelleInfo.message}</p>
                </div>
                
                <button
                  onClick={() => {
                    setShowZelleModal(false);
                    // Return to support mode if Orientation is open, otherwise go to song list
                    if (showOrientation && orientationMode === 'support') {
                      // Stay in support mode (Orientation is already open underneath)
                    } else if (tipSongId) {
                      setShowSocialMediaModal(true);
                    }
                  }}
                  className="w-full bg-green-600 hover:bg-green-700 py-3 rounded-lg font-medium transition duration-300"
                >
                  Got it! 👍
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* NEW: Social Media Follow Modal */}
        {showSocialMediaModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-white">🎵 Follow {musician?.name}</h3>
                <button
                  onClick={() => setShowSocialMediaModal(false)}
                  className="text-gray-400 hover:text-white text-xl"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-3">
                <p className="text-gray-300 text-center mb-4">
                  Thank you for your request and tip! 🙏 Follow {musician?.name} on social media to stay connected:
                </p>
                
                {musician?.instagram_username && (
                  <a
                    href={`https://instagram.com/${musician.instagram_username}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center space-x-3 bg-pink-600 hover:bg-pink-700 py-3 px-4 rounded-lg font-medium transition duration-300"
                  >
                    <span>📸 Instagram</span>
                  </a>
                )}
                
                {musician?.facebook_username && (
                  <a
                    href={`https://facebook.com/${musician.facebook_username}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center space-x-3 bg-blue-600 hover:bg-blue-700 py-3 px-4 rounded-lg font-medium transition duration-300"
                  >
                    <span>👥 Facebook</span>
                  </a>
                )}
                
                {musician?.tiktok_username && (
                  <a
                    href={`https://tiktok.com/@${musician.tiktok_username}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center space-x-3 bg-black hover:bg-gray-900 py-3 px-4 rounded-lg font-medium transition duration-300 border border-gray-600"
                  >
                    <span>🎵 TikTok</span>
                  </a>
                )}
                
                {musician?.spotify_artist_url && (
                  <a
                    href={musician.spotify_artist_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center space-x-3 bg-green-600 hover:bg-green-700 py-3 px-4 rounded-lg font-medium transition duration-300"
                  >
                    <span>🎧 Spotify</span>
                  </a>
                )}
                
                {musician?.apple_music_artist_url && (
                  <a
                    href={musician.apple_music_artist_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center space-x-3 bg-gray-900 hover:bg-black py-3 px-4 rounded-lg font-medium transition duration-300 border border-gray-600"
                  >
                    <span>🍎 Apple Music</span>
                  </a>
                )}
                
                <button
                  onClick={() => {
                    setShowSocialMediaModal(false);
                    resetRequestForm(); // Reset form after complete flow
                  }}
                  className="w-full bg-purple-600 hover:bg-purple-700 py-3 rounded-lg font-medium transition duration-300 mt-4"
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

// Suggestion Card Component for On Stage Interface
const SuggestionCard = ({ item, index, onMatchToSong, onLearnLater, onSkip, songs }) => {
  const [showSongPicker, setShowSongPicker] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSongId, setSelectedSongId] = useState('');
  
  const filteredSongs = songs.filter(song => 
    song.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    song.artist.toLowerCase().includes(searchTerm.toLowerCase())
  ).slice(0, 10);
  
  return (
    <div className="bg-orange-900/30 rounded-lg p-4 border-l-4 border-orange-400">
      {/* Suggestion Label */}
      <div className="flex justify-between items-start mb-3">
        <span className="px-2 py-1 rounded-full text-xs font-bold bg-orange-600 text-white">
          SUGGESTION
        </span>
        <span className="text-gray-400 text-sm">
          {new Date(item.created_at).toLocaleTimeString()}
        </span>
      </div>
      
      {/* Song Info */}
      <div className="mb-4">
        <h3 className="font-bold text-xl mb-2 text-orange-100">
          {item.suggested_title || item.song_title}
        </h3>
        <p className="text-orange-200 text-base">
          by {item.suggested_artist || item.song_artist}
        </p>
      </div>
      
      {/* Requester Info */}
      <div className="mb-4">
        <div className="text-white text-lg font-bold mb-2">
          <span className="text-gray-300 font-semibold">From:</span> <span className="font-black text-yellow-300">{item.requester_name}</span>
        </div>
        {item.message && (
          <div className="text-orange-200 italic font-bold text-base">
            💌 "{item.message}"
          </div>
        )}
      </div>
      
      {/* Song Picker Modal */}
      {showSongPicker && (
        <div className="mb-4 p-3 bg-gray-800 rounded-lg">
          <input
            type="text"
            placeholder="Search your songs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full p-2 mb-2 rounded bg-gray-700 text-white"
            autoFocus
          />
          <div className="max-h-48 overflow-y-auto space-y-1">
            {filteredSongs.map(song => (
              <div
                key={song.id}
                onClick={() => setSelectedSongId(song.id)}
                className={`p-2 rounded cursor-pointer ${
                  selectedSongId === song.id ? 'bg-purple-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                <div className="font-bold text-sm">{song.title}</div>
                <div className="text-xs text-gray-400">{song.artist}</div>
              </div>
            ))}
          </div>
          <div className="flex space-x-2 mt-2">
            <button
              onClick={() => {
                if (selectedSongId) {
                  onMatchToSong(item.id, selectedSongId);
                  setShowSongPicker(false);
                }
              }}
              disabled={!selectedSongId}
              className="flex-1 bg-green-600 hover:bg-green-700 py-2 px-3 rounded font-bold disabled:opacity-50"
            >
              Confirm Match
            </button>
            <button
              onClick={() => setShowSongPicker(false)}
              className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 px-3 rounded font-bold"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      
      {/* Actions */}
      <div className="flex space-x-2">
        <button
          onClick={() => setShowSongPicker(true)}
          className="flex-1 bg-green-600 hover:bg-green-700 py-2 px-3 rounded-lg font-bold text-white text-sm"
        >
          Match to Song
        </button>
        <button
          onClick={() => onLearnLater(item.id)}
          className="flex-1 bg-blue-600 hover:bg-blue-700 py-2 px-3 rounded-lg font-bold text-white text-sm"
        >
          Learn it later
        </button>
        <button
          onClick={() => onSkip(item.id)}
          className="bg-red-600 hover:bg-red-700 py-2 px-3 rounded-lg font-bold text-white text-sm"
          title="Skip"
        >
          🗑️
        </button>
      </div>
    </div>
  );
};

// Shared Completed Item Component - Used by both Dashboard On Stage and Standalone On Stage
const CompletedRequestItem = ({ request, onRestore, compact = false }) => {
  const isSuggestion = request.type === 'suggestion';
  const isLearnLater = isSuggestion && request.status === 'learn_later';
  
  const getStatusLabel = () => {
    if (isLearnLater) return '📚 LEARN LATER';
    if (request.status === 'played') return '🎵 PLAYED';
    if (request.status === 'rejected') return '❌ SKIPPED';
    return request.status;
  };
  
  const getBgColor = () => {
    if (isLearnLater) return compact ? 'bg-blue-800/50' : 'bg-blue-900/30 border-l-4 border-blue-400';
    if (request.status === 'played') return compact ? 'bg-green-800/50' : 'bg-gray-700 border-l-4 border-gray-500 bg-gray-800/50';
    return compact ? 'bg-red-800/30' : 'bg-gray-700 border-l-4 border-gray-500 bg-gray-800/50';
  };
  
  return (
    <div className={`rounded-lg p-4 ${getBgColor()}`}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center space-x-2">
          {isSuggestion && (
            <span className="px-2 py-1 rounded-full text-xs font-bold bg-orange-600 text-white">
              SUGGESTION
            </span>
          )}
          <span className={`px-2 py-1 rounded-full text-xs font-bold ${
            compact
              ? (isLearnLater ? 'bg-blue-600 text-white' : request.status === 'played' ? 'bg-green-600 text-white' : 'bg-red-600 text-white')
              : 'bg-gray-600'
          }`}>
            {getStatusLabel()}
          </span>
          {!compact && (
            <span className="text-gray-400 text-sm">
              {new Date(request.created_at).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
      
      <div className="mb-4">
        <h4 className={`font-bold ${compact ? 'text-lg' : 'text-xl'} text-white mb-2`}>
          {request.song_title}
        </h4>
        <p className={`${compact ? 'text-base' : 'text-base'} ${
          request.status === 'played' 
            ? (compact ? 'text-green-200' : 'text-gray-300')
            : (compact ? 'text-red-200' : 'text-gray-300')
        }`}>
          by {request.song_artist}
        </p>
      </div>
      
      <div className="mb-4">
        <p className="text-sm text-gray-300">
          From: <strong className="text-white">{request.requester_name}</strong>
        </p>
        {request.dedication && (
          <p className={`text-sm mt-1 italic ${
            request.status === 'played'
              ? (compact ? 'text-green-200' : 'text-purple-200')
              : (compact ? 'text-red-200' : 'text-purple-200')
          }`}>
            💌 "{request.dedication}"
          </p>
        )}
      </div>
      
      {/* Restore Button */}
      <div className="flex space-x-2">
        <button
          onClick={() => onRestore(request.id)}
          className="flex-1 bg-yellow-600 hover:bg-yellow-700 active:bg-yellow-800 py-2 px-4 rounded-lg font-bold text-white transition duration-200"
        >
          Restore
        </button>
      </div>
    </div>
  );
};

// Request Card Component for On Stage Interface
const RequestCard = ({ item, index, onAccept, onPlay, onSkip, onRestore, showMoveButtons, isUpNext, isCompleted }) => {
  const isNewRequest = index === 0 && !isCompleted && !isUpNext;
  
  return (
    <div className={`bg-gray-700 rounded-lg p-4 border-l-4 transition-all duration-300 ${
      isUpNext ? 'border-blue-400 bg-blue-900/20' :
      isCompleted ? 'border-gray-500 bg-gray-800/50' :
      'border-purple-400'
    }`}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center space-x-2">
          <span className={`px-2 py-1 rounded-full text-xs font-bold ${
            isUpNext ? 'bg-blue-600' :
            isCompleted ? 'bg-gray-600' :
            'bg-purple-600'
          }`}>
            {isUpNext ? '⬆️ UP NEXT' : 
             isCompleted ? (item.status === 'played' ? '🎵 PLAYED' : '❌ SKIPPED') :
             '🎵 REQUEST'}
          </span>
          <span className="text-gray-400 text-sm">
            {formatTime(item.created_at)}
          </span>
        </div>
        {isNewRequest && (
          <span className="bg-red-600 text-white px-2 py-1 rounded-full text-xs font-bold animate-pulse">
            NEW
          </span>
        )}
      </div>
      
      {/* Song Info - LARGER FONTS */}
      <div className="mb-4">
        <h3 className={`font-bold mb-2 ${isUpNext || isCompleted ? 'text-xl' : 'text-2xl'}`}>
          {item.song_title || item.title}
        </h3>
        <p className={`text-gray-300 ${isUpNext || isCompleted ? 'text-base' : 'text-lg'}`}>
          by {item.song_artist || item.artist}
        </p>
      </div>
      
      {/* Requester Info - MUCH LARGER & BOLDER FONTS */}
      <div className="mb-4">
        <div className={`text-white mb-2 ${isUpNext || isCompleted ? 'text-lg font-bold' : 'text-2xl font-black'}`}>
          <span className="text-gray-300 font-semibold">From:</span> <span className="font-black text-yellow-300">{item.requester_name || 'Anonymous'}</span>
        </div>
        {item.dedication && (
          <div className={`text-purple-200 italic font-bold ${isUpNext || isCompleted ? 'text-base' : 'text-xl'}`}>
            💌 "{item.dedication}"
          </div>
        )}
        {/* Tip Amount Display */}
        {item.tip_amount && item.tip_amount > 0 && (
          <div className={`text-green-400 font-bold mt-2 ${isUpNext || isCompleted ? 'text-sm' : 'text-base'}`}>
            💰 ${item.tip_amount.toFixed(2)} tip included!
          </div>
        )}
      </div>
      
      {/* Action Buttons */}
      {showMoveButtons && (!item.status || item.status === 'pending') && (
        <div className="flex space-x-2">
          <button
            onClick={() => onAccept(item.id)}
            className="flex-1 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 py-3 px-4 rounded-lg font-bold text-white transition duration-200 touch-manipulation"
          >
            ⬆️ Add to Up Next
          </button>
          <button
            onClick={() => onPlay(item.id)}
            className="flex-1 bg-green-600 hover:bg-green-700 active:bg-green-800 py-3 px-4 rounded-lg font-bold text-white transition duration-200 touch-manipulation"
          >
            🎵 Play Now
          </button>
          <button
            onClick={() => onSkip(item.id)}
            className="flex-1 bg-red-600 hover:bg-red-700 active:bg-red-800 py-3 px-4 rounded-lg font-bold text-white transition duration-200 touch-manipulation"
          >
            ❌ Skip
          </button>
        </div>
      )}
      
      {/* Up Next Section Buttons */}
      {isUpNext && (
        <div className="flex space-x-2">
          <button
            onClick={() => onPlay(item.id)}
            className="flex-1 bg-green-600 hover:bg-green-700 active:bg-green-800 py-3 px-4 rounded-lg font-bold text-white transition duration-200 touch-manipulation"
          >
            🎵 Play Now
          </button>
          <button
            onClick={() => onSkip(item.id)}
            className="flex-1 bg-red-600 hover:bg-red-700 active:bg-red-800 py-3 px-4 rounded-lg font-bold text-white transition duration-200 touch-manipulation"
          >
            ❌ Remove
          </button>
        </div>
      )}
      
      {/* Completed Section - Restore Button */}
      {isCompleted && onRestore && (
        <div className="flex space-x-2">
          <button
            onClick={() => onRestore(item.id)}
            className="flex-1 bg-yellow-600 hover:bg-yellow-700 active:bg-yellow-800 py-3 px-4 rounded-lg font-bold text-white transition duration-200 touch-manipulation"
          >
            ↩️ Restore to Active
          </button>
        </div>
      )}
    </div>
  );
};

// NEW: On Stage Interface Component for Live Performances
const OnStageInterface = () => {
  const { slug } = useParams();
  const [musician, setMusician] = useState(null);
  const [requests, setRequests] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [songs, setSongs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newRequestCount, setNewRequestCount] = useState(0);
  const [lastUpdateTime, setLastUpdateTime] = useState(Date.now());
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [completedSectionCollapsed, setCompletedSectionCollapsed] = useState(false);
  const [errorToast, setErrorToast] = useState({ show: false, message: '' });
  
  // Helper function to show error toast
  const showErrorToast = (message, error = null) => {
    // Detect network/offline errors
    let displayMessage = message;
    if (error) {
      if (!navigator.onLine || error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
        displayMessage = 'You appear to be offline. Reconnect and try again.';
      }
    }
    setErrorToast({ show: true, message: displayMessage });
    setTimeout(() => setErrorToast({ show: false, message: '' }), 5000);
  };
  
  // Audio for notifications
  const notificationSound = useRef(null);
  
  useEffect(() => {
    // Create notification sound
    notificationSound.current = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmUgBSuK1/LBayUHLIHO8tiJOQgZZrnr65lEFAxOo+H0v2EcBSuK2Oy1YSMGGHfh9LZoFwcKSY7Z6GROC9OgUBCFQxWFdTyqp+3tPnxH3b/7PKXw95cZggHfyOvkxFkcCzhPztuuaB0JLHTP8seKRAgUX7jr1qRUEg5Kme7xvWEaBiB8x/a7YCUJKnvH7daXOQgZZrfh9bpmFgkEUY3O8dGINQcUYbLL5ZdBBgpKgdFyMWMTOxbT7tqIMw0YXrLl1qBRDQdHg9PjkCQFMXXP8s2LOAwOYaWw4qlaUg4LZq7G9s2OSQMNYazJ6JNEAxOp+T+mVlwb9Uu12ddPKq1DzuaOc8QYXbTu');
    
    // Start initialization
    fetchMusician();
    requestNotificationPermission();
  }, [slug]);
  
  useEffect(() => {
    // FIXED: Set up polling only after musician is loaded
    if (musician) {
      console.log('Starting On Stage polling for musician:', musician.name);
      
      // Initial fetch
      fetchUpdates();
      
      // Set up continuous polling
      const interval = setInterval(() => {
        console.log('On Stage polling tick...');
        fetchUpdates();
      }, 5000); // Poll every 5 seconds
      
      return () => {
        console.log('Stopping On Stage polling');
        clearInterval(interval);
      };
    }
  }, [musician]); // Depend on musician, not slug
  
  const fetchMusician = async () => {
    try {
      const response = await axios.get(`${API}/musicians/${slug}`);
      setMusician(response.data);
      setLoading(false); // Clear loading state once musician is fetched
      
      // Fetch songs for this musician
      const token = localStorage.getItem('token');
      const songsResponse = await axios.get(`${API}/songs`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        params: { musician_id: response.data.id }
      });
      setSongs(songsResponse.data || []);
    } catch (error) {
      console.error('Error fetching musician:', error);
      setLoading(false); // Clear loading state even on error
    }
  };
  
  const fetchUpdates = async () => {
    if (!musician) {
      console.log('No musician loaded yet, skipping update');
      return;
    }
    
    try {
      // FIXED: Use real API endpoint instead of demo data
      const response = await axios.get(`${API}/requests/updates/${musician.id}`);
      const data = response.data;
      
      console.log('On Stage update received:', data);
      
      // Fetch suggestions separately
      const token = localStorage.getItem('token');
      const suggestionsResponse = await axios.get(`${API}/song-suggestions`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      
      // Update requests with real data from backend
      if (data.requests) {
        // Keep existing request statuses if they were updated locally
        setRequests(prevRequests => {
          const updatedRequests = data.requests.map(apiRequest => {
            const existingReq = prevRequests.find(req => req.id === apiRequest.id);
            // Preserve local status changes, otherwise use API status
            return existingReq && existingReq.status !== apiRequest.status
              ? { ...apiRequest, status: existingReq.status }
              : apiRequest;
          });
          
          // Check for new requests and show notifications
          if (prevRequests.length > 0) {
            const newRequests = updatedRequests.filter(newReq => 
              !prevRequests.find(existingReq => existingReq.id === newReq.id)
            );
            
            if (newRequests.length > 0) {
              console.log('New requests detected:', newRequests);
              showNotification(newRequests);
              playNotificationSound();
            }
          }
          
          return updatedRequests;
        });
      }
      
      // Update suggestions - only pending and learn_later (not matched/rejected)
      if (suggestionsResponse.data) {
        const activeSuggestions = suggestionsResponse.data.filter(s => 
          s.status === 'pending' || s.status === 'learn_later'
        );
        setSuggestions(activeSuggestions);
      }
      
      setLoading(false);
      
    } catch (error) {
      console.error('Error fetching real-time updates:', error);
      
      // DON'T set loading to false on error - let polling continue
      // Only fall back to demo data if this is a complete API failure
      if (error.response?.status >= 500 || error.code === 'NETWORK_ERROR') {
        console.warn('Using demo data due to API failure');
        const demoRequests = [
          {
            id: 'demo-1',
            song_title: 'Wonderwall',
            song_artist: 'Oasis',
            requester_name: 'Demo User',
            dedication: 'Demo request - API unavailable',
            created_at: new Date().toISOString(),
            status: 'pending'
          }
        ];
        setRequests(demoRequests);
        setLoading(false);
      }
      // For other errors (like 404, 401), continue polling without updating data
    }
  };
  
  const requestNotificationPermission = async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission();
      setNotificationsEnabled(permission === 'granted');
    }
  };
  
  const showNotification = (newItems) => {
    if (!notificationsEnabled) return;
    
    const title = `🎵 New ${newItems.length > 1 ? 'Requests' : 'Request'}!`;
    const body = newItems.length === 1 
      ? `${newItems[0].song_title || newItems[0].title} - ${newItems[0].requester_name || 'Anonymous'}`
      : `${newItems.length} new requests received`;
    
    new Notification(title, {
      body,
      icon: 'https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png',
      badge: 'https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png',
      tag: 'new-request',
      requireInteraction: true
    });
  };
  
  const playNotificationSound = () => {
    if (notificationSound.current) {
      notificationSound.current.play().catch(() => {
        // Fallback: create a simple beep using Web Audio API
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
      });
    }
  };
  
  const clearNewCount = () => {
    setNewRequestCount(0);
  };
  
  // UNIFIED: On Stage request management (matching main dashboard pattern)
  const updateRequestStatus = async (requestId, status) => {
    // Validate status (archived handled by separate endpoint)
    const validStatuses = ['pending', 'up_next', 'accepted', 'played', 'rejected'];
    if (!validStatuses.includes(status)) {
      const errorMsg = `Invalid status "${status}". Use archiveRequest() for archiving.`;
      if (process.env.NODE_ENV === 'development') {
        console.error('[On Stage Status Update] Invalid status:', { requestId, status });
      }
      showErrorToast(errorMsg, error);
      return;
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        showErrorToast('Please log in again to update request status');
        return;
      }

      const payload = { status };
      if (process.env.NODE_ENV === 'development') {
        console.log('[On Stage Status Update] Request:', { requestId, status });
      }
      
      const response = await axios.put(
        `${API}/requests/${requestId}/status`, 
        payload,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[On Stage Status Update] Success:', { requestId, newStatus: response.data.new_status });
      }
      
      // Refetch to ensure consistency
      fetchUpdates();
      
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[On Stage Status Update] Error:', {
          requestId,
          status,
          error: error.response?.data || error.message,
          statusCode: error.response?.status
        });
      }
      
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message || 
                       `Failed to update request status to "${status}"`;
      showErrorToast(errorMsg, error);
    }
  };

  // UNIFIED: Archive request function (separate endpoint from status updates)
  const archiveRequest = async (requestId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        showErrorToast('Please log in again to archive request');
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.log('[On Stage Archive] Request:', requestId);
      }
      
      const response = await axios.put(
        `${API}/requests/${requestId}/archive`,
        {},
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[On Stage Archive] Success:', requestId);
      }
      
      // Refetch to ensure consistency
      fetchUpdates();
      
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[On Stage Archive] Error:', {
          requestId,
          error: error.response?.data || error.message,
          statusCode: error.response?.status
        });
      }
      
      const errorMsg = error.response?.data?.detail || 
                       error.response?.data?.message || 
                       'Failed to archive request';
      showErrorToast(errorMsg, error);
    }
  };
  
  // Request action handlers
  const handleAccept = (requestId) => updateRequestStatus(requestId, 'up_next');
  const handlePlay = (requestId) => updateRequestStatus(requestId, 'played');
  const handleSkip = (requestId) => updateRequestStatus(requestId, 'rejected');
  const handleRestore = (requestId) => updateRequestStatus(requestId, 'accepted');
  
  // Suggestion action handlers
  const handleMatchToSong = async (suggestionId, songId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API}/song-suggestions/${suggestionId}/match`,
        { song_id: songId },
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      fetchUpdates(); // Refresh to show new request
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to match suggestion';
      showErrorToast(errorMsg, error);
    }
  };
  
  const handleLearnLater = async (suggestionId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API}/song-suggestions/${suggestionId}/learn-later`,
        {},
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      fetchUpdates(); // Refresh to move to handled
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to mark as learn later';
      showErrorToast(errorMsg, error);
    }
  };
  
  const handleSkipSuggestion = async (suggestionId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API}/song-suggestions/${suggestionId}/status`,
        { status: 'rejected' },
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      fetchUpdates(); // Refresh to move to handled
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to skip suggestion';
      showErrorToast(errorMsg, error);
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }
  
  if (!musician) {
    // Demo mode for testing the new UI structure
    const demoMusician = { name: "Demo Artist", slug: "demo" };
    const demoRequests = [
      {
        id: 'demo-up-next-1',
        song_title: 'Sweet Child O Mine',
        song_artist: 'Guns N Roses',
        requester_name: 'Sarah M.',
        dedication: 'For my anniversary!',
        created_at: new Date(Date.now() - 300000).toISOString(), // 5 mins ago
        status: 'up_next',
        type: 'request'
      },
      {
        id: 'demo-up-next-2',
        song_title: 'Bohemian Rhapsody',
        song_artist: 'Queen',
        requester_name: 'Mike D.',
        dedication: '',
        created_at: new Date(Date.now() - 240000).toISOString(), // 4 mins ago
        status: 'up_next',
        type: 'request'
      },
      {
        id: 'demo-active-1',
        song_title: 'Wonderwall',
        song_artist: 'Oasis',
        requester_name: 'Emily R.',
        dedication: 'First dance song!',
        created_at: new Date(Date.now() - 120000).toISOString(), // 2 mins ago
        status: 'pending',
        type: 'request'
      },
      {
        id: 'demo-active-2',
        song_title: 'Hotel California',
        song_artist: 'Eagles',
        requester_name: 'John K.',
        dedication: '',
        created_at: new Date(Date.now() - 60000).toISOString(), // 1 min ago
        status: 'pending',
        type: 'request'
      },
      {
        id: 'demo-completed-1',
        song_title: 'Stairway to Heaven',
        song_artist: 'Led Zeppelin',
        requester_name: 'Lisa P.',
        dedication: 'Amazing performance!',
        created_at: new Date(Date.now() - 600000).toISOString(), // 10 mins ago
        status: 'played',
        type: 'request'
      },
      {
        id: 'demo-completed-2',
        song_title: 'Freebird',
        song_artist: 'Lynyrd Skynyrd',
        requester_name: 'Tom S.',
        dedication: '',
        created_at: new Date(Date.now() - 900000).toISOString(), // 15 mins ago
        status: 'rejected',
        type: 'request'
      }
    ];
    
    // Override the state for demo
    musician = demoMusician;
    requests = demoRequests;
  }
  
  // Organize requests into sections
  // Organize requests into sections
  
  if (!musician) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Demo Mode - Testing On Stage Interface</h1>
          <p>This shows the new three-section layout with demo data</p>
        </div>
      </div>
    );
  }
  
  const upNextRequests = requests.filter(r => r.status === 'up_next')
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at)); // oldest first
  
  // Merge active requests with pending suggestions, sorted by created_at (oldest first)
  const activeRequestsAndSuggestions = [
    ...requests.filter(r => !r.status || r.status === 'pending').map(r => ({ ...r, type: 'request' })),
    ...suggestions.filter(s => s.status === 'pending').map(s => ({ 
      ...s, 
      type: 'suggestion',
      song_title: s.suggested_title,
      song_artist: s.suggested_artist,
      dedication: s.message
    }))
  ].sort((a, b) => new Date(a.created_at) - new Date(b.created_at)); // oldest first
  
  // Backwards compatibility - keep activeRequests for other code
  const activeRequests = activeRequestsAndSuggestions;
    
  const completedRequests = [
    ...requests.filter(r => r.status === 'played' || r.status === 'rejected').map(r => ({ ...r, type: 'request' })),
    ...suggestions.filter(s => s.status === 'learn_later' || s.status === 'rejected').map(s => ({ 
      ...s, 
      type: 'suggestion',
      song_title: s.suggested_title,
      song_artist: s.suggested_artist,
      dedication: s.message
    }))
  ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)); // newest first
  
  const allItems = [
    ...requests.map(r => ({ ...r, type: 'request' })),
    ...suggestions.map(s => ({ ...s, type: 'suggestion' }))
  ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      {/* Error Toast */}
      {errorToast.show && (
        <div className="fixed top-4 right-4 z-50 animate-fade-in">
          <div className="bg-red-600 text-white px-6 py-4 rounded-lg shadow-lg max-w-md">
            <div className="flex items-start">
              <span className="text-xl mr-3">⚠️</span>
              <div className="flex-1">
                <p className="font-medium">Error</p>
                <p className="text-sm mt-1">{errorToast.message}</p>
              </div>
              <button
                onClick={() => setErrorToast({ show: false, message: '' })}
                className="ml-4 text-white hover:text-gray-200"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Header */}
      <div className="bg-gray-800 rounded-xl p-4 mb-6 sticky top-4 z-10">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <img
              src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png"
              alt="RequestWave"
              className="w-8 h-8 object-contain"
            />
            <div>
              <h1 className="text-xl font-bold">🎤 On Stage</h1>
              <p className="text-gray-400 text-sm">{musician.name}</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {/* Request Toggle Switch */}
            <div className="flex items-center space-x-2">
              <span className="text-gray-300 text-sm">Requests:</span>
              <div className="relative inline-block w-8 align-middle select-none">
                <input
                  type="checkbox"
                  id="requests_enabled_toggle"
                  checked={musician.requests_enabled !== false}
                  onChange={async (e) => {
                    const newValue = e.target.checked;
                    try {
                      // Update profile in real-time
                      await axios.put(`${API}/profile`, {
                        requests_enabled: newValue
                      });
                      
                      // Update local musician state
                      setMusician(prev => ({...prev, requests_enabled: newValue}));
                      
                      console.log('Request toggle updated:', newValue);
                    } catch (error) {
                      console.error('Error updating request toggle:', error);
                      // Revert the toggle if update failed
                      e.target.checked = !newValue;
                    }
                  }}
                  className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-2 appearance-none cursor-pointer transition-transform duration-200 transform"
                  style={{
                    left: (musician.requests_enabled !== false) ? '12px' : '0px',
                    backgroundColor: '#ffffff'
                  }}
                />
                <label
                  htmlFor="requests_enabled_toggle"
                  className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer transition-colors duration-200 ${
                    (musician.requests_enabled !== false) ? 'bg-green-500' : 'bg-red-500'
                  }`}
                ></label>
              </div>
              <span className={`text-xs font-bold ${(musician.requests_enabled !== false) ? 'text-green-400' : 'text-red-400'}`}>
                {(musician.requests_enabled !== false) ? 'ON' : 'OFF'}
              </span>
            </div>
            
            {/* Notification Indicator */}
            <div className={`w-3 h-3 rounded-full ${notificationsEnabled ? 'bg-green-500' : 'bg-red-500'}`}></div>
          </div>
        </div>
      </div>
      
      {/* Live Requests - Three Section Layout */}
      <div className="space-y-6">
        
        {/* UP NEXT Section */}
        {upNextRequests.length > 0 && (
          <div className="bg-gradient-to-r from-blue-900 to-purple-900 rounded-xl p-4 border-2 border-blue-500">
            <div className="flex items-center space-x-2 mb-4">
              <span className="text-2xl">⬆️</span>
              <h2 className="text-xl font-bold text-blue-200">Up Next ({upNextRequests.length})</h2>
            </div>
            <div className="space-y-3">
              {upNextRequests.map((item, index) => (
                <RequestCard 
                  key={item.id} 
                  item={item} 
                  index={index}
                  onPlay={handlePlay}
                  onSkip={handleSkip}
                  showMoveButtons={false}
                  isUpNext={true}
                />
              ))}
            </div>
          </div>
        )}

        {/* ACTIVE REQUESTS Section */}
        <div className="bg-gray-800 rounded-xl p-4 border-2 border-purple-500">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">🎵</span>
              <h2 className="text-xl font-bold text-purple-200">Active Requests ({activeRequests.length})</h2>
            </div>
            {newRequestCount > 0 && (
              <div 
                onClick={clearNewCount}
                className="bg-red-600 text-white px-3 py-1 rounded-full text-sm font-bold animate-pulse cursor-pointer"
              >
                +{newRequestCount} New!
              </div>
            )}
          </div>
          
          {activeRequests.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-6xl mb-4">🎵</div>
              <h3 className="text-lg font-bold mb-2 text-gray-300">No active requests</h3>
              <p className="text-gray-400">New requests will appear here in real-time</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeRequests.map((item, index) => (
                item.type === 'suggestion' ? (
                  <SuggestionCard
                    key={item.id}
                    item={item}
                    index={index}
                    onMatchToSong={handleMatchToSong}
                    onLearnLater={handleLearnLater}
                    onSkip={handleSkipSuggestion}
                    songs={songs}
                  />
                ) : (
                  <RequestCard 
                    key={item.id} 
                    item={item} 
                    index={index}
                    onAccept={handleAccept}
                    onPlay={handlePlay}
                    onSkip={handleSkip}
                    showMoveButtons={true}
                    isUpNext={false}
                  />
                )
              ))}
            </div>
          )}
        </div>

        {/* HANDLED REQUESTS Section */}
        {completedRequests.length > 0 && (
          <div className="bg-gray-800 rounded-xl border-2 border-gray-600">
            <div 
              className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-700 transition-colors rounded-t-xl"
              onClick={() => setCompletedSectionCollapsed(!completedSectionCollapsed)}
            >
              <div className="flex items-center space-x-2">
                <span className="text-2xl">✅</span>
                <div>
                  <h2 className="text-xl font-bold text-gray-300">Handled ({completedRequests.length})</h2>
                  <p className="text-sm text-gray-400">Played, skipped, or saved for later.</p>
                </div>
              </div>
              <span className={`text-xl transition-transform ${completedSectionCollapsed ? 'rotate-90' : 'rotate-0'}`}>
                ▶️
              </span>
            </div>
            
            {!completedSectionCollapsed && (
              <div className="p-4 pt-0 space-y-3 max-h-96 overflow-y-auto">
                {completedRequests.map((item, index) => (
                  <CompletedRequestItem
                    key={item.id}
                    request={item}
                    onRestore={(requestId) => {
                      updateRequestStatus(requestId, 'accepted');
                    }}
                    compact={false}
                  />
                ))}
              </div>
            )}
          </div>
        )}
        
      </div>
      
      {/* Footer */}
      <div className="mt-8 text-center text-gray-500 text-sm">
        <p>Updates automatically • Keep this tab open during your performance</p>
        {!notificationsEnabled && (
          <button 
            onClick={requestNotificationPermission}
            className="mt-2 text-purple-400 hover:text-purple-300 underline"
          >
            Enable notifications for background alerts
          </button>
        )}
      </div>
    </div>
  );
};

const LandingPage = () => {
  const [authMode, setAuthMode] = useState('login');
  const [showSupport, setShowSupport] = useState(false);
  const [supportAmount, setSupportAmount] = useState('24');

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header with Logo */}
        <div className="text-center mb-8">
          <img
            src="https://customer-assets.emergentagent.com/job_bandbridge/artifacts/x5k3yeey_RequestWave%20Logo.png"
            alt="RequestWave Logo"
            className="w-32 h-32 mx-auto mb-4 object-contain"
          />
          <h1 className="text-4xl lg:text-5xl font-bold mb-2">
            <span className="text-purple-400">Request</span><span className="text-green-400">Wave</span>
          </h1>
          <p className="text-xl text-purple-200">Connect with your audience through music</p>
        </div>

        {/* Sign In Form - Now at the top */}
        <div className="max-w-md mx-auto mb-12">
          <AuthForm mode={authMode} onSwitch={setAuthMode} />
        </div>

        {/* Story and Information - Now below the login form */}
        <div className="max-w-4xl mx-auto space-y-8">

            {/* Bryce's Photo and Story */}
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl">
              <div className="flex flex-col md:flex-row items-start space-y-4 md:space-y-0 md:space-x-6 mb-6">
                <img
                  src="https://customer-assets.emergentagent.com/job_requestwave-2/artifacts/oxuafhes_Bryce%20ASL%202.png"
                  alt="Bryce Larsen"
                  className="w-32 h-32 rounded-full object-cover mx-auto md:mx-0 flex-shrink-0"
                />
                <div>
                  <h2 className="text-2xl font-bold text-white mb-4">Welcome to RequestWave</h2>
                  <p className="text-purple-200 leading-relaxed">
                    My name is <strong className="text-white">Bryce Larsen</strong>. I am a lifelong musician, performer, and educator who has spent years on stage fronting original and cover bands, looping solo acoustic sets, and teaching music in schools. At my shows, I have always looked for ways to connect the audience more directly with the music.
                  </p>
                </div>
              </div>
              
              <div className="space-y-4 text-purple-200 leading-relaxed">
                <p>
                  For years, I relied on Google Forms as a simple audience request system. The concept was strong, but the execution was tedious and awkward for both me and my audiences. It was clear the idea had potential, but the tools weren't built for live performance.
                </p>
                
                <p>
                  That is why I created <strong className="text-white">RequestWave</strong>. This app takes the same idea and finally makes it easy, fast, and enjoyable. It has already improved my own live shows, and I am excited to make it available to other performing musicians who want to give their audiences a voice.
                </p>
              </div>
            </div>

            {/* About the Subscription */}
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl">
              <h3 className="text-2xl font-bold text-white mb-4">About the Subscription</h3>
              <p className="text-purple-200 mb-4">RequestWave will eventually run on a small subscription model:</p>
              <ul className="list-disc list-inside text-purple-200 space-y-2 mb-4">
                <li><strong className="text-white">$15</strong> startup fee</li>
                <li><strong className="text-white">$4</strong> per month if paid annually</li>
                <li><strong className="text-white">$10</strong> per month if paid monthly</li>
              </ul>
              <p className="text-purple-200">
                For now, my focus has been on making the app as functional and reliable as possible. Subscription coding will come later, but the priority today is giving musicians a tool that works.
              </p>
            </div>

            {/* Supporting the Project */}
            <div className="bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl">
              <h3 className="text-2xl font-bold text-white mb-4">Supporting the Project</h3>
              <p className="text-purple-200 mb-4">
                Building and hosting this app comes with ongoing costs. If you would like to support its development, you can Venmo me at <strong className="text-green-400">@adventuresound</strong>. As a thank you, any donation will be credited at twice its value once subscriptions go live. For example, a $25 donation today will receive a coupon for a full year subscription (a $48 value).
              </p>
              
              <button
                onClick={() => setShowSupport(true)}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-bold py-3 rounded-lg transition duration-300 flex items-center justify-center space-x-2 mb-4"
              >
                <span>💰</span>
                <span>Support RequestWave</span>
              </button>
              
              <p className="text-purple-200 text-sm">
                Thank you for being part of this project. My goal is to make live performance more interactive and enjoyable for both musicians and audiences, and your support helps make that possible.
              </p>
            </div>
        </div>
      </div>

      {/* Support Modal */}
      {showSupport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-800 rounded-xl p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold text-white text-center mb-6">
              Support RequestWave
            </h2>
            
            <p className="text-gray-300 text-center mb-6">
              Choose your support amount. Your contribution will be credited at 2x value when subscriptions launch!
            </p>
            
            {/* Amount Selection */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              {['24', '48', '96'].map((amount) => (
                <button
                  key={amount}
                  onClick={() => setSupportAmount(amount)}
                  className={`p-4 rounded-lg border-2 transition duration-300 ${
                    supportAmount === amount
                      ? 'border-green-500 bg-green-900/30'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">${amount}</div>
                    <div className="text-sm text-gray-400">
                      ${parseInt(amount) * 2} credit
                    </div>
                  </div>
                </button>
              ))}
              
              <div className="col-span-2">
                <input
                  type="number"
                  placeholder="Other amount"
                  value={supportAmount !== '24' && supportAmount !== '48' && supportAmount !== '96' ? supportAmount : ''}
                  onChange={(e) => setSupportAmount(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                />
              </div>
            </div>
            
            {/* Payment Options */}
            <div className="space-y-3 mb-6">
              <button
                onClick={() => {
                  window.open(`https://venmo.com/adventuresound?txn=pay&amount=${supportAmount}&note=RequestWave Support`, '_blank');
                }}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition duration-300 flex items-center justify-center space-x-2"
              >
                <span>📱</span>
                <span>Venmo (@adventuresound)</span>
              </button>
              
              <button
                onClick={() => {
                  window.open(`https://www.paypal.me/brycelarsenmusic/${supportAmount}`, '_blank');
                }}
                className="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-bold py-3 rounded-lg transition duration-300 flex items-center justify-center space-x-2"
              >
                <span>💳</span>
                <span>PayPal (brycelarsenmusic)</span>
              </button>
              
              <div className="bg-gray-700 rounded-lg p-3 text-center">
                <p className="text-gray-300 text-sm mb-1">Zelle:</p>
                <p className="text-white font-medium">brycelarsenmusic@gmail.com</p>
                <p className="text-white font-medium">(516) 680-0672</p>
              </div>
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={() => setShowSupport(false)}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white py-3 rounded-lg transition duration-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
        
    </div>
  );
};

// Short URL Redirect component - handles catch-all routes for vanity URLs
const ShortUrlRedirect = () => {
  const { seg1, seg2, seg3 } = useParams();
  const navigate = useNavigate();
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const resolveSlug = async () => {
      try {
        await axios.get(`${API}/resolve/${seg1}`);
        // Slug found - redirect to the proper musician URL
        if (seg3) {
          navigate(`/musician/${seg1}/${seg2}/${seg3}`, { replace: true });
        } else if (seg2) {
          navigate(`/musician/${seg1}/${seg2}`, { replace: true });
        } else {
          navigate(`/musician/${seg1}`, { replace: true });
        }
      } catch {
        setNotFound(true);
      }
    };
    resolveSlug();
  }, [seg1, seg2, seg3, navigate]);

  if (notFound) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">404</h1>
          <p className="text-gray-400 mb-4">Page not found</p>
          <a href="/" className="text-purple-400 hover:text-purple-300 underline">Go Home</a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">
      <p className="text-gray-400">Loading...</p>
    </div>
  );
};

const App = () => {
  const { musician, login } = useAuth();

  // NEW: Check for Emergent OAuth session on app load
  useEffect(() => {
    const checkEmergentSession = async () => {
      // Check for session_id in URL fragment
      const fragment = window.location.hash.substring(1);
      const params = new URLSearchParams(fragment);
      const sessionId = params.get('session_id');
      
      if (sessionId && !musician) {
        console.log('Found Emergent session ID, authenticating...', sessionId);
        
        // Log OAuth attempt (non-PII telemetry)
        console.log('oauth_authentication_attempt', {
          environment: process.env.NODE_ENV || 'development',
          user_agent: navigator.userAgent,
          referrer: document.referrer,
          timestamp: new Date().toISOString()
        });
        
        try {
          // Call backend to authenticate with Emergent session
          const response = await axios.post(`${API}/auth/emergent-oauth`, {}, {
            headers: {
              'X-Session-ID': sessionId
            }
          });
          
          if (response.data.success) {
            // Login with returned data
            login(response.data);
            
            // Clear the fragment from URL
            window.location.hash = '';
            
            // Log OAuth success (non-PII telemetry)
            console.log('oauth_success', {
              environment: process.env.NODE_ENV || 'development',
              user_agent: navigator.userAgent,
              timestamp: new Date().toISOString()
            });
            
            console.log('Emergent OAuth authentication successful');
          }
        } catch (error) {
          console.error('Emergent OAuth authentication failed:', error);
          
          // Log OAuth error (non-PII telemetry)
          console.log('oauth_error', {
            environment: process.env.NODE_ENV || 'development',
            user_agent: navigator.userAgent,
            error_type: error.response?.status || 'network_error',
            timestamp: new Date().toISOString()
          });
          
          alert('Authentication failed. Please try logging in again.');
        }
      }
    };
    
    // Only check on initial load or when musician is null
    // Skip authentication check for audience interface routes
    const isAudienceRoute = window.location.pathname.startsWith('/musician/') || 
                           window.location.pathname.startsWith('/on-stage/');
    
    if (!musician && !isAudienceRoute) {
      checkEmergentSession();
    }
  }, [musician, login]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={musician ? <Navigate to="/dashboard" /> : <LandingPage />} />
        <Route path="/rw-ops" element={<AdminPanel />} />
        <Route path="/dashboard" element={musician ? <MusicianDashboard /> : <Navigate to="/" />} />
        <Route path="/musician/:masterSlug/:profileSlug/:eventSlug" element={<AudienceInterface />} />
        <Route path="/musician/:masterSlug/:profileSlug" element={<AudienceInterface />} />
        <Route path="/musician/:slug" element={<AudienceInterface />} />
        <Route path="/on-stage/:slug" element={<OnStageInterface />} />
        <Route path="/:seg1/:seg2/:seg3" element={<ShortUrlRedirect />} />
        <Route path="/:seg1/:seg2" element={<ShortUrlRedirect />} />
        <Route path="/:seg1" element={<ShortUrlRedirect />} />
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
