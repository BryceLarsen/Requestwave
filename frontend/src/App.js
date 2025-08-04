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
    <AuthContext.Provider value={{ musician, token, login, logout }}>
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
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">RequestWave</h1>
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
  const { musician, token, logout } = useAuth();
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
  const [songError, setSongError] = useState('');

  // Profile management state
  const [showProfile, setShowProfile] = useState(false);
  const [profile, setProfile] = useState({
    name: '',
    email: '',
    venmo_link: '',
    bio: '',
    website: ''
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

  useEffect(() => {
    fetchSongs();
    fetchRequests();
    fetchSubscriptionStatus();
    
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

  useEffect(() => {
    if (activeTab === 'design') {
      fetchDesignSettings();
    }
  }, [activeTab]);

  const fetchSongs = async () => {
    try {
      const response = await axios.get(`${API}/songs`);
      setSongs(response.data);
    } catch (error) {
      console.error('Error fetching songs:', error);
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
        await axios.delete(`${API}/songs/${songId}`);
        fetchSongs();
      } catch (error) {
        console.error('Error deleting song:', error);
        if (error.response?.status === 401) {
          // Token expired or invalid, redirect to login
          logout();
        }
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
        const url = new URL(window.location);
        url.searchParams.delete('session_id');
        url.searchParams.delete('payment');
        window.history.replaceState({}, document.title, url.pathname + url.search);
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
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
      alert(response.data.message);
      setPlaylistUrl('');
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
      
      const response = await axios.post(`${API}/songs/csv/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Reset form and refresh songs
      setCsvFile(null);
      setCsvPreview(null);
      setShowCsvUpload(false);
      fetchSongs();
      
      alert(`Success! ${response.data.songs_added} songs imported${response.data.errors.length > 0 ? ' with some warnings' : ''}`);
      
    } catch (error) {
      setCsvError(error.response?.data?.detail || 'Error uploading CSV file');
    } finally {
      setCsvUploading(false);
    }
  };

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
            <h1 className="text-2xl font-bold text-purple-400">RequestWave</h1>
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
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 bg-gray-800 rounded-lg p-1 mb-8">
          {['songs', 'requests', 'profile', 'design'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition duration-300 ${
                activeTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
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
              <button
                onClick={() => setShowCsvUpload(!showCsvUpload)}
                className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-bold transition duration-300"
              >
                {showCsvUpload ? 'Hide CSV Upload' : 'Upload CSV'}
              </button>
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
            <div className="bg-gray-800 rounded-xl p-6 mb-8">
              <h3 className="text-lg font-bold mb-4">Import from Music Playlist</h3>
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

            {/* Add Song Form */}
            <div className="bg-gray-800 rounded-xl p-6 mb-8">
              <h2 className="text-xl font-bold mb-4">
                {editingSong ? 'Edit Song' : 'Add New Song'}
              </h2>
              
              {songError && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 text-red-200">
                  {songError}
                </div>
              )}
              
              <form onSubmit={editingSong ? handleUpdateSong : handleAddSong} className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    {editingSong ? 'Update Song' : 'Add Song'}
                  </button>
                  {editingSong && (
                    <button
                      type="button"
                      onClick={cancelEdit}
                      className="flex-1 bg-gray-600 hover:bg-gray-700 py-2 rounded-lg font-bold transition duration-300"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            </div>

            {/* Songs List */}
            <div className="bg-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-bold mb-4">Your Songs ({songs.length})</h2>
              <div className="space-y-4">
                {songs.map((song) => (
                  <div key={song.id} className="bg-gray-700 rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-bold text-lg">{song.title}</h3>
                        <p className="text-gray-300">by {song.artist}</p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {song.genres.map((genre, idx) => (
                            <span key={idx} className="bg-blue-600 text-xs px-2 py-1 rounded">{genre}</span>
                          ))}
                          {song.moods.map((mood, idx) => (
                            <span key={idx} className="bg-green-600 text-xs px-2 py-1 rounded">{mood}</span>
                          ))}
                          {song.year && <span className="bg-gray-600 text-xs px-2 py-1 rounded">{song.year}</span>}
                        </div>
                        {song.notes && (
                          <p className="text-gray-400 text-sm mt-2 italic">"{song.notes}"</p>
                        )}
                      </div>
                      <div className="flex space-x-2 ml-4">
                        <button
                          onClick={() => handleEditSong(song)}
                          className="bg-blue-600 hover:bg-blue-700 text-xs px-3 py-1 rounded transition duration-300"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteSong(song.id)}
                          className="bg-red-600 hover:bg-red-700 text-xs px-3 py-1 rounded transition duration-300"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {songs.length === 0 && (
                  <p className="text-gray-400 text-center py-8">No songs added yet. Add your first song above!</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Requests Tab */}
        {activeTab === 'requests' && (
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-xl font-bold mb-4">Song Requests ({requests.length})</h2>
            <div className="space-y-4">
              {requests.map((request) => (
                <div key={request.id} className="bg-gray-700 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg">{request.song_title}</h3>
                      <p className="text-gray-300">by {request.song_artist}</p>
                      <p className="text-purple-300 mt-2">Requested by: {request.requester_name}</p>
                      {request.dedication && (
                        <p className="text-gray-400 italic mt-1">"{request.dedication}"</p>
                      )}
                      {request.tip_amount > 0 && (
                        <p className="text-green-400 font-bold mt-1">Tip: ${request.tip_amount}</p>
                      )}
                    </div>
                    <div className="flex flex-col space-y-2 ml-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        request.status === 'pending' ? 'bg-yellow-600' :
                        request.status === 'accepted' ? 'bg-blue-600' :
                        request.status === 'played' ? 'bg-green-600' :
                        'bg-red-600'
                      }`}>
                        {request.status.toUpperCase()}
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
                    </div>
                  </div>
                </div>
              ))}
              {requests.length === 0 && (
                <p className="text-gray-400 text-center py-8">No requests yet. Share your audience link to start receiving requests!</p>
              )}
            </div>
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
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
              
              <div>
                <label className="block text-gray-300 text-sm font-bold mb-2">Venmo Link (for tips)</label>
                <input
                  type="text"
                  placeholder="@yourusername or venmo.com/yourusername"
                  value={profile.venmo_link}
                  onChange={(e) => setProfile({...profile, venmo_link: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400"
                />
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
              
              <button
                type="submit"
                className="w-full bg-purple-600 hover:bg-purple-700 py-2 rounded-lg font-bold transition duration-300"
              >
                Update Profile
              </button>
            </form>
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
                <label className="block text-gray-300 text-sm font-bold mb-3">Artist Photo</label>
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
                      className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg cursor-pointer transition duration-300"
                    >
                      Upload Photo
                    </label>
                    <p className="text-xs text-gray-400 mt-1">Max 2MB, JPG/PNG</p>
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
    year: ''
  });
  const [requestForm, setRequestForm] = useState({
    requester_name: '',
    requester_email: '',
    dedication: '',
    tip_amount: 0
  });
  const [selectedSong, setSelectedSong] = useState(null);
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState('');
  const [showFilters, setShowFilters] = useState(false);

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
    applyFilters();
  }, [songs, selectedFilters]);

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
      const response = await axios.get(`${API}/musicians/${slug}/songs`);
      setSongs(response.data);
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

    setFilteredSongs(filtered);
  };

  const handleRequest = async (song) => {
    if (!requestForm.requester_name || !requestForm.requester_email) {
      alert('Please enter your name and email');
      return;
    }

    try {
      await axios.post(`${API}/requests`, {
        song_id: song.id,
        ...requestForm,
        tip_amount: parseFloat(requestForm.tip_amount) || 0
      });
      
      setSuccess('Request sent successfully!');
      setSelectedSong(null);
      setRequestForm({
        requester_name: '',
        requester_email: '',
        dedication: '',
        tip_amount: 0
      });
      
      setTimeout(() => setSuccess(''), 3000);
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
      year: ''
    });
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
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`md:hidden ${colors.primary} px-4 py-2 rounded-lg font-medium transition duration-300`}
            >
              Filters
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-4 md:py-8">
        {success && (
          <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-3 md:p-4 mb-4 md:mb-6 text-green-200">
            {success}
          </div>
        )}

        {/* Mobile/Desktop Filters */}
        <div className={`${colors.secondary} rounded-xl p-4 md:p-6 mb-4 md:mb-8 ${showFilters ? 'block' : 'hidden md:block'}`}>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
            <h2 className="text-lg md:text-xl font-bold mb-2 md:mb-0">Find a Song</h2>
            <div className="flex items-center space-x-2">
              <button
                onClick={clearFilters}
                className="text-gray-300 hover:text-white text-sm transition duration-300"
              >
                Clear Filters
              </button>
              <button
                onClick={() => setShowFilters(false)}
                className="md:hidden text-gray-300 hover:text-white"
              >
                ✕
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 md:gap-4">
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
          </div>
        </div>

        {/* Songs Display */}
        <div className="mb-4">
          <p className="text-gray-400 text-sm md:text-base">
            {filteredSongs.length} song{filteredSongs.length !== 1 ? 's' : ''} found
          </p>
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
                
                <input
                  type="number"
                  placeholder="Tip Amount ($)"
                  value={requestForm.tip_amount}
                  onChange={(e) => setRequestForm({...requestForm, tip_amount: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-400"
                  min="0"
                  step="0.01"
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